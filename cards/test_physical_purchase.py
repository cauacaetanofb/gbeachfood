from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.test import Client, TestCase

from accounts.models import User
from .models import Card, CardIssuance, Transaction


class PhysicalCardPurchaseTests(TestCase):
    url = '/api/cards/physical/purchase/'

    def setUp(self):
        self.cashier = User.objects.create_user(username='purchase-cashier', user_type='caixa')
        self.client.force_login(self.cashier)
        self.card = Card.objects.create(is_temporary=True, nome='Visitante com etiqueta',
                                        cpf='000.000.001-91', saldo=Decimal('35.50'))

    def buy(self, **changes):
        return self.client.post(self.url, {
            'qr_data': str(self.card.qr_code_data), 'metodo': 'dinheiro', **changes,
        }, content_type='application/json')

    def test_buy_keeps_same_card_personal_data_uuid_and_balance(self):
        before = Card.objects.values().get(pk=self.card.pk)
        response = self.buy()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['created'])
        self.assertEqual(response.json()['valor_cartao'], '2.00')
        self.assertEqual(Card.objects.values().get(pk=self.card.pk), before)
        self.assertEqual(Card.objects.count(), 1)
        sale = Transaction.objects.get()
        self.assertEqual((sale.tipo, sale.valor, sale.metodo, sale.origem, sale.operador_id, sale.cpf_cliente),
                         ('cartao', Decimal('2.00'), 'dinheiro', 'caixa', self.cashier.pk, self.card.cpf))
        self.assertEqual(self.client.get(response.json()['label_url']).status_code, 200)
        self.assertFalse(CardIssuance.objects.exists())

    def test_zero_balance_can_buy_because_payment_is_external(self):
        self.card.saldo = 0
        self.card.save()
        self.assertEqual(self.buy().status_code, 200)
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, 0)
        self.assertEqual(Transaction.objects.get().tipo, 'cartao')

    def test_retries_and_other_cashier_do_not_duplicate_or_change_payment_method(self):
        first = self.buy().json()
        other = User.objects.create_user(username='second-cashier', user_type='caixa')
        self.client.force_login(other)
        second = self.buy(metodo='pix').json()
        self.assertFalse(second['created'])
        self.assertEqual(first['transaction_id'], second['transaction_id'])
        self.assertEqual(second['metodo'], 'dinheiro')
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(Transaction.objects.get().operador, self.cashier)

    def test_card_bought_at_creation_is_already_marked_and_cannot_be_sold_again(self):
        created = self.client.post('/api/cards/temp/create/', {
            'request_id': str(uuid4()), 'nome': 'Com cartão', 'valor': '50.00',
            'metodo': 'credito', 'incluir_cartao_fisico': True,
        }, content_type='application/json').json()
        code = created['card']['qr_code_data']
        response = self.buy(qr_data=code)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['created'])
        self.assertEqual(Transaction.objects.filter(tipo='cartao').count(), 1)
        self.assertEqual(Transaction.objects.count(), 2)
        info = self.client.get('/api/cards/balance/', {'qr_data': code}).json()['card']
        self.assertTrue(info['physical_card_purchased'])
        self.assertEqual(info['saldo'], '50.00')

    def test_later_purchase_preserves_initial_issue_and_retry_total(self):
        payload = {'request_id': str(uuid4()), 'nome': 'Só etiqueta', 'valor': '50.00', 'metodo': 'pix'}
        initial = self.client.post('/api/cards/temp/create/', payload, content_type='application/json').json()
        self.assertEqual(self.buy(qr_data=initial['card']['qr_code_data']).status_code, 200)
        retried = self.client.post('/api/cards/temp/create/', payload, content_type='application/json').json()
        self.assertFalse(retried['created'])
        self.assertEqual(retried['valor_cartao'], '0.00')
        self.assertEqual(retried['total_cobrado'], '50.00')
        self.assertEqual(Transaction.objects.count(), 2)

    def test_balance_query_changes_purchase_status_without_writing(self):
        query = {'qr_data': str(self.card.qr_code_data)}
        before = self.client.get('/api/cards/balance/', query)
        self.assertFalse(before.json()['card']['physical_card_purchased'])
        self.assertEqual(before.json()['card']['physical_card_price'], '2.00')
        self.assertIn('no-store', before['Cache-Control'])
        self.assertFalse(Transaction.objects.exists())
        self.buy()
        self.assertTrue(self.client.get('/api/cards/balance/', query).json()['card']['physical_card_purchased'])
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(self.client.get('/api/cards/balance/', {'qr_data': 'invalid'}).status_code, 400)

    def test_invalid_card_price_and_method_do_not_write(self):
        for changes in ({'qr_data': ''}, {'qr_data': 'bad'}, {'qr_data': None}, {'metodo': 'saldo'},
                        {'metodo': 'outro'}, {'valor': '0.01'}, {'valor_cartao': '100'}):
            with self.subTest(changes=changes):
                self.assertEqual(self.buy(**changes).status_code, 400)
        self.assertEqual(self.buy(qr_data=str(uuid4())).status_code, 404)
        self.assertFalse(Transaction.objects.exists())

    def test_cancelled_personal_and_unassigned_cards_are_rejected(self):
        self.card.bloqueado = True
        self.card.save()
        self.assertEqual(self.buy().status_code, 400)
        customer = User.objects.create_user(username='purchase-customer', user_type='cliente')
        self.assertEqual(self.buy(qr_data=str(customer.card.qr_code_data)).status_code, 400)
        stock = Card.objects.create()
        self.assertEqual(self.buy(qr_data=str(stock.qr_code_data)).status_code, 400)
        self.assertFalse(Transaction.objects.exists())

    def test_only_cashier_admin_and_post_with_csrf_are_allowed(self):
        for role in ('cliente', 'balcao'):
            user = User.objects.create_user(username='purchase-' + role, user_type=role)
            self.client.force_login(user)
            self.assertEqual(self.buy().status_code, 403)
        self.client.logout()
        self.assertEqual(self.buy().status_code, 302)
        admin = User.objects.create_user(username='purchase-admin', user_type='admin')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(admin)
        self.assertEqual(protected.post(self.url, '{}', content_type='application/json').status_code, 403)
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(self.buy().status_code, 200)

    def test_failure_after_inserting_sale_rolls_back_and_can_be_retried(self):
        original = Transaction.objects.create
        def fail_after_write(**kwargs):
            original(**kwargs)
            raise RuntimeError('simulated write failure')
        with patch('cards.views.Transaction.objects.create', side_effect=fail_after_write):
            with self.assertRaises(RuntimeError):
                self.buy()
        self.assertFalse(Transaction.objects.exists())
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('35.50'))
        self.assertTrue(self.buy().json()['created'])
        self.assertEqual(Transaction.objects.count(), 1)

    def test_sale_appears_in_reports_without_increasing_deposits_or_consumption(self):
        self.buy()
        self.buy()
        daily = self.client.get('/api/reports/daily/').json()
        self.assertEqual(Decimal(daily['total_depositos']), 0)
        self.assertEqual(Decimal(daily['total_vendas']), 0)
        self.assertEqual(Decimal(daily['vendas_cartoes']['total']), 2)
        self.assertEqual(daily['vendas_cartoes']['count'], 1)
        self.assertEqual(Decimal(daily['por_metodo'][0]['total']), 2)
        admin = User.objects.create_user(username='sale-report-admin', user_type='admin')
        self.client.force_login(admin)
        report = self.client.get('/api/reports/sales/').json()
        self.assertEqual(Decimal(report['vendas_cartoes']['total']), 2)
        self.assertEqual(Decimal(report['total_pagamentos_saldo']), 0)
        entries = self.client.get('/api/reports/transactions/').json()['transactions']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['tipo_label'], 'Venda de cartão físico')
