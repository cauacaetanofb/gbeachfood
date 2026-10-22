from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from smtplib import SMTPException
import logging
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
import json

from .forms import LoginForm, ClienteRegisterForm, StaffUserForm
from .models import User, PasswordResetCode

logger = logging.getLogger(__name__)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                form.add_error(None, 'Usuário ou senha inválidos.')
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ClienteRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = ClienteRegisterForm()
    return render(request, 'register.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    user = request.user
    template_map = {
        'admin': 'dashboard_admin.html',
        'balcao': 'dashboard_balcao.html',
        'caixa': 'dashboard_caixa.html',
        'cliente': 'dashboard_cliente.html',
    }

    # Admin pode acessar os painéis operacionais, sem cartão pessoal.
    view_as = user.user_type
    if user.user_type == 'admin':
        requested = request.GET.get('as', 'admin')
        if requested in ('admin', 'caixa', 'balcao'):
            view_as = requested

    template = template_map.get(view_as, 'login.html')
    return render(request, template, {'user': user, 'is_admin': user.user_type == 'admin', 'active_page': view_as})


# ---- Esqueci minha senha ----

@require_POST
def api_forgot_password(request):
    """Envia código de 6 dígitos para o e-mail."""
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    if not isinstance(data, dict) or not isinstance(data.get('email'), str):
        return JsonResponse({'error': 'Informe o e-mail'}, status=400)
    email = data['email'].strip()
    if not email:
        return JsonResponse({'error': 'Informe o e-mail'}, status=400)

    if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
        gmail_without_credentials = settings.EMAIL_HOST == 'smtp.gmail.com' and not (
            settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)
        if not settings.EMAIL_HOST or gmail_without_credentials:
            return JsonResponse({'error': 'Envio de e-mail não configurado. Contate o suporte.'}, status=503)

    if not User.objects.filter(email=email).exists():
        return JsonResponse({'success': True})

    code = PasswordResetCode.generate_code()
    reset = PasswordResetCode.objects.create(email=email, code=code)
    try:
        sent = send_mail(
            subject='GFood — Código de Recuperação',
            message=f'Seu código de recuperação é: {code}\n\nEste código expira em 15 minutos.',
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )
        if sent != 1:
            raise SMTPException('Mensagem não enviada')
    except (SMTPException, OSError, ImproperlyConfigured) as error:
        reset.delete()
        # Não registrar senha SMTP, código de recuperação ou endereço do destinatário.
        logger.warning('Falha no envio de recuperação de senha (%s).', type(error).__name__)
        return JsonResponse({
            'error': 'Não foi possível enviar o e-mail. Tente novamente mais tarde.',
        }, status=503)
    return JsonResponse({'success': True})


@require_POST
def api_verify_reset_code(request):
    """Verifica código e reseta a senha."""
    data = json.loads(request.body)
    email = data.get('email', '').strip()
    code = data.get('code', '').strip()
    new_password = data.get('new_password', '')

    if not all([email, code, new_password]):
        return JsonResponse({'error': 'Preencha todos os campos'}, status=400)
    if len(new_password) < 8:
        return JsonResponse({'error': 'Senha deve ter pelo menos 8 caracteres'}, status=400)

    try:
        reset = PasswordResetCode.objects.filter(
            email=email, code=code, usado=False
        ).latest('criado_em')
    except PasswordResetCode.DoesNotExist:
        return JsonResponse({'error': 'Código inválido'}, status=400)

    if reset.is_expired():
        return JsonResponse({'error': 'Código expirado. Solicite um novo.'}, status=400)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'error': 'Usuário não encontrado'}, status=404)

    user.set_password(new_password)
    user.save()
    reset.usado = True
    reset.save()

    return JsonResponse({'success': True})


# ---- API views para admin gerenciar staff ----

@login_required
def api_list_staff(request):
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    users = User.objects.filter(user_type__in=['admin', 'balcao', 'caixa']).exclude(
        id=request.user.id
    ).values('id', 'username', 'first_name', 'user_type')
    return JsonResponse({'users': list(users)})


