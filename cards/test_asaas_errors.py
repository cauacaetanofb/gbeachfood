"""Falhas do Asaas não podem virar acusações incorretas ao CPF nem crédito local."""
from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings

from accounts.models import User
from .models import Recarga, Transaction


@override_settings(ASAAS_API_KEY='test-key', ASAAS_BASE_URL='https://api-sandbox.asaas.com/v3')
class AsaasErrorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='payer-test', user_type='cliente',
                                             cpf='000.000.001-91', email='payer@example.test')
        self.client.force_login(self.user)

    def create_payment(self):
        return self.client.post('/api/asaas/create-payment/',
                                {'valor': '20.00', 'metodo': 'credito'}, content_type='application/json')

    @staticmethod
    def provider_response(status, data):
        return Mock(status_code=status, json=Mock(return_value=data))

    def assert_no_payment(self):
        self.assertFalse(Recarga.objects.exists())
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(self.user.card.saldo, 0)

    @patch('cards.views.http_requests.post')
    def test_authentication_failure_is_configuration_error_with_or_without_customer(self, post):
        for customer_id in ('', 'cus_existing'):
            for status in (401, 403):
                with self.subTest(customer=bool(customer_id), status=status):
                    self.user.asaas_customer_id = customer_id
                    self.user.save(update_fields=['asaas_customer_id'])
                    response = self.provider_response(status, None)
                    response.json.side_effect = ValueError('sensitive provider detail')
                    post.return_value = response
                    with self.assertLogs('cards.views', level='WARNING') as logs:
                        result = self.create_payment()
                    self.assertEqual(result.status_code, 503)
                    self.assertEqual(result.json()['code'], 'asaas_authentication')
                    self.assertIn('configuração', result.json()['error'])
                    self.assertNotIn('CPF', result.json()['error'])
                    self.assertNotIn('sensitive', result.content.decode())
                    self.assertNotIn('test-key', ' '.join(logs.output))
                    self.assertNotIn(self.user.cpf, ' '.join(logs.output))
                    response.json.assert_not_called()
        self.assert_no_payment()

    @patch('cards.views.http_requests.post')
    def test_missing_cpf_is_profile_error_before_provider_request(self, post):
        self.user.cpf = ''
        self.user.save(update_fields=['cpf'])
        result = self.create_payment()
        self.assertEqual(result.status_code, 400)
        self.assertIn('CPF', result.json()['error'])
        post.assert_not_called()
        self.assert_no_payment()

    @patch('cards.views.http_requests.post')
    def test_customer_rejection_does_not_expose_provider_description(self, post):
        post.return_value = self.provider_response(400, {
            'errors': [{'code': 'invalid_object', 'description': 'sensitive provider detail'}]})
        result = self.create_payment()
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.json()['code'], 'asaas_customer_rejected')
        self.assertNotIn('sensitive', result.content.decode())
        self.user.refresh_from_db()
        self.assertEqual(self.user.asaas_customer_id, '')
        self.assert_no_payment()

    @patch('cards.views.http_requests.post')
    def test_connection_and_timeout_errors_do_not_blame_profile(self, post):
        for failure, status, code in (
            (requests.Timeout('secret detail'), 504, 'asaas_timeout'),
            (requests.ConnectionError('secret detail'), 502, 'asaas_connection'),
        ):
            with self.subTest(code=code):
                post.side_effect = failure
                result = self.create_payment()
                self.assertEqual(result.status_code, status)
                self.assertEqual(result.json()['code'], code)
                self.assertNotIn('CPF', result.json()['error'])
                self.assertNotIn('secret', result.content.decode())
        self.assert_no_payment()

    @patch('cards.views.http_requests.post')
    def test_provider_unavailability_is_not_a_customer_rejection(self, post):
        for status in (429, 500, 503):
            with self.subTest(status=status):
                post.return_value = self.provider_response(status, None)
                result = self.create_payment()
                self.assertEqual(result.status_code, 503)
                self.assertEqual(result.json()['code'], 'asaas_unavailable')
        self.assert_no_payment()

    @patch('cards.views.http_requests.post')
    def test_malformed_customer_response_is_not_saved(self, post):
        responses = [self.provider_response(200, value) for value in ([], {}, {'id': None}, {'id': 123})]
        invalid_json = self.provider_response(200, None)
        invalid_json.json.side_effect = ValueError('sensitive provider detail')
        for response in responses + [invalid_json]:
            with self.subTest(response=response.json.return_value):
                post.return_value = response
                result = self.create_payment()
                self.assertEqual(result.status_code, 502)
                self.assertEqual(result.json()['code'], 'asaas_invalid_response')
                self.user.refresh_from_db()
                self.assertEqual(self.user.asaas_customer_id, '')
        self.assert_no_payment()

    @patch('cards.views.http_requests.post')
    def test_new_customer_then_credit_payment_succeeds_without_crediting_balance(self, post):
        post.side_effect = [self.provider_response(200, {'id': 'cus_new'}),
            self.provider_response(200, {'id': 'pay_new', 'invoiceUrl': 'https://sandbox.asaas.com/i/test'})]
        result = self.create_payment()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[0].args[0], 'https://api-sandbox.asaas.com/v3/customers')
        self.assertEqual(post.call_args_list[0].kwargs['json']['cpfCnpj'], '00000000191')
        self.assertEqual(post.call_args_list[1].kwargs['json']['customer'], 'cus_new')
        self.user.refresh_from_db()
        self.assertEqual(self.user.asaas_customer_id, 'cus_new')
        self.assertEqual(Recarga.objects.get().status, 'pendente')
        self.assertEqual(self.user.card.saldo, 0)
        self.assertFalse(Transaction.objects.exists())

    @patch('cards.views.http_requests.post')
    def test_customer_recreation_preserves_authentication_error(self, post):
        self.user.asaas_customer_id = 'cus_old_environment'
        self.user.save(update_fields=['asaas_customer_id'])
        post.side_effect = [self.provider_response(400, {'errors': [{'code': 'invalid_customer'}]}),
                            self.provider_response(401, {})]
        with self.assertLogs('cards.views', level='WARNING'):
            result = self.create_payment()
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json()['code'], 'asaas_authentication')
        self.assertEqual(post.call_count, 2)
        self.assert_no_payment()
