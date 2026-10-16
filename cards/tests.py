from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase, override_settings
from accounts.models import User
from .models import Card, Transaction, Recarga


class BalancePermissionsTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username='customer', user_type='cliente')
        self.card = self.customer.card

    def post(self, path, data):
        return self.client.post(path, data, content_type='application/json')

    def test_legacy_credit_is_disabled_for_every_role(self):
        for role in ('cliente', 'admin', 'caixa', 'balcao'):
            with self.subTest(role=role):
                user = User.objects.create_user(username=role, user_type=role)
                self.client.force_login(user)
                response = self.post('/api/cards/client/add/', {'valor': '10.00'})
                self.assertEqual(response.status_code, 410)
        self.assertFalse(Transaction.objects.exists())
        self.assertFalse(Card.objects.exclude(saldo=0).exists())

    def test_customer_and_counter_cannot_credit_cards(self):
        for role in ('cliente', 'balcao'):
            with self.subTest(role=role):
                user = User.objects.create_user(username=role, user_type=role)
                self.client.force_login(user)
                response = self.post('/api/cards/balance/add/', {
                    'qr_data': str(self.card.qr_code_data), 'valor': '10.00',
                })
                self.assertEqual(response.status_code, 403)
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, 0)
        self.assertFalse(Transaction.objects.exists())

    def test_cashier_and_admin_can_credit_cards(self):
        for role in ('caixa', 'admin'):
            user = User.objects.create_user(username=role, user_type=role)
            self.client.force_login(user)
            response = self.post('/api/cards/balance/add/', {
                'qr_data': str(self.card.qr_code_data), 'valor': '10.01',
            })
            self.assertEqual(response.status_code, 200)
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('20.02'))
        self.assertEqual(Transaction.objects.count(), 2)

    def test_anonymous_cannot_credit(self):
        response = self.post('/api/cards/balance/add/', {
            'qr_data': str(self.card.qr_code_data), 'valor': '10.00',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Transaction.objects.exists())


@override_settings(ASAAS_WEBHOOK_TOKEN='test-webhook-token')
class WebhookTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pix-user', user_type='cliente')
        self.card = self.user.card
        self.recarga = Recarga.objects.create(card=self.card, user=self.user,
            valor=Decimal('12.34'), asaas_payment_id='pay_test')
        self.payload = {'event': 'PAYMENT_CONFIRMED', 'payment': {
            'id': 'pay_test', 'value': '12.34', 'billingType': 'PIX', 'status': 'CONFIRMED',
        }}

    def send(self, token='test-webhook-token', payload=None):
        return self.client.post('/api/asaas/webhook/', self.payload if payload is None else payload,
            content_type='application/json', HTTP_ASAAS_ACCESS_TOKEN=token)

    def assert_unchanged(self):
        self.card.refresh_from_db()
        self.recarga.refresh_from_db()
        self.assertEqual(self.card.saldo, 0)
        self.assertEqual(self.recarga.status, 'pendente')
        self.assertFalse(Transaction.objects.exists())

    def test_missing_and_invalid_tokens(self):
        for token in ('', 'wrong'):
            self.assertEqual(self.send(token).status_code, 401)
        self.assert_unchanged()

    @override_settings(ASAAS_WEBHOOK_TOKEN='')
    def test_unconfigured_token_fails_closed(self):
        self.assertEqual(self.send('').status_code, 503)
        self.assert_unchanged()

    def test_invalid_payloads_and_amounts(self):
        for payload in ([], {'event': 'PAYMENT_RECEIVED'}, {'event': 'PAYMENT_RECEIVED', 'payment': []}):
            self.assertEqual(self.send(payload=payload).status_code, 400)
        for amount in ('NaN', 'Infinity', '-10', '0', '12.345', '15'):
            self.payload['payment']['value'] = amount
            self.assertEqual(self.send().status_code, 400)
        self.assert_unchanged()

    def test_wrong_payment_type_or_status(self):
        self.payload['payment']['billingType'] = 'BOLETO'
        self.assertEqual(self.send().status_code, 400)
        self.payload['payment']['billingType'] = 'PIX'
        self.payload['payment']['status'] = 'PENDING'
        self.assertEqual(self.send().status_code, 400)
        self.assert_unchanged()

    def test_confirmed_received_and_replays_credit_once(self):
        for event in ('PAYMENT_CONFIRMED', 'PAYMENT_RECEIVED', 'PAYMENT_RECEIVED'):
            self.payload['event'] = event
            self.payload['payment']['status'] = event.removeprefix('PAYMENT_')
            self.assertEqual(self.send().status_code, 200)
        self.card.refresh_from_db()
        self.recarga.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('12.34'))
        self.assertEqual(self.recarga.status, 'pago')
        self.assertEqual(Transaction.objects.count(), 1)

    def test_failure_rolls_back_credit_and_status(self):
        with patch('cards.views.Transaction.objects.create', side_effect=RuntimeError('simulated')):
            with self.assertRaises(RuntimeError):
                self.send()
        self.assert_unchanged()

    def test_blocked_or_reassigned_card_is_not_credited(self):
        self.card.bloqueado = True
        self.card.save()
        self.assertEqual(self.send().status_code, 409)
        self.card.bloqueado = False
        self.card.user = None
        self.card.save()
        self.assertEqual(self.send().status_code, 409)
        self.assert_unchanged()

    def test_other_events_are_ignored_and_get_is_not_allowed(self):
        self.assertEqual(self.send(payload={'event': 'PAYMENT_CREATED'}).status_code, 200)
        self.assertEqual(self.client.get('/api/asaas/webhook/').status_code, 405)
        self.assert_unchanged()


