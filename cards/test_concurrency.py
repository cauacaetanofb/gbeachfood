"""Testes de bloqueio real: exigem banco com SELECT FOR UPDATE (ex.: PostgreSQL)."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from django.db import close_old_connections
from django.test import Client, TransactionTestCase, override_settings, skipUnlessDBFeature
from accounts.models import User
from .models import Recarga, Transaction


@skipUnlessDBFeature('has_select_for_update')
@override_settings(ASAAS_WEBHOOK_TOKEN='test-webhook-token')
class ConcurrentBalanceTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='customer', user_type='cliente')
        self.cashier = User.objects.create_user(username='cashier', user_type='caixa')
        self.card = self.user.card
        self.card.saldo = Decimal('20.00')
        self.card.save()

    def parallel(self, path, payload, authenticated=False):
        barrier = Barrier(2)
        def send(_):
            close_old_connections()
            try:
                client = Client()
                if authenticated:
                    client.force_login(User.objects.get(pk=self.cashier.pk))
                barrier.wait(timeout=10)
                return client.post(path, payload, content_type='application/json',
                    HTTP_ASAAS_ACCESS_TOKEN='test-webhook-token').status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return sorted(pool.map(send, range(2)))

    def test_simultaneous_withdrawals_cannot_overdraw(self):
        statuses = self.parallel('/api/cards/balance/remove/', {
            'qr_data': str(self.card.qr_code_data), 'valor': '15.00',
        }, authenticated=True)
        self.assertEqual(statuses, [200, 400])
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('5.00'))
        self.assertEqual(Transaction.objects.count(), 1)

    def test_simultaneous_webhooks_credit_once(self):
        Recarga.objects.create(card=self.card, user=self.user, valor=Decimal('1.23'),
                               asaas_payment_id='pay_concurrent')
        statuses = self.parallel('/api/asaas/webhook/', {
            'event': 'PAYMENT_RECEIVED', 'payment': {'id': 'pay_concurrent',
            'value': '1.23', 'billingType': 'PIX', 'status': 'RECEIVED'},
        })
        self.assertEqual(statuses, [200, 200])
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('21.23'))
        self.assertEqual(Transaction.objects.count(), 1)