@login_required
@require_POST
def api_create_staff(request):
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    data = json.loads(request.body)
    form = StaffUserForm(data)
    if form.is_valid():
        user = form.save()
        return JsonResponse({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'user_type': user.user_type
            }
        })
    error_msgs = []
    for field, errors in form.errors.items():
        for e in errors:
            error_msgs.append(e)
    return JsonResponse({'error': ' | '.join(error_msgs)}, status=400)


@login_required
@require_POST
def api_update_staff(request, user_id):
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    try:
        user = User.objects.get(id=user_id, user_type__in=['admin', 'balcao', 'caixa'])
    except User.DoesNotExist:
        return JsonResponse({'error': 'Usuário não encontrado'}, status=404)

    data = json.loads(request.body)
    user.first_name = data.get('first_name', user.first_name)
    new_type = data.get('user_type', '')
    if new_type in ['admin', 'balcao', 'caixa']:
        user.user_type = new_type
    new_password = data.get('password', '')
    if new_password:
        if len(new_password) < 8:
            return JsonResponse({'error': 'Senha deve ter pelo menos 8 caracteres'}, status=400)
        user.set_password(new_password)
    user.save()
    return JsonResponse({'success': True})


@login_required
@require_POST
def api_delete_staff(request, user_id):
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    if user_id == request.user.id:
        return JsonResponse({'error': 'Você não pode excluir a si mesmo'}, status=400)
    try:
        user = User.objects.get(id=user_id, user_type__in=['admin', 'balcao', 'caixa'])
        user.delete()
        return JsonResponse({'success': True})
    except User.DoesNotExist:
        return JsonResponse({'error': 'Usuário não encontrado'}, status=404)


# ---- API para admin editar seu próprio perfil ----

@login_required
def api_my_profile(request):
    u = request.user
    return JsonResponse({
        'profile': {
            'id': u.id,
            'username': u.username,
            'first_name': u.first_name,
            'email': u.email,
            'cpf': u.cpf,
        }
    })


@login_required
@require_POST
def api_update_my_profile(request):
    data = json.loads(request.body)
    user = request.user

    user.first_name = data.get('first_name', user.first_name)
    user.email = data.get('email', user.email)
    if 'cpf' in data:
        user.cpf = data['cpf'].strip()

    new_username = data.get('username', '').strip()
    if new_username and new_username != user.username:
        if User.objects.filter(username=new_username).exclude(id=user.id).exists():
            return JsonResponse({'error': 'Este nome de usuário já está em uso'}, status=400)
        user.username = new_username

    new_password = data.get('password', '')
    if new_password:
        if len(new_password) < 8:
            return JsonResponse({'error': 'Senha deve ter pelo menos 8 caracteres'}, status=400)
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
    else:
        user.save()

    return JsonResponse({'success': True})


# ---- API views para admin gerenciar clientes ----

@login_required
def api_list_clients(request):
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    clients = User.objects.filter(user_type='cliente').select_related('card')
    data = []
    for c in clients:
        saldo = '0.00'
        try:
            saldo = str(c.card.saldo)
        except Exception:
            pass
        data.append({
            'id': c.id,
            'username': c.username,
            'first_name': c.first_name,
            'email': c.email,
            'cpf': c.cpf,
            'telefone': c.telefone,
            'saldo': saldo,
            'date_joined': c.date_joined.strftime('%d/%m/%Y'),
        })
    return JsonResponse({'clients': data})


@login_required
@require_POST
def api_update_client(request, client_id):
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    try:
        user = User.objects.get(id=client_id, user_type='cliente')
    except User.DoesNotExist:
        return JsonResponse({'error': 'Cliente não encontrado'}, status=404)

    data = json.loads(request.body)
    user.first_name = data.get('first_name', user.first_name)
    user.email = data.get('email', user.email)
    user.cpf = data.get('cpf', user.cpf)
    user.telefone = data.get('telefone', user.telefone)
    user.save()
    return JsonResponse({'success': True})


@login_required
@require_POST
def api_delete_client(request, client_id):
    if request.user.user_type != 'admin':
        return JsonResponse({'error': 'Sem permissão'}, status=403)
    try:
        user = User.objects.get(id=client_id, user_type='cliente')
        user.delete()
        return JsonResponse({'success': True})
    except User.DoesNotExist:
        return JsonResponse({'error': 'Cliente não encontrado'}, status=404)
