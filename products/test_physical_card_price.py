from decimal import Decimal
from uuid import uuid4

from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User
from cards.models import Card, CardIssuance, Transaction
from .models import PhysicalCardPrice, Product


class PhysicalCardPriceTests(TestCase):
    price_url = '/api/products/physical-card/'
    update_url = '/api/products/physical-card/update/'

    def setUp(self):
        self.admin = User.objects.create_user(username='price-admin', user_type='admin')
        self.cashier = User.objects.create_user(username='price-cashier', user_type='caixa')
        self.client.force_login(self.admin)

    def update_price(self, price):
        return self.client.post(self.update_url, {'preco': price}, content_type='application/json')

    def set_price(self, price):
        PhysicalCardPrice.objects.update_or_create(pk=1, defaults={'preco': Decimal(price)})

    def buy(self, card, price='3.75', request_id=None):
        return self.client.post('/api/cards/physical/purchase/', {
            'qr_data': str(card.qr_code_data), 'metodo': 'saldo',
            'request_id': request_id or str(uuid4()), 'preco_cartao': price,
        }, content_type='application/json')

    def issue(self, price='3.75', request_id=None, include=True):
        return self.client.post('/api/cards/temp/create/', {
            'nome': 'Visitante', 'valor': '50.00', 'metodo': 'pix',
            'incluir_cartao_fisico': include, 'preco_cartao': price,
            'request_id': request_id or str(uuid4()),
        }, content_type='application/json')

    def test_initial_price_and_admin_update_persist_without_changing_menu(self):
        self.assertEqual(PhysicalCardPrice.current(), Decimal('2.00'))
        product = Product.objects.create(nome='Suco', preco='7.50')
        response = self.update_price('3.75')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['preco'], '3.75')
        self.assertEqual(PhysicalCardPrice.current(), Decimal('3.75'))
        self.assertEqual(PhysicalCardPrice.objects.count(), 1)
        self.assertEqual([p['id'] for p in self.client.get('/api/products/').json()['products']], [product.pk])
        self.assertEqual([p['id'] for p in self.client.get('/api/products/all/').json()['products']], [product.pk])
        self.assertEqual(self.client.get(self.price_url).json()['preco'], '3.75')
        self.assertIn('no-store', self.client.get(self.price_url)['Cache-Control'])

    def test_price_is_pinned_on_admin_and_rendered_in_both_cashier_forms(self):
        self.set_price('3.75')
        response = self.client.get('/dashboard/')
        self.assertContains(response, 'id="physical-card-product"')
        self.assertContains(response, 'value="3.75"')
        html = response.content.decode()
        self.assertLess(html.index('id="physical-card-product"'), html.index('id="products-list"'))
        fixed_item = html.split('id="physical-card-product"')[1].split('</section>')[0]
        self.assertNotIn('deleteProduct', fixed_item)
        self.client.force_login(self.cashier)
        response = self.client.get('/dashboard/')
        self.assertContains(response, 'data-physical-card-price="3.75"')
        self.assertContains(response, 'R$ 3,75 - Incluir cartão físico')
        self.assertContains(response, 'Comprar cartão físico — R$ 3,75')
        self.assertNotContains(response, 'R$ 2,00')

    def test_only_admin_can_change_price_and_only_staff_can_read_it(self):
        for role in ('caixa', 'balcao', 'cliente'):
            user = User.objects.create_user(username=f'price-{role}', user_type=role)
            self.client.force_login(user)
            self.assertEqual(self.update_price('8.00').status_code, 403)
            self.assertEqual(self.client.get(self.price_url).status_code, 200 if role == 'caixa' else 403)
        self.client.logout()
        self.assertEqual(self.update_price('8.00').status_code, 302)
        self.assertEqual(PhysicalCardPrice.current(), Decimal('2.00'))

    def test_invalid_prices_and_extra_fields_do_not_change_configuration(self):
        for value in ('0', '-1', 'NaN', 'Infinity', '1.001', '100000000', '', None, True, [], {}):
            with self.subTest(value=value):
                self.assertEqual(self.update_price(value).status_code, 400)
                self.assertEqual(PhysicalCardPrice.current(), Decimal('2.00'))
        for body in ({'preco': '3', 'disponivel': False}, {'preco': '3', 'delete': True}, {}):
            self.assertEqual(self.client.post(self.update_url, body, content_type='application/json').status_code, 400)
        self.assertEqual(self.client.get(self.update_url).status_code, 405)

    def test_fixed_item_cannot_be_deleted_through_product_api(self):
        for url in (self.price_url, self.update_url):
            self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(self.client.post(self.price_url + 'delete/').status_code, 404)
        self.assertEqual(self.client.post('/api/products/1/delete/').status_code, 404)
        self.assertEqual(PhysicalCardPrice.current(), Decimal('2.00'))

    def test_database_prevents_duplicate_settings_and_nonpositive_price(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            PhysicalCardPrice.objects.create(id=2, preco='3.00')
        with self.assertRaises(IntegrityError), transaction.atomic():
            PhysicalCardPrice.objects.filter(pk=1).update(preco=0)

    def test_issue_uses_configured_price_without_changing_initial_balance(self):
        self.set_price('3.75')
        self.client.force_login(self.cashier)
        response = self.issue()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_cobrado'], '53.75')
        self.assertEqual(response.json()['valor_cartao'], '3.75')
        self.assertEqual(Card.objects.get().saldo, Decimal('50.00'))
        self.assertEqual(Transaction.objects.get(tipo='cartao').valor, Decimal('3.75'))

    def test_balance_purchase_debits_current_price_and_reports_actual_value(self):
        self.set_price('3.75')
        self.client.force_login(self.cashier)
        card = Card.objects.create(is_temporary=True, nome='Etiqueta', saldo='10.00')
        quote = self.client.get('/api/cards/balance/', {'qr_data': str(card.qr_code_data)})
        self.assertEqual(quote.json()['card']['physical_card_price'], '3.75')
        response = self.buy(card)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['card']['saldo'], '6.25')
        self.assertEqual(Transaction.objects.get().valor, Decimal('3.75'))
        report = self.client.get('/api/reports/daily/').json()
        self.assertEqual(Decimal(report['vendas_cartoes']['total']), Decimal('3.75'))
        self.assertEqual(Decimal(report['vendas_cartoes']['total_saldo']), Decimal('3.75'))

    def test_insufficient_balance_uses_configured_price_not_old_two_reais(self):
        self.set_price('3.75')
        card = Card.objects.create(is_temporary=True, saldo='3.74')
        self.assertEqual(self.buy(card).status_code, 400)
        card.refresh_from_db()
        self.assertEqual(card.saldo, Decimal('3.74'))
        self.assertFalse(Transaction.objects.exists())

    def test_changed_price_rejects_stale_checkout_without_sale_or_debit(self):
        self.set_price('3.75')
        card = Card.objects.create(is_temporary=True, saldo='10.00')
        request_id = str(uuid4())
        for quote in ('2.00', '0.01', '20.00'):
            response = self.buy(card, quote, request_id)
            self.assertEqual(response.status_code, 400)
            self.assertIn('preço do cartão físico foi alterado', response.json()['error'])
        card.refresh_from_db()
        self.assertEqual(card.saldo, Decimal('10.00'))
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(self.buy(card, request_id=request_id).status_code, 200)

    def test_changed_price_rejects_stale_issue_and_label_only_remains_free(self):
        self.set_price('3.75')
        request_id = str(uuid4())
        self.assertEqual(self.issue('2.00', request_id).status_code, 400)
        self.assertFalse(Card.objects.exists())
        self.assertFalse(CardIssuance.objects.exists())
        self.assertFalse(Transaction.objects.exists())
        response = self.issue('2.00', request_id, include=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_cobrado'], '50.00')
        self.assertFalse(Transaction.objects.filter(tipo='cartao').exists())

    def test_price_change_preserves_completed_purchase_retry_and_historical_amount(self):
        self.set_price('3.75')
        card = Card.objects.create(is_temporary=True, saldo='10.00')
        request_id = str(uuid4())
        first = self.buy(card, request_id=request_id).json()
        self.set_price('5.50')
        retry = self.buy(card, request_id=request_id).json()
        self.assertFalse(retry['created'])
        self.assertEqual(retry['transaction_id'], first['transaction_id'])
        self.assertEqual(retry['valor_cartao'], '3.75')
        self.assertEqual(retry['card']['saldo'], '6.25')
        self.assertEqual(retry['card']['physical_card_price'], '5.50')
        self.assertEqual(self.buy(card, '5.50').status_code, 200)
        self.assertCountEqual(list(Transaction.objects.values_list('valor', flat=True)),
                              [Decimal('3.75'), Decimal('5.50')])
        card.refresh_from_db()
        self.assertEqual(card.saldo, Decimal('0.75'))

    def test_price_change_preserves_completed_issuance_retry_and_total(self):
        self.set_price('3.75')
        request_id = str(uuid4())
        first = self.issue(request_id=request_id).json()
        self.set_price('5.50')
        retry = self.issue(request_id=request_id).json()
        self.assertFalse(retry['created'])
        self.assertEqual(retry['card']['id'], first['card']['id'])
        self.assertEqual(retry['total_cobrado'], '53.75')
        self.assertEqual(Transaction.objects.get(tipo='cartao').valor, Decimal('3.75'))
        self.assertEqual(Card.objects.count(), 1)
        self.assertEqual(self.issue('5.50').json()['total_cobrado'], '55.50')
