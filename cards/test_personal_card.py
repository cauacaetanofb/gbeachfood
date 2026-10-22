from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from accounts.models import User
from .models import Card, Recarga, Transaction


class PersonalCardPermissionsTests(TestCase):
    def test_staff_have_no_card_or_personal_dashboard(self):
        for role in ('admin', 'balcao', 'caixa'):
            with self.subTest(role=role):
                user = User.objects.create_user(username=role, user_type=role)
                self.assertFalse(Card.objects.filter(user=user).exists())
                self.client.force_login(user)
                for suffix in ('', '?as=cliente'):
                    response = self.client.get('/dashboard/' + suffix)
                    self.assertEqual(response.status_code, 200)
                    self.assertTemplateUsed(response, f'dashboard_{role}.html')
                    self.assertNotContains(response, 'Meu Cartão')
                    self.assertNotContains(response, 'Meu cartão')
                    self.assertNotContains(response, '?as=cliente')
                self.assertFalse(Card.objects.filter(user=user).exists())

    @patch('cards.views.http_requests.post')
    def test_staff_cannot_access_personal_apis_or_create_pix(self, external_post):
        for role in ('admin', 'balcao', 'caixa'):
            with self.subTest(role=role):
                user = User.objects.create_user(username=role, user_type=role)
                self.client.force_login(user)
                for path in ('/api/cards/my/', '/api/cards/my/transactions/',
                             '/api/asaas/check-payment/1/'):
                    self.assertEqual(self.client.get(path).status_code, 403)
                response = self.client.post('/api/asaas/create-payment/',
                    {'valor': '10.00'}, content_type='application/json')
                self.assertEqual(response.status_code, 403)
                self.assertFalse(Card.objects.filter(user=user).exists())
        external_post.assert_not_called()
        self.assertFalse(Recarga.objects.exists())

    def test_legacy_staff_card_does_not_grant_personal_access_or_lose_history(self):
        user = User.objects.create_user(username='old-admin', user_type='admin')
        card = Card.objects.create(user=user, saldo=Decimal('25.00'))
        entry = Transaction.objects.create(card=card, tipo='deposito', valor=Decimal('25.00'))
        self.client.force_login(user)
        self.client.get('/dashboard/?as=cliente')
        self.assertEqual(self.client.get('/api/cards/my/').status_code, 403)
        self.assertEqual(self.client.get('/api/cards/my/transactions/').status_code, 403)
        card.refresh_from_db()
        self.assertEqual(card.saldo, Decimal('25.00'))
        self.assertTrue(Transaction.objects.filter(pk=entry.pk).exists())

    def test_customer_keeps_card_dashboard_balance_and_payment_status(self):
        user = User.objects.create_user(username='customer', user_type='cliente')
        card = user.card
        self.client.force_login(user)
        response = self.client.get('/dashboard/')
        self.assertTemplateUsed(response, 'dashboard_cliente.html')
        self.assertContains(response, 'Meu cartão')
        response = self.client.get('/api/cards/my/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['card']['id'], card.pk)
        self.assertEqual(self.client.get('/api/cards/my/transactions/').status_code, 200)
        recarga = Recarga.objects.create(card=card, user=user, valor=Decimal('10.00'),
                                        asaas_payment_id='pay_customer')
        self.assertEqual(self.client.get(f'/api/asaas/check-payment/{recarga.pk}/').status_code, 200)

    def test_admin_retains_operational_dashboards(self):
        user = User.objects.create_user(username='admin', user_type='admin')
        self.client.force_login(user)
        for role in ('admin', 'caixa', 'balcao'):
            response = self.client.get('/dashboard/?as=' + role)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, f'dashboard_{role}.html')
        self.assertFalse(Card.objects.filter(user=user).exists())