class BalanceIntegrityTests(TestCase):
    def setUp(self):
        self.cashier = User.objects.create_user(username='cashier', user_type='caixa')
        self.client.force_login(self.cashier)
        self.card = Card.objects.create(saldo=Decimal('20.25'), is_temporary=True, nome='Origem')
        self.destination = Card.objects.create(saldo=Decimal('1.10'), is_temporary=True, nome='Destino')

    def post(self, path, data):
        return self.client.post(path, data, content_type='application/json')

    def transfer(self):
        return self.post('/api/cards/transfer/', {
            'from_card_id': self.card.pk, 'to_qr_data': str(self.destination.qr_code_data),
        })

    def test_transfer_conserves_balance_and_records_both_sides(self):
        self.assertEqual(self.transfer().status_code, 200)
        self.card.refresh_from_db()
        self.destination.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('0.00'))
        self.assertEqual(self.destination.saldo, Decimal('21.35'))
        self.assertEqual(Transaction.objects.filter(valor=Decimal('20.25')).count(), 2)

    def test_transfer_failure_after_first_record_rolls_everything_back(self):
        create = Transaction.objects.create
        calls = []
        def fail_second(**kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                raise RuntimeError('simulated')
            return create(**kwargs)
        with patch('cards.views.Transaction.objects.create', side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                self.transfer()
        self.card.refresh_from_db()
        self.destination.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('20.25'))
        self.assertEqual(self.destination.saldo, Decimal('1.10'))
        self.assertFalse(Transaction.objects.exists())

    def test_transfer_overflow_and_same_card_do_not_change_balance(self):
        self.destination.saldo = Decimal('99999999.99')
        self.destination.save()
        self.assertEqual(self.transfer().status_code, 400)
        self.assertEqual(self.post('/api/cards/transfer/', {
            'from_card_id': self.card.pk, 'to_qr_data': str(self.card.qr_code_data),
        }).status_code, 400)
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('20.25'))
        self.assertFalse(Transaction.objects.exists())

    def test_invalid_amounts_do_not_move_money(self):
        for route in ('add', 'remove'):
            for value in ('NaN', 'Infinity', '-Infinity', '0', '-1', '0.001', '1.005', '100000000', True, None):
                with self.subTest(route=route, value=value):
                    response = self.post(f'/api/cards/balance/{route}/', {
                        'qr_data': str(self.card.qr_code_data), 'valor': value,
                    })
                    self.assertEqual(response.status_code, 400)
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('20.25'))
        self.assertFalse(Transaction.objects.exists())

    def test_deposit_and_withdrawal_failures_roll_back(self):
        for route in ('add', 'remove'):
            with self.subTest(route=route):
                with patch('cards.views.Transaction.objects.create', side_effect=RuntimeError('simulated')):
                    with self.assertRaises(RuntimeError):
                        self.post(f'/api/cards/balance/{route}/', {
                            'qr_data': str(self.card.qr_code_data), 'valor': '10.10',
                        })
                self.card.refresh_from_db()
                self.assertEqual(self.card.saldo, Decimal('20.25'))
        self.assertFalse(Transaction.objects.exists())

    def test_withdrawal_and_insufficient_balance(self):
        data = {'qr_data': str(self.card.qr_code_data), 'valor': '10.10'}
        self.assertEqual(self.post('/api/cards/balance/remove/', data).status_code, 200)
        data['valor'] = '10.16'
        self.assertEqual(self.post('/api/cards/balance/remove/', data).status_code, 400)
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('10.15'))
        self.assertEqual(Transaction.objects.count(), 1)

    def test_blocked_cards_reject_movements(self):
        self.card.bloqueado = True
        self.card.save()
        for route in ('add', 'remove'):
            self.assertEqual(self.post(f'/api/cards/balance/{route}/', {
                'qr_data': str(self.card.qr_code_data), 'valor': '1',
            }).status_code, 400)
        self.assertEqual(self.transfer().status_code, 400)
        self.assertFalse(Transaction.objects.exists())

    def test_temp_card_creation_and_reuse_roll_back_on_failure(self):
        count = Card.objects.count()
        for qr in ('', str(self.card.qr_code_data)):
            with patch('cards.views.Transaction.objects.create', side_effect=RuntimeError('simulated')):
                with self.assertRaises(RuntimeError):
                    self.post('/api/cards/temp/create/', {'nome': 'Novo', 'valor': '10.01', 'qr_data': qr})
        self.assertEqual(Card.objects.count(), count)
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('20.25'))
        self.assertEqual(self.card.nome, 'Origem')

    def test_cancellation_rolls_back_record_if_card_save_fails(self):
        with patch('cards.views.Card.save', side_effect=RuntimeError('simulated')):
            with self.assertRaises(RuntimeError):
                self.post('/api/cards/block/', {'card_id': self.card.pk})
        self.card.refresh_from_db()
        self.assertEqual(self.card.saldo, Decimal('20.25'))
        self.assertFalse(self.card.bloqueado)
        self.assertFalse(Transaction.objects.exists())

    def test_cancel_and_reuse_physical_card(self):
        self.assertEqual(self.post('/api/cards/block/', {'card_id': self.card.pk}).status_code, 200)
        self.card.refresh_from_db()
        self.assertTrue(self.card.bloqueado)
        self.assertEqual(self.card.saldo, 0)
        self.assertEqual(self.post('/api/cards/temp/create/', {
            'nome': 'Novo', 'valor': '1.01', 'qr_data': str(self.card.qr_code_data),
        }).status_code, 200)
        self.card.refresh_from_db()
        self.assertFalse(self.card.bloqueado)
        self.assertEqual(self.card.saldo, Decimal('1.01'))
        self.assertEqual(Transaction.objects.count(), 2)

    def test_malformed_json_uuid_and_method_do_not_write(self):
        for payload in ('{', '[]'):
            self.assertEqual(self.client.post('/api/cards/balance/add/', payload,
                content_type='application/json').status_code, 400)
        for data in ({'qr_data': 'invalid', 'valor': '1'},
                     {'qr_data': str(self.card.qr_code_data), 'valor': '1', 'metodo': 'saldo'}):
            self.assertEqual(self.post('/api/cards/balance/add/', data).status_code, 400)
        self.assertFalse(Transaction.objects.exists())


class PixCreationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='pix-customer', user_type='cliente',
                                             asaas_customer_id='cus_test')
        self.client.force_login(self.user)

    def request_payment(self, amount):
        return self.client.post('/api/asaas/create-payment/', {'valor': amount},
                                content_type='application/json')

    def test_invalid_amounts_are_rejected_before_calling_provider(self):
        with patch('cards.views.http_requests.post') as post:
            for value in ('0.99', 'NaN', 'Infinity', '-1', '1.005', '100000000'):
                with self.subTest(value=value):
                    self.assertEqual(self.request_payment(value).status_code, 400)
            post.assert_not_called()
        self.assertFalse(Recarga.objects.exists())

    def test_creating_pix_does_not_credit_card(self):
        with patch('cards.views.http_requests.post') as post, patch('cards.views.http_requests.get') as get:
            post.return_value.status_code = 200
            post.return_value.json.return_value = {'id': 'pay_created'}
            get.return_value.json.return_value = {'encodedImage': 'image', 'payload': 'pix-code'}
            response = self.request_payment('12.34')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(post.call_args.kwargs['json']['value'], 12.34)
        recarga = Recarga.objects.get()
        self.assertEqual(recarga.valor, Decimal('12.34'))
        self.assertEqual(recarga.status, 'pendente')
        self.assertEqual(Card.objects.get(user=self.user).saldo, 0)
        self.assertFalse(Transaction.objects.exists())
