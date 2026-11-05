from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase

from accounts.models import User
from .models import Card, CardIssuance, Transaction


class LabelIssuanceTests(TestCase):
    def setUp(self):
        self.cashier = User.objects.create_user(username='label-cashier', user_type='caixa')
        self.client.force_login(self.cashier)
        self.payload = {'request_id': str(uuid4()), 'nome': 'Visitante de teste', 'cpf': '000.000.001-91',
                        'telefone': '(27) 99999-0000', 'valor': '50.00', 'metodo': 'pix',
                        'incluir_cartao_fisico': False}

    def create(self, **changes):
        return self.client.post('/api/cards/temp/create/', {**self.payload, **changes}, content_type='application/json')

    def test_label_only_credits_exact_initial_balance_without_a_user_account(self):
        response = self.create()
        self.assertEqual(response.status_code, 200)
        card = Card.objects.get()
        self.assertIsNone(card.user_id)
        self.assertTrue(card.is_temporary)
        self.assertEqual(card.saldo, Decimal('50.00'))
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(response.json()['total_cobrado'], '50.00')
        self.assertEqual(response.json()['valor_cartao'], '0.00')
        self.assertEqual(Transaction.objects.get().tipo, 'deposito')

    def test_physical_card_is_two_reais_extra_and_never_changes_consumption_balance(self):
        response = self.create(incluir_cartao_fisico=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['total_cobrado'], '52.00')
        self.assertEqual(Card.objects.get().saldo, Decimal('50.00'))
        self.assertEqual(Transaction.objects.get(tipo='deposito').valor, Decimal('50.00'))
        sale = Transaction.objects.get(tipo='cartao')
        self.assertEqual((sale.valor, sale.metodo, sale.origem, sale.operador_id),
                         (Decimal('2.00'), 'pix', 'caixa', self.cashier.pk))

    def test_same_request_retries_do_not_duplicate_cards_credit_or_card_sale(self):
        first = self.create(incluir_cartao_fisico=True).json()
        second = self.create(incluir_cartao_fisico=True).json()
        self.assertTrue(first['created'])
        self.assertFalse(second['created'])
        self.assertEqual(first['card']['qr_code_data'], second['card']['qr_code_data'])
        self.assertEqual(Card.objects.count(), 1)
        self.assertEqual(CardIssuance.objects.count(), 1)
        self.assertEqual(Transaction.objects.count(), 2)
        self.assertEqual(Card.objects.get().saldo, Decimal('50.00'))

    def test_conflicting_retry_cannot_change_amount_person_or_operator(self):
        self.create()
        for changes in ({'nome': 'Outra pessoa'}, {'valor': '60'}, {'incluir_cartao_fisico': True}):
            self.assertEqual(self.create(**changes).status_code, 409)
        other = User.objects.create_user(username='other-cashier', user_type='caixa')
        self.client.force_login(other)
        self.assertEqual(self.create().status_code, 409)
        self.assertEqual(Card.objects.get().nome, 'Visitante de teste')
        self.assertEqual(Transaction.objects.count(), 1)

    def test_second_transaction_failure_rolls_back_card_initial_credit_and_issue(self):
        original = Transaction.objects.create
        def fail_sale(**kwargs):
            if kwargs['tipo'] == 'cartao':
                raise RuntimeError('sale failure')
            return original(**kwargs)
        with patch('cards.views.Transaction.objects.create', side_effect=fail_sale):
            with self.assertRaises(RuntimeError):
                self.create(incluir_cartao_fisico=True)
        self.assertFalse(Card.objects.exists())
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(CardIssuance.objects.exists())
        self.assertEqual(self.create(incluir_cartao_fisico=True).status_code, 200)

    def test_render_failure_during_creation_rolls_back_then_retry_is_safe(self):
        with patch('cards.views.generate_qr_base64', side_effect=RuntimeError('render failure')):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertFalse(Card.objects.exists())
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(CardIssuance.objects.exists())

    def test_input_validation_rejects_price_tampering_manual_qr_and_bad_values(self):
        for changes in ({'valor_cartao': '0.01'}, {'qr_data': str(uuid4())}, {'request_id': ''},
                        {'request_id': 'invalid'}, {'incluir_cartao_fisico': 'true'},
                        {'incluir_cartao_fisico': 1}, {'valor': '0'}, {'valor': 'NaN'},
                        {'valor': '1.001'}, {'metodo': 'saldo'}, {'nome': '  '}, {'cpf': '123'}):
            with self.subTest(changes=changes):
                self.assertEqual(self.create(**changes).status_code, 400)
        self.assertFalse(Card.objects.exists())
        self.assertFalse(Transaction.objects.exists())

    def test_get_print_and_reprint_only_read_existing_card_and_do_not_expose_cpf(self):
        created = self.create(incluir_cartao_fisico=True).json()
        card = Card.objects.get()
        for _ in range(2):
            response = self.client.get(created['card']['label_url'])
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, str(card.qr_code_data))
            self.assertNotContains(response, card.nome)
            self.assertNotContains(response, card.cpf)
            self.assertNotContains(response, card.telefone)
            self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(Card.objects.count(), 1)
        self.assertEqual(Transaction.objects.count(), 2)
        card.refresh_from_db()
        self.assertEqual(card.saldo, Decimal('50.00'))

    def test_failed_print_can_be_retried_without_issuing_again(self):
        url = self.create().json()['card']['label_url']
        with patch('cards.views.generate_qr_base64', side_effect=RuntimeError('print failure')):
            with self.assertRaises(RuntimeError):
                self.client.get(url)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(Card.objects.count(), 1)
        self.assertEqual(Transaction.objects.count(), 1)

    def test_cancelled_or_personal_card_cannot_print_and_cancelled_issue_cannot_recharge(self):
        url = self.create().json()['card']['label_url']
        card = Card.objects.get()
        card.bloqueado = True
        card.save()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.create().status_code, 409)
        self.assertEqual(Transaction.objects.count(), 1)
        customer = User.objects.create_user(username='personal', user_type='cliente')
        self.assertEqual(self.client.get(f'/cards/{customer.card.pk}/label/').status_code, 404)

    def test_cashier_admin_permissions_and_csrf(self):
        url = self.create().json()['card']['label_url']
        for role in ('cliente', 'balcao'):
            user = User.objects.create_user(username='labels-' + role, user_type=role)
            self.client.force_login(user)
            self.assertEqual(self.create(request_id=str(uuid4())).status_code, 403)
            self.assertEqual(self.client.get(url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)
        admin = User.objects.create_user(username='labels-admin', user_type='admin')
        self.client.force_login(admin)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.create(request_id=str(uuid4())).status_code, 200)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(admin)
        self.assertEqual(protected.post('/api/cards/temp/create/', self.payload, content_type='application/json').status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 405)

    def test_reports_show_sale_separately_and_received_total_includes_it_once(self):
        self.create(incluir_cartao_fisico=True)
        self.create(incluir_cartao_fisico=True)
        daily = self.client.get('/api/reports/daily/').json()
        self.assertEqual(Decimal(daily['total_depositos']), 50)
        self.assertEqual(Decimal(daily['total_vendas']), 0)
        self.assertEqual(daily['vendas_cartoes']['count'], 1)
        self.assertEqual(Decimal(daily['vendas_cartoes']['total']), 2)
        self.assertEqual(Decimal(daily['por_metodo'][0]['total']), 52)
        admin = User.objects.create_user(username='report-admin', user_type='admin')
        self.client.force_login(admin)
        report = self.client.get('/api/reports/sales/').json()
        self.assertEqual(Decimal(report['total_depositos']), 50)
        self.assertEqual(Decimal(report['total_pagamentos_saldo']), 0)
        self.assertEqual(Decimal(report['vendas_cartoes']['total']), 2)
        entries = self.client.get('/api/reports/transactions/').json()['transactions']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['tipo_label'], 'Venda de cartão físico')
        self.assertEqual(Decimal(entries[0]['valor']), 2)


class LabelMigrationTests(TransactionTestCase):
    def test_upgrade_preserves_preexisting_cards_and_transactions_after_code_revert(self):
        previous = [('cards', '0008_card_vinculo_version_cardprintbatch_card_print_batch_and_more')]
        current = [('cards', '0009_temp_card_labels')]
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            old = executor.loader.project_state(previous).apps
            batch = old.get_model('cards', 'CardPrintBatch').objects.create(quantidade=1)
            card = old.get_model('cards', 'Card').objects.create(
                print_batch=batch, is_temporary=True, nome='Visitante anterior', saldo=Decimal('12.34'))
            entry = old.get_model('cards', 'Transaction').objects.create(card=card, tipo='deposito', valor=Decimal('12.34'))
            MigrationExecutor(connection).migrate(current)
            restored = Card.objects.get(pk=card.pk)
            self.assertEqual(restored.saldo, Decimal('12.34'))
            self.assertEqual(restored.qr_code_data, card.qr_code_data)
            self.assertEqual(restored.nome, 'Visitante anterior')
            self.assertTrue(Transaction.objects.filter(pk=entry.pk, card=restored).exists())
            Card.objects.create(is_temporary=True, nome='Novo visitante')
        finally:
            MigrationExecutor(connection).migrate(current)
