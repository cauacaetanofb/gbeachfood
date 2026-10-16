from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase
from accounts.models import User
from cards.models import Card, Transaction
from products.models import Product
from .models import Order, OrderItem


class OrderIntegrityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='counter', user_type='balcao')
        self.client.force_login(self.user)
        self.card = Card.objects.create(saldo=Decimal('20.00'))
        self.product = Product.objects.create(nome='Produto', preco=Decimal('3.33'))

    def buy(self, quantity=2):
        return self.client.post('/api/orders/create/', {
            'qr_data': str(self.card.qr_code_data),
            'items': [{'product_id': self.product.pk, 'quantidade': quantity}],
        }, content_type='application/json')

    def assert_no_purchase(self):
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('20.00'))
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
        self.assertFalse(Transaction.objects.exists())

    def test_order_uses_exact_prices_from_database(self):
        response = self.buy()
        self.assertEqual(response.status_code, 200)
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('13.34'))
        self.assertEqual(Order.objects.get().total, Decimal('6.66'))
        self.assertEqual(Transaction.objects.get().valor, Decimal('6.66'))

    def test_order_and_debit_roll_back_when_ledger_fails(self):
        with patch('orders.views.Transaction.objects.create', side_effect=RuntimeError('simulated')):
            with self.assertRaises(RuntimeError):
                self.buy()
        self.assert_no_purchase()

    def test_order_rolls_back_when_item_fails(self):
        with patch('orders.views.OrderItem.objects.create', side_effect=RuntimeError('simulated')):
            with self.assertRaises(RuntimeError):
                self.buy()
        self.assert_no_purchase()

    def test_invalid_quantities_and_insufficient_balance(self):
        for qty in (0, -1, 1.5, True, None, 'NaN', 100, 2147483648):
            with self.subTest(qty=qty):
                self.assertEqual(self.buy(qty).status_code, 400)
                self.assert_no_purchase()

    def test_blocked_card_rejected(self):
        self.card.bloqueado = True
        self.card.save()
        self.assertEqual(self.buy().status_code, 400)
        self.assert_no_purchase()
