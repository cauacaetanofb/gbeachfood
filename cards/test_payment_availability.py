from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings

from accounts.models import User
from .models import Recarga, Transaction


@override_settings(ASAAS_PAYMENTS_ENABLED=False)
class PaymentAvailabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='paused-customer', user_type='cliente')
        self.card = self.user.card
        self.client.force_login(self.user)

    def assert_creation_blocked(self):
        with patch('cards.views.http_requests.post') as post, patch('cards.views.http_requests.get') as get:
            for method in ('pix', 'credito'):
                for _ in range(2):
                    response = self.client.post('/api/asaas/create-payment/',
                        {'valor': '20.00', 'metodo': method}, content_type='application/json')
                    self.assertEqual(response.status_code, 503)
                    self.assertEqual(response.json()['code'], 'payments_disabled')
            post.assert_not_called()
            get.assert_not_called()
        self.card.refresh_from_db()
        self.user.refresh_from_db()
        self.assertEqual(self.card.saldo, 0)
        self.assertFalse(self.user.asaas_customer_id)
        self.assertFalse(Recarga.objects.exists())
        self.assertFalse(Transaction.objects.exists())

    def test_paused_payments_and_retries_never_call_provider_or_write_money(self):
        self.assert_creation_blocked()

    @override_settings(ASAAS_PAYMENTS_ENABLED=True, ASAAS_API_KEY='')
    def test_missing_key_also_blocks_creation(self):
        self.assert_creation_blocked()
        self.assertContains(self.client.get('/dashboard/'), 'Recarga no caixa')

    @override_settings(ASAAS_PAYMENTS_ENABLED=True)
    def test_incomplete_or_unsafe_configuration_blocks_payments_and_pending_links(self):
        recarga = Recarga.objects.create(card=self.card, user=self.user, valor=Decimal('20.00'),
            metodo='credito', asaas_payment_id='pay_config',
            invoice_url='https://www.asaas.com/i/config')
        configurations = (
            {'ASAAS_WEBHOOK_TOKEN': ''},
            {'ASAAS_WEBHOOK_TOKEN': '   '},
            {'ASAAS_API_KEY': 'same-secret', 'ASAAS_WEBHOOK_TOKEN': 'same-secret'},
            {'ASAAS_BASE_URL': 'http://api.asaas.com/v3'},
            {'ASAAS_BASE_URL': 'https://api.asaas.com.evil.example/v3'},
            {'ASAAS_BASE_URL': 'https://user:secret@api.asaas.com/v3'},
            {'ASAAS_BASE_URL': 'https://api.asaas.com/v3?token=secret'},
            {'ASAAS_BASE_URL': 'https://api.asaas.com/v3#fragment'},
        )
        with patch('cards.views.http_requests.post') as post, patch('cards.views.http_requests.get') as get:
            for configuration in configurations:
                with self.subTest(configuration=list(configuration)), override_settings(**configuration):
                    for method in ('pix', 'credito'):
                        for _ in range(2):
                            response = self.client.post('/api/asaas/create-payment/',
                                {'valor': '20.00', 'metodo': method}, content_type='application/json')
                            self.assertEqual(response.status_code, 503)
                            self.assertEqual(response.json()['code'], 'payments_disabled')
                    self.assertContains(self.client.get('/dashboard/'), 'Recarga no caixa')
                    self.assertEqual(self.client.get('/api/asaas/pending-payments/').json()['recargas'], [])
            post.assert_not_called()
            get.assert_not_called()
        self.card.refresh_from_db()
        recarga.refresh_from_db()
        self.assertEqual(self.card.saldo, 0)
        self.assertEqual(recarga.status, 'pendente')
        self.assertEqual(Recarga.objects.count(), 1)
        self.assertFalse(Transaction.objects.exists())

    @override_settings(ASAAS_PAYMENTS_ENABLED=True, ASAAS_API_KEY='private-api-secret',
                       ASAAS_WEBHOOK_TOKEN='private-webhook-secret')
    def test_dashboard_does_not_expose_credentials(self):
        response = self.client.get('/dashboard/')
        self.assertContains(response, 'id="add-metodo"')
        self.assertNotContains(response, 'private-api-secret')
        self.assertNotContains(response, 'private-webhook-secret')

    def test_customer_dashboard_keeps_card_and_balance_without_payment_controls(self):
        response = self.client.get('/dashboard/')
        self.assertContains(response, 'Recarga no caixa')
        self.assertContains(response, 'Procure o caixa para adicionar saldo.')
        self.assertContains(response, 'id="my-saldo"')
        self.assertContains(response, 'id="my-qr-img"')
        self.assertNotContains(response, 'id="add-metodo"')
        self.assertNotContains(response, 'id="credit-payment-link"')
        self.assertNotContains(response, 'sem passar no caixa')
        with override_settings(ASAAS_PAYMENTS_ENABLED=True):
            response = self.client.get('/dashboard/')
            self.assertContains(response, 'id="add-metodo"')
            self.assertNotContains(response, 'Recarga no caixa')

    def test_pause_hides_pending_links_without_losing_record_or_status(self):
        recarga = Recarga.objects.create(card=self.card, user=self.user, valor=Decimal('20.00'),
            metodo='credito', asaas_payment_id='pay_paused',
            invoice_url='https://www.asaas.com/i/paused')
        self.assertEqual(self.client.get('/api/asaas/pending-payments/').json()['recargas'], [])
        response = self.client.get(f'/api/asaas/check-payment/{recarga.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'pendente')
        recarga.refresh_from_db()
        self.assertEqual(recarga.status, 'pendente')
        with override_settings(ASAAS_PAYMENTS_ENABLED=True):
            pending = self.client.get('/api/asaas/pending-payments/').json()['recargas']
            self.assertEqual([item['id'] for item in pending], [recarga.pk])

    def test_pause_preserves_staff_permission_checks(self):
        for role in ('admin', 'caixa', 'balcao'):
            user = User.objects.create_user(username=f'paused-{role}', user_type=role)
            self.client.force_login(user)
            response = self.client.post('/api/asaas/create-payment/',
                {'valor': '20.00', 'metodo': 'credito'}, content_type='application/json')
            self.assertEqual(response.status_code, 403)
            self.assertEqual(self.client.get('/api/asaas/pending-payments/').status_code, 403)
