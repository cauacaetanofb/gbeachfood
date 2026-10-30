from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, override_settings
from accounts.models import User
from .models import Card, Recarga, Transaction


@override_settings(ASAAS_API_KEY='test-key', ASAAS_WEBHOOK_TOKEN='test-token')
class CreditPaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='credit-client', user_type='cliente', asaas_customer_id='cus_credit')
        self.card = self.user.card
        self.client.force_login(self.user)

    def create_payment(self, **changes):
        return self.client.post('/api/asaas/create-payment/',
            {'valor': '20.00', 'metodo': 'credito', **changes}, content_type='application/json')

    def recharge(self):
        return Recarga.objects.create(card=self.card, user=self.user, valor=Decimal('20.00'),
            asaas_payment_id='pay_credit', metodo='credito', invoice_url='https://www.asaas.com/i/credit')

    def webhook(self, event='PAYMENT_CONFIRMED', **changes):
        payment = {'id': 'pay_credit', 'billingType': 'CREDIT_CARD', 'value': '20.00',
                   'status': event.removeprefix('PAYMENT_'), **changes}
        return self.client.post('/api/asaas/webhook/', {'event': event, 'payment': payment},
            content_type='application/json', HTTP_ASAAS_ACCESS_TOKEN='test-token')

    @patch('cards.views.http_requests.get')
    @patch('cards.views.http_requests.post')
    def test_hosted_credit_creates_pending_without_credit_or_card_details(self, post, get):
        post.return_value.status_code = 200
        post.return_value.json.return_value = {'id': 'pay_credit', 'invoiceUrl': 'https://www.asaas.com/i/credit'}
        response = self.create_payment()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['invoice_url'], 'https://www.asaas.com/i/credit')
        payload = post.call_args.kwargs['json']
        self.assertEqual(payload['billingType'], 'CREDIT_CARD')
        self.assertEqual(payload['customer'], 'cus_credit')
        self.assertEqual(payload['value'], 20.0)
        self.assertTrue({'creditCard', 'creditCardHolderInfo', 'installmentCount', 'split'}.isdisjoint(payload))
        get.assert_not_called()
        self.assertEqual(Recarga.objects.get().metodo, 'credito')
        self.assertEqual(Recarga.objects.get().status, 'pendente')
        self.assertEqual(Card.objects.get(pk=self.card.pk).saldo, 0)
        self.assertFalse(Transaction.objects.exists())

    @patch('cards.views.http_requests.post')
    def test_invalid_values_methods_installments_and_card_details_never_reach_provider(self, post):
        for data in ({'valor': '4.99'}, {'valor': 'NaN'}, {'metodo': 'boleto'},
                     {'installmentCount': 2}, {'creditCard': {'number': 'test-only'}}):
            with self.subTest(data=data):
                self.assertEqual(self.create_payment(**data).status_code, 400)
        self.card.bloqueado = True
        self.card.save()
        self.assertEqual(self.create_payment().status_code, 400)
        post.assert_not_called()

    @patch('cards.views.http_requests.post')
    def test_staff_cannot_create_credit_or_list_pending(self, post):
        for role in ('admin', 'caixa', 'balcao'):
            self.user.user_type = role
            self.user.save()
            self.assertEqual(self.create_payment().status_code, 403)
            self.assertEqual(self.client.get('/api/asaas/pending-payments/').status_code, 403)
        post.assert_not_called()

    @patch('cards.views.http_requests.post')
    def test_provider_failure_is_not_exposed_or_credited(self, post):
        post.side_effect = RuntimeError('sensitive provider detail')
        response = self.create_payment()
        self.assertEqual(response.status_code, 502)
        self.assertNotContains(response, 'sensitive provider detail', status_code=502)
        self.assertFalse(Recarga.objects.exists())
        self.assertFalse(Transaction.objects.exists())

    @patch('cards.views.http_requests.post')
    def test_untrusted_invoice_link_is_never_returned(self, post):
        post.return_value.status_code = 200
        for i, url in enumerate(('javascript:alert(1)', 'http://www.asaas.com/i/a',
                                 'https://asaas.com.evil.example/i/a', 'https://user@www.asaas.com/i/a')):
            post.return_value.json.return_value = {'id': f'pay_{i}', 'invoiceUrl': url}
            self.assertEqual(self.create_payment().status_code, 502)
        self.assertEqual(Recarga.objects.count(), 4)  # Keep payment ids for reconciliation.
        self.assertEqual(self.client.get('/api/asaas/pending-payments/').json()['recargas'], [])
        self.assertFalse(Transaction.objects.exists())

    def test_confirmed_and_received_credit_gross_value_only_once(self):
        self.recharge()
        for event in ('PAYMENT_CONFIRMED', 'PAYMENT_CONFIRMED', 'PAYMENT_RECEIVED'):
            self.assertEqual(self.webhook(event, netValue='18.50').status_code, 200)
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('20.00'))
        entry = Transaction.objects.get()
        self.assertEqual(entry.metodo, 'credito')
        self.assertEqual(entry.valor, Decimal('20.00'))
        self.assertEqual(Recarga.objects.get().status, 'pago')

    def test_unpaid_authorized_risk_and_refused_events_do_not_credit(self):
        self.recharge()
        for event in ('PAYMENT_CREATED', 'PAYMENT_AUTHORIZED', 'PAYMENT_AWAITING_RISK_ANALYSIS',
                      'PAYMENT_APPROVED_BY_RISK_ANALYSIS', 'PAYMENT_REPROVED_BY_RISK_ANALYSIS',
                      'PAYMENT_CREDIT_CARD_CAPTURE_REFUSED'):
            self.assertEqual(self.webhook(event).status_code, 200)
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(Recarga.objects.get().status, 'pendente')
        self.assertEqual(self.webhook(status='PENDING').status_code, 400)
        self.assertEqual(self.webhook(billingType='PIX').status_code, 400)
        self.assertEqual(self.webhook(value='19.99').status_code, 400)

    def test_credit_cannot_confirm_an_old_pix_recharge(self):
        r = self.recharge()
        r.metodo = 'pix'
        r.save()
        self.assertEqual(self.webhook().status_code, 400)
        self.assertFalse(Transaction.objects.exists())

    def test_write_failure_rolls_back_credit_and_status(self):
        self.recharge()
        with patch('cards.views.Transaction.objects.create', side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError): self.webhook()
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, 0)
        self.assertEqual(Recarga.objects.get().status, 'pendente')

    def test_refund_and_chargeback_block_for_review_without_double_credit(self):
        r = self.recharge()
        self.webhook()
        for event in ('PAYMENT_CHARGEBACK_REQUESTED', 'PAYMENT_CHARGEBACK_DISPUTE',
                      'PAYMENT_REFUND_IN_PROGRESS', 'PAYMENT_PARTIALLY_REFUNDED', 'PAYMENT_REFUNDED',
                      'PAYMENT_AWAITING_CHARGEBACK_REVERSAL', 'PAYMENT_CONFIRMED', 'PAYMENT_RECEIVED'):
            self.assertEqual(self.webhook(event).status_code, 200)
        self.card.refresh_from_db()
        r.refresh_from_db()
        self.assertTrue(self.card.bloqueado)
        self.assertEqual(r.status, 'revisao')
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(self.card.saldo, Decimal('20.00'))
        self.assertTrue(self.client.get('/api/cards/my/').json()['card']['bloqueado'])
        self.assertEqual(self.client.get(f'/api/asaas/check-payment/{r.pk}/').json()['status'], 'revisao')
        self.assertEqual(self.client.get('/api/asaas/pending-payments/').json()['recargas'], [])

    def test_refund_before_confirmation_prevents_late_credit(self):
        self.recharge()
        self.webhook('PAYMENT_REFUNDED')
        self.webhook()
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(Recarga.objects.get().status, 'revisao')

    def test_pending_links_and_status_are_private_to_customer(self):
        r = self.recharge()
        other = User.objects.create_user(username='other-client', user_type='cliente')
        foreign = Recarga.objects.create(card=other.card, user=other, valor=10, metodo='credito',
            asaas_payment_id='pay_other', invoice_url='https://www.asaas.com/i/other')
        result = self.client.get('/api/asaas/pending-payments/').json()['recargas']
        self.assertEqual([item['id'] for item in result], [r.pk])
        self.assertEqual(self.client.get(f'/api/asaas/check-payment/{foreign.pk}/').status_code, 404)
        self.assertEqual(self.client.post('/api/asaas/pending-payments/').status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get('/api/asaas/pending-payments/').status_code, 302)
