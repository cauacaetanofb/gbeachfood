import base64
import io
import logging
import qrcode
from decimal import Decimal as D
from datetime import date, timedelta
from urllib.parse import urlsplit
import requests as http_requests
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings as django_settings
from django.db import transaction
from django.utils.crypto import constant_time_compare
from .validation import money, json_api, InvalidInput, MAX_AMOUNT, positive_id
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET

from .models import Card, Transaction, Recarga

logger = logging.getLogger(__name__)


def _payment_method(data):
    method = data.get('metodo', 'dinheiro')
    if method not in ('dinheiro', 'pix', 'credito', 'debito'):
        raise InvalidInput('Forma de pagamento inválida.')
    return method


def _validate_credit(card, amount):
    if card.bloqueado:
        raise InvalidInput('Este cartão está cancelado.')
    if card.saldo + amount > MAX_AMOUNT:
        raise InvalidInput('Saldo máximo excedido.')


def generate_qr_base64(data_str):
    """Gera QR Code em base64 para exibir no frontend."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


@login_required
def api_my_card(request):
    """Retorna o cartão do cliente logado."""
    if request.user.user_type != 'cliente':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    card, created = Card.objects.get_or_create(user=request.user)
    qr_b64 = generate_qr_base64(str(card.qr_code_data))
    return JsonResponse({
        'card': {
            'id': card.id,
            'saldo': str(card.saldo),
            'qr_code_data': str(card.qr_code_data),
            'qr_code_image': qr_b64,
            'bloqueado': card.bloqueado,
        }
    })


@login_required
def api_check_balance(request):
    """Consulta saldo por QR code data (UUID)."""
    qr_data = request.GET.get('qr_data', '')
    try:
        card = Card.objects.get(qr_code_data=qr_data)
        nome = card.nome if card.is_temporary else (card.user.get_full_name() if card.user else 'N/A')
        return JsonResponse({
            'card': {
                'id': card.id,
                'nome': nome,
                'saldo': str(card.saldo),
                'qr_code_data': str(card.qr_code_data),
                'is_temporary': card.is_temporary,
                'bloqueado': card.bloqueado,
            }
        })
    except Card.DoesNotExist:
        return JsonResponse({'error': 'Cartão não encontrado'}, status=404)


@login_required
@require_POST
@json_api
@transaction.atomic
def api_add_balance(request):
    """Recarga presencial restrita a caixa/admin, com saldo e extrato atômicos."""
    if request.user.user_type not in ('admin', 'caixa'):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    data = request.json_data
    valor = money(data.get('valor'))
    metodo = _payment_method(data)
    try:
        card = Card.objects.select_for_update().get(qr_code_data=data.get('qr_data', ''))
    except Card.DoesNotExist:
        return JsonResponse({'error': 'Cartão não encontrado'}, status=404)
    _validate_credit(card, valor)
    card.saldo += valor
    card.save(update_fields=['saldo'])
    Transaction.objects.create(
        card=card, tipo='deposito', valor=valor, metodo=metodo, origem='caixa',
        descricao=f'Recarga presencial via {dict(Transaction.METODO_CHOICES)[metodo]}',
        operador=request.user,
    )
    return JsonResponse({'success': True, 'novo_saldo': str(card.saldo)})


@login_required
@require_POST
@json_api
@transaction.atomic
def api_remove_balance(request):
    if request.user.user_type not in ('admin', 'caixa'):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    data = request.json_data
    valor = money(data.get('valor'))
    metodo = _payment_method(data)
    try:
        card = Card.objects.select_for_update().get(qr_code_data=data.get('qr_data', ''))
    except Card.DoesNotExist:
        return JsonResponse({'error': 'Cartão não encontrado'}, status=404)
    if card.bloqueado:
        raise InvalidInput('Este cartão está cancelado.')
    if card.saldo < valor:
        raise InvalidInput('Saldo insuficiente.')
    card.saldo -= valor
    card.save(update_fields=['saldo'])
    Transaction.objects.create(
        card=card, tipo='retirada', valor=valor, metodo=metodo, origem='caixa',
        descricao='Retirada de saldo', operador=request.user,
    )
    return JsonResponse({'success': True, 'novo_saldo': str(card.saldo)})


@login_required
@require_POST
@json_api
@transaction.atomic
def api_create_temp_card(request):
    if request.user.user_type not in ('admin', 'caixa'):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    data = request.json_data
    nome = data.get('nome', '')
    cpf = data.get('cpf', '')
    telefone = data.get('telefone', '')
    for value, limit in ((nome, 200), (cpf, 14), (telefone, 15)):
        if not isinstance(value, str) or len(value) > limit:
            raise InvalidInput('Dados do cliente inválidos.')
    if not nome.strip():
        raise InvalidInput('Nome é obrigatório.')
    valor = money(data.get('valor'))
    metodo = _payment_method(data)
    qr_data = data.get('qr_data')
    if qr_data:
        try:
            card = Card.objects.select_for_update().get(qr_code_data=qr_data)
        except Card.DoesNotExist:
            return JsonResponse({'error': 'QR Code do cartão físico não encontrado'}, status=404)
        if card.user_id is not None:
            raise InvalidInput('Este cartão já pertence a um usuário cadastrado.')
        card.bloqueado = False
        card.motivo_bloqueio = ''
        _validate_credit(card, valor)
        card.saldo += valor
        card.is_temporary = True
        card.nome, card.cpf, card.telefone = nome.strip(), cpf, telefone
        card.save()
    else:
        card = Card.objects.create(is_temporary=True, nome=nome.strip(), cpf=cpf,
                                   telefone=telefone, saldo=valor)
    Transaction.objects.create(
        card=card, tipo='deposito', valor=valor, metodo=metodo, origem='caixa',
        descricao=f'Recarga presencial — novo cartão para {nome}'[:255], operador=request.user,
    )
    return JsonResponse({'success': True, 'card': {
        'id': card.id, 'nome': card.nome, 'saldo': str(card.saldo),
        'qr_code_data': str(card.qr_code_data),
        'qr_code_image': generate_qr_base64(str(card.qr_code_data)),
    }})


@login_required
@require_POST
def api_client_add_balance(request):
    """Rota antiga desativada: crédito do app exige confirmação PIX."""
    return JsonResponse({
        'error': 'Recarga direta desativada. Use uma cobrança Asaas para adicionar saldo.',
    }, status=410)


@login_required
def api_client_transactions(request, client_id):
    """Admin: retorna transações de um cliente."""
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    try:
        card = Card.objects.get(user_id=client_id)
    except Card.DoesNotExist:
        return JsonResponse({'transactions': []})

    tipo_labels = dict(Transaction.TIPO_CHOICES)
    metodo_labels = dict(Transaction.METODO_CHOICES)

    txns = card.transactions.all()[:50]
    data = []
    for t in txns:
        data.append({
            'id': t.id,
            'tipo': t.tipo,
            'tipo_label': tipo_labels.get(t.tipo, t.tipo),
            'valor': str(t.valor),
            'metodo': t.metodo,
            'metodo_label': metodo_labels.get(t.metodo, t.metodo),
            'descricao': t.descricao,
            'data': t.criado_em.strftime('%d/%m/%Y %H:%M'),
        })
    return JsonResponse({'transactions': data, 'saldo': str(card.saldo)})


@login_required
def api_my_transactions(request):
    """Cliente: retorna suas próprias transações."""
    if request.user.user_type != 'cliente':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    try:
        card = Card.objects.get(user=request.user)
    except Card.DoesNotExist:
        return JsonResponse({'transactions': [], 'saldo': '0.00'})

    tipo_labels = dict(Transaction.TIPO_CHOICES)
    metodo_labels = dict(Transaction.METODO_CHOICES)

    txns = card.transactions.all()[:100]
    data = []
    for t in txns:
        data.append({
            'id': t.id,
            'tipo': t.tipo,
            'tipo_label': tipo_labels.get(t.tipo, t.tipo),
            'valor': str(t.valor),
            'metodo': t.metodo,
            'metodo_label': metodo_labels.get(t.metodo, t.metodo),
            'descricao': t.descricao,
            'data': t.criado_em.strftime('%d/%m/%Y %H:%M'),
        })
    return JsonResponse({'transactions': data, 'saldo': str(card.saldo)})


# ===== Busca por CPF =====
@login_required
def api_search_by_cpf(request):
    """Busca cartões por CPF."""
    if request.user.user_type not in ['admin', 'caixa']:
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    cpf = request.GET.get('cpf', '').strip()
    if not cpf:
        return JsonResponse({'error': 'CPF é obrigatório'}, status=400)

    cards = Card.objects.filter(cpf=cpf)
    if not cards.exists():
        return JsonResponse({'error': 'Nenhum cartão encontrado com esse CPF'}, status=404)

    result = []
    for card in cards:
        nome = card.nome if card.is_temporary else (card.user.get_full_name() if card.user else 'N/A')
        result.append({
            'id': card.id,
            'nome': nome,
            'cpf': card.cpf,
            'saldo': str(card.saldo),
            'qr_code_data': str(card.qr_code_data),
            'is_temporary': card.is_temporary,
            'bloqueado': card.bloqueado,
            'motivo_bloqueio': card.motivo_bloqueio,
        })
    return JsonResponse({'cards': result})


# ===== Bloquear / Cancelar Cartão =====
@login_required
@require_POST
@json_api
@transaction.atomic
def api_block_card(request):
    """Cancela cartão e registra a retirada na mesma transação."""
    if request.user.user_type not in ('admin', 'caixa'):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    data = request.json_data
    card_id = positive_id(data.get('card_id'))
    motivo = data.get('motivo', 'Cancelado pelo caixa')
    if not isinstance(motivo, str) or len(motivo) > 255:
        raise InvalidInput('Motivo inválido.')
    try:
        card = Card.objects.select_for_update().get(id=card_id)
    except Card.DoesNotExist:
        return JsonResponse({'error': 'Cartão não encontrado'}, status=404)
    if card.bloqueado:
        raise InvalidInput('Este cartão já está cancelado.')
    if card.saldo > 0:
        Transaction.objects.create(
            card=card, tipo='retirada', valor=card.saldo, metodo='outro', origem='caixa',
            descricao=f'Saldo zerado por cancelamento — {motivo}'[:255], operador=request.user,
        )
    card.bloqueado = True
    card.motivo_bloqueio = motivo
    card.saldo = D('0.00')
    card.nome = card.cpf = card.telefone = ''
    card.is_temporary = False
    card.user = None
    card.save()
    return JsonResponse({'success': True, 'message': 'Cartão cancelado e liberado para reutilização'})


# ===== Transferir Saldo =====
@login_required
@require_POST
@json_api
@transaction.atomic
def api_transfer_balance(request):
    """Bloqueia os dois cartões em ordem de ID para evitar deadlocks."""
    if request.user.user_type not in ('admin', 'caixa'):
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    data = request.json_data
    from_id = positive_id(data.get('from_card_id'))
    try:
        to_id = Card.objects.values_list('pk', flat=True).get(qr_code_data=data.get('to_qr_data', ''))
    except Card.DoesNotExist:
        return JsonResponse({'error': 'Cartão de destino não encontrado'}, status=404)
    if from_id == to_id:
        raise InvalidInput('Não é possível transferir para o mesmo cartão.')
    cards = {card.pk: card for card in Card.objects.select_for_update().filter(
        pk__in=[from_id, to_id]).order_by('pk')}
    if from_id not in cards or to_id not in cards:
        return JsonResponse({'error': 'Cartão não encontrado'}, status=404)
    from_card, to_card = cards[from_id], cards[to_id]
    if from_card.bloqueado:
        raise InvalidInput('O cartão de origem está cancelado.')
    saldo = money(from_card.saldo)
    _validate_credit(to_card, saldo)
    from_card.saldo = D('0.00')
    to_card.saldo += saldo
    from_card.save(update_fields=['saldo'])
    to_card.save(update_fields=['saldo'])
    to_nome = to_card.nome if to_card.is_temporary else (to_card.user.get_full_name() if to_card.user else 'N/A')
    from_nome = from_card.nome or (from_card.user.get_full_name() if from_card.user else 'Cartão sem nome')
    Transaction.objects.create(
        card=from_card, tipo='retirada', valor=saldo, metodo='outro', origem='caixa',
        descricao=f'Transferência para cartão de {to_nome}'[:255], operador=request.user,
    )
    Transaction.objects.create(
        card=to_card, tipo='deposito', valor=saldo, metodo='outro', origem='caixa',
        descricao=f'Transferência recebida do cartão de {from_nome}'[:255], operador=request.user,
    )
    return JsonResponse({'success': True, 'valor_transferido': str(saldo),
                         'novo_saldo_destino': str(to_card.saldo)})


# ===== Integração Asaas =====


def _asaas_headers():
    return {
        'access_token': django_settings.ASAAS_API_KEY.strip(),
        'Content-Type': 'application/json',
        'User-Agent': 'gbeachfood',
    }


def _asaas_url(path):
    """Monta URL da API Asaas, removendo barras extras."""
    base = django_settings.ASAAS_BASE_URL.strip().rstrip('/')
    return f'{base}/{path.lstrip("/")}'


class _AsaasError(Exception):
    """Falha do provedor com mensagem pública controlada, sem dados da resposta."""

    def __init__(self, message, *, code, status=502):
        super().__init__(message)
        self.code = code
        self.status = status

    def response(self):
        return JsonResponse({'error': str(self), 'code': self.code}, status=self.status)


def _asaas_post(path, payload):
    try:
        response = http_requests.post(_asaas_url(path), json=payload,
                                      headers=_asaas_headers(), timeout=15)
    except http_requests.Timeout:
        raise _AsaasError(
            'O Asaas demorou para responder. Procure o atendimento antes de tentar novamente.',
            code='asaas_timeout', status=504) from None
    except http_requests.RequestException:
        raise _AsaasError(
            'Não foi possível conectar ao serviço de pagamentos. Tente novamente em instantes.',
            code='asaas_connection') from None

    # Classifica HTTP antes do JSON: um erro de autenticação também pode vir em HTML.
    if response.status_code in (401, 403):
        logger.warning('Asaas: autenticação ou acesso recusado em %s (HTTP %s). '
                       'Verifique ASAAS_API_KEY e o ambiente ASAAS_BASE_URL.', path, response.status_code)
        raise _AsaasError(
            'Pagamentos indisponíveis por uma falha na configuração do serviço. Procure o atendimento.',
            code='asaas_authentication', status=503)
    if response.status_code == 429 or response.status_code >= 500:
        raise _AsaasError('O serviço de pagamentos está indisponível. Tente novamente em instantes.',
                          code='asaas_unavailable', status=503)
    try:
        data = response.json()
    except ValueError:
        data = None
    if not isinstance(data, dict):
        raise _AsaasError('O serviço de pagamentos retornou uma resposta inválida. Procure o atendimento.',
                          code='asaas_invalid_response')
    return response.status_code, data


def _get_or_create_asaas_customer(user):
    """Cria o customer no Asaas se ainda não existir."""
    if user.asaas_customer_id:
        return user.asaas_customer_id

    cpf_limpo = ''.join(c for c in (user.cpf or '') if c in '0123456789')
    if len(cpf_limpo) != 11:
        raise InvalidInput('CPF inválido ou não cadastrado. Atualize seu CPF no perfil.')

    payload = {'name': user.first_name or user.username, 'cpfCnpj': cpf_limpo}
    if user.email:
        payload['email'] = user.email
    status, data = _asaas_post('customers', payload)
    if status >= 400:
        raise _AsaasError(
            'O Asaas não aceitou o cadastro do pagador. Confira os dados do perfil ou procure o atendimento.',
            code='asaas_customer_rejected', status=400)
    customer_id = data.get('id')
    if not isinstance(customer_id, str) or not customer_id.strip() or len(customer_id) > 100:
        raise _AsaasError('Não foi possível confirmar o cadastro no serviço de pagamentos. Procure o atendimento.',
                          code='asaas_invalid_response')
    user.asaas_customer_id = customer_id
    user.save(update_fields=['asaas_customer_id'])
    return customer_id


def _safe_invoice_url(value):
    if not isinstance(value, str) or len(value) > 500:
        return ''
    try:
        url = urlsplit(value)
        hosts = {'asaas.com', 'www.asaas.com', 'sandbox.asaas.com', 'www.sandbox.asaas.com'}
        if (url.scheme == 'https' and url.hostname in hosts and not url.username
                and not url.password and url.port in (None, 443)):
            return value
    except ValueError:
        pass
    return ''


@login_required
@require_POST
@json_api
def api_asaas_create_payment(request):
    """Cria PIX ou fatura de crédito à vista; nunca recebe dados do cartão."""
    if request.user.user_type != 'cliente':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    data = request.json_data
    if set(data) - {'valor', 'metodo'}:
        raise InvalidInput('Informe apenas o valor e a forma de pagamento. O cartão é informado no Asaas.')
    metodo = data.get('metodo', 'pix')
    if metodo not in ('pix', 'credito'):
        raise InvalidInput('Forma de pagamento inválida.')
    valor = money(data.get('valor'), minimum=D('5.00') if metodo == 'credito' else D('1.00'))
    card, _ = Card.objects.get_or_create(user=request.user)
    _validate_credit(card, valor)
    if not django_settings.ASAAS_API_KEY.strip():
        return JsonResponse({'error': 'Pagamentos temporariamente indisponíveis.'}, status=503)

    try:
        customer_id = _get_or_create_asaas_customer(request.user)
        payment_payload = {
            'customer': customer_id,
            'billingType': 'CREDIT_CARD' if metodo == 'credito' else 'PIX',
            'value': float(valor),  # Apenas serialização; cálculos locais usam Decimal.
            'dueDate': (date.today() + timedelta(days=1)).isoformat(),
            'description': f'Recarga GBeachFood - R$ {valor:.2f}',
        }
        # Sem installmentCount/creditCard: cobrança única, paga na página do Asaas.
        status, payment = _asaas_post('payments', payment_payload)
        if status >= 400:
            errors = payment.get('errors')
            invalid_customer = isinstance(errors, list) and any(
                isinstance(e, dict) and e.get('code') == 'invalid_customer' for e in errors)
            if invalid_customer:
                request.user.asaas_customer_id = ''
                request.user.save(update_fields=['asaas_customer_id'])
                payment_payload['customer'] = _get_or_create_asaas_customer(request.user)
                status, payment = _asaas_post('payments', payment_payload)
            if status >= 400:
                raise _AsaasError(
                    'O Asaas não permitiu criar a cobrança. Confira seu cadastro ou procure o atendimento.',
                    code='asaas_payment_rejected', status=400)
        if not isinstance(payment.get('id'), str) or not payment['id']:
            raise _AsaasError('Não foi possível confirmar a cobrança no serviço de pagamentos. Procure o atendimento.',
                              code='asaas_invalid_response')
    except InvalidInput:
        raise  # Erro do perfil é HTTP 400, sem confundir com falha do provedor.
    except _AsaasError as error:
        return error.response()
    except Exception:
        logger.warning('Asaas: falha inesperada ao preparar a recarga.')
        return JsonResponse({'error': 'Não foi possível obter a cobrança no Asaas. Procure o atendimento.',
                             'code': 'asaas_unexpected_error'}, status=502)

    invoice_url = _safe_invoice_url(payment.get('invoiceUrl')) if metodo == 'credito' else ''
    recarga = Recarga.objects.create(card=card, user=request.user, valor=valor,
        asaas_payment_id=payment['id'], metodo=metodo, invoice_url=invoice_url)
    if metodo == 'credito':
        if not invoice_url:
            return JsonResponse({'error': 'Cobrança criada, mas o link não está disponível. Procure o atendimento antes de criar outra.'}, status=502)
        return JsonResponse({'success': True, 'recarga_id': recarga.pk,
                             'metodo': metodo, 'invoice_url': invoice_url, 'valor': str(valor)})
    try:
        pix_resp = http_requests.get(_asaas_url(f'payments/{payment["id"]}/pixQrCode'),
                                     headers=_asaas_headers(), timeout=15)
        pix_data = pix_resp.json()
        if not isinstance(pix_data, dict):
            raise ValueError('Invalid QR response')
    except Exception:
        pix_data = {}
    return JsonResponse({'success': True, 'recarga_id': recarga.pk, 'metodo': metodo,
        'pix_qr_code_image': pix_data.get('encodedImage', ''),
        'pix_copia_cola': pix_data.get('payload', ''), 'valor': str(valor)})


@login_required
@require_GET
def api_asaas_pending_payments(request):
    if request.user.user_type != 'cliente':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    recargas = Recarga.objects.filter(user=request.user, card__user=request.user,
        card__bloqueado=False, metodo='credito', status='pendente').exclude(invoice_url='')[:10]
    return JsonResponse({'recargas': [{'id': r.pk, 'valor': str(r.valor),
        'invoice_url': url} for r in recargas if (url := _safe_invoice_url(r.invoice_url))]})


@csrf_exempt
@require_POST
def api_asaas_webhook(request):
    """Autentica antes de interpretar qualquer confirmação de pagamento."""
    expected_token = django_settings.ASAAS_WEBHOOK_TOKEN
    if not expected_token:
        return JsonResponse({'error': 'Webhook não configurado'}, status=503)
    token = request.headers.get('asaas-access-token', '')
    if not token or not constant_time_compare(token, expected_token):
        return JsonResponse({'error': 'Token inválido'}, status=401)
    return _process_asaas_webhook(request)


@json_api
@transaction.atomic
def _process_asaas_webhook(request):
    data = request.json_data
    event = data.get('event')
    review_events = {'PAYMENT_REFUNDED', 'PAYMENT_PARTIALLY_REFUNDED',
        'PAYMENT_REFUND_IN_PROGRESS', 'PAYMENT_CHARGEBACK_REQUESTED',
        'PAYMENT_CHARGEBACK_DISPUTE', 'PAYMENT_AWAITING_CHARGEBACK_REVERSAL'}
    if event not in {'PAYMENT_CONFIRMED', 'PAYMENT_RECEIVED'} | review_events:
        return JsonResponse({'ok': True})
    payment = data.get('payment')
    if not isinstance(payment, dict) or not isinstance(payment.get('id'), str) or not payment['id']:
        raise InvalidInput('Pagamento inválido.')
    amount = money(payment.get('value'))
    if payment.get('billingType') not in ('PIX', 'CREDIT_CARD'):
        raise InvalidInput('Forma de pagamento inválida.')
    if event not in review_events and payment.get('status') != event.removeprefix('PAYMENT_'):
        raise InvalidInput('Confirmação de pagamento inválida.')

    recarga = Recarga.objects.select_for_update().filter(asaas_payment_id=payment['id']).first()
    if recarga is None:
        return JsonResponse({'ok': True})  # Cobrança não pertence às recargas do app.
    expected_type = 'CREDIT_CARD' if recarga.metodo == 'credito' else 'PIX'
    if payment.get('billingType') != expected_type:
        raise InvalidInput('Forma de pagamento não corresponde à recarga.')
    if amount != recarga.valor:
        raise InvalidInput('Valor do pagamento não corresponde à recarga.')
    if event in review_events:
        card = Card.objects.select_for_update().get(pk=recarga.card_id)
        recarga.status = 'revisao'
        recarga.evento_revisao = event
        recarga.save(update_fields=['status', 'evento_revisao'])
        # Não deduz automaticamente valores já consumidos nem credita novamente
        # após uma disputa: o atendimento precisa reconciliar o saldo e o Asaas.
        if card.user_id == recarga.user_id and not card.bloqueado:
            card.bloqueado = True
            card.motivo_bloqueio = f'Revisar recarga Asaas {recarga.asaas_payment_id}: {event}'[:255]
            card.save(update_fields=['bloqueado', 'motivo_bloqueio'])
        return JsonResponse({'ok': True})
    if recarga.status != 'pendente':
        return JsonResponse({'ok': True})  # CONFIRMED e RECEIVED creditam uma única vez.

    card = Card.objects.select_for_update().get(pk=recarga.card_id)
    if card.bloqueado or card.user_id != recarga.user_id:
        return JsonResponse({'error': 'Cartão indisponível para esta recarga'}, status=409)
    if card.saldo + recarga.valor > MAX_AMOUNT:
        raise InvalidInput('Saldo máximo excedido.')
    card.saldo += recarga.valor
    card.save(update_fields=['saldo'])
    recarga.status = 'pago'
    recarga.save(update_fields=['status'])
    Transaction.objects.create(
        card=card, tipo='deposito', valor=recarga.valor, metodo=recarga.metodo, origem='app',
        descricao=f'Recarga via {recarga.get_metodo_display()} (Asaas)', operador_id=recarga.user_id,
    )
    return JsonResponse({'ok': True})


@login_required
@require_GET
def api_asaas_check_payment(request, recarga_id):
    """Cliente verifica se o pagamento foi confirmado."""
    if request.user.user_type != 'cliente':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    try:
        recarga = Recarga.objects.get(id=recarga_id, user=request.user)
        return JsonResponse({
            'status': recarga.status,
            'metodo': recarga.metodo,
            'valor': str(recarga.valor),
        })
    except Recarga.DoesNotExist:
        return JsonResponse({'error': 'Recarga não encontrada'}, status=404)
