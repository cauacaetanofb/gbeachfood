import os
import runpy
from datetime import timedelta
from pathlib import Path
from smtplib import SMTPAuthenticationError
from unittest.mock import patch
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from .models import User, PasswordResetCode


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   DEFAULT_FROM_EMAIL='GFood <sender@example.com>')
class PasswordRecoveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='customer', email='cliente@example.com',
                                             password='OldPassword123!')

    def request_code(self, email='cliente@example.com'):
        return self.client.post('/api/forgot-password/', {'email': email}, content_type='application/json')

    def reset(self, code):
        return self.client.post('/api/reset-password/', {
            'email': self.user.email, 'code': code, 'new_password': 'NewPassword456!',
        }, content_type='application/json')

    def test_email_and_complete_password_reset(self):
        self.assertEqual(self.request_code().status_code, 200)
        code = PasswordResetCode.objects.get()
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertEqual(mail.outbox[0].from_email, 'GFood <sender@example.com>')
        self.assertIn(code.code, mail.outbox[0].body)
        self.assertEqual(self.reset(code.code).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPassword456!'))
        self.assertEqual(self.reset(code.code).status_code, 400)

    def test_unknown_email_returns_generic_success_without_sending(self):
        self.assertEqual(self.request_code('unknown@example.com').status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(PasswordResetCode.objects.exists())

    def test_expired_code_cannot_change_password(self):
        self.request_code()
        code = PasswordResetCode.objects.get()
        PasswordResetCode.objects.filter(pk=code.pk).update(criado_em=timezone.now() - timedelta(minutes=16))
        self.assertEqual(self.reset(code.code).status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPassword123!'))

    def test_failed_send_removes_unsent_code_and_returns_json(self):
        for failure in (SMTPAuthenticationError(535, b'invalid credentials'), OSError('timeout')):
            with patch('accounts.views.send_mail', side_effect=failure):
                with self.assertLogs('accounts.views', level='WARNING'):
                    response = self.request_code()
            self.assertEqual(response.status_code, 503)
            self.assertIn('error', response.json())
            self.assertFalse(PasswordResetCode.objects.exists())
            self.assertNotIn('credentials', response.content.decode())

    def test_zero_messages_is_an_error(self):
        with patch('accounts.views.send_mail', return_value=0):
            with self.assertLogs('accounts.views', level='WARNING'):
                self.assertEqual(self.request_code().status_code, 503)
        self.assertFalse(PasswordResetCode.objects.exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.gmail.com', EMAIL_HOST_USER='', EMAIL_HOST_PASSWORD='')
    def test_missing_gmail_credentials_does_not_attempt_delivery(self):
        with patch('accounts.views.send_mail') as send:
            self.assertEqual(self.request_code().status_code, 503)
            send.assert_not_called()
        self.assertFalse(PasswordResetCode.objects.exists())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
        EMAIL_HOST='smtp.gmail.com', EMAIL_PORT=587, EMAIL_HOST_USER='sender@gmail.com',
        EMAIL_HOST_PASSWORD='test-app-password', EMAIL_USE_TLS=True, EMAIL_USE_SSL=False,
        EMAIL_TIMEOUT=15, DEFAULT_FROM_EMAIL='sender@gmail.com')
    def test_gmail_smtp_backend_uses_starttls_and_credentials(self):
        with patch('smtplib.SMTP') as smtp:
            smtp.return_value.sendmail.return_value = {}
            self.assertEqual(self.request_code().status_code, 200)
            smtp.assert_called_once()
            self.assertEqual(smtp.call_args.args[:2], ('smtp.gmail.com', 587))
            self.assertEqual(smtp.call_args.kwargs['timeout'], 15)
            smtp.return_value.starttls.assert_called_once()
            smtp.return_value.login.assert_called_once_with('sender@gmail.com', 'test-app-password')
            smtp.return_value.sendmail.assert_called_once()

    def test_invalid_request_returns_json(self):
        for data in ([], {'email': None}, {'email': ''}):
            self.assertEqual(self.client.post('/api/forgot-password/', data,
                content_type='application/json').status_code, 400)


class EmailSettingsTests(SimpleTestCase):
    def load(self, **env):
        with patch.dict(os.environ, {'PYTHON_DOTENV_DISABLED': '1', **env}, clear=True):
            return runpy.run_path(str(Path(__file__).resolve().parents[1] / 'gfood/settings.py'))

    def test_gmail_defaults_and_environment_overrides(self):
        settings = self.load(EMAIL_HOST_USER='sender@gmail.com', EMAIL_HOST_PASSWORD='test-password')
        self.assertEqual(settings['EMAIL_BACKEND'], 'django.core.mail.backends.smtp.EmailBackend')
        self.assertEqual(settings['EMAIL_HOST'], 'smtp.gmail.com')
        self.assertEqual(settings['EMAIL_PORT'], 587)
        self.assertTrue(settings['EMAIL_USE_TLS'])
        self.assertFalse(settings['EMAIL_USE_SSL'])
        self.assertEqual(settings['DEFAULT_FROM_EMAIL'], 'sender@gmail.com')
        settings = self.load(EMAIL_PORT='465', EMAIL_USE_TLS='False', EMAIL_USE_SSL='True')
        self.assertEqual(settings['EMAIL_PORT'], 465)
        self.assertTrue(settings['EMAIL_USE_SSL'])

    def test_tls_and_ssl_cannot_be_enabled_together(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(EMAIL_USE_TLS='True', EMAIL_USE_SSL='True')

    def test_console_allowed_only_in_development(self):
        backend = 'django.core.mail.backends.console.EmailBackend'
        self.assertEqual(self.load(DEBUG='True', EMAIL_BACKEND=backend)['EMAIL_BACKEND'], backend)
        with self.assertRaises(ImproperlyConfigured):
            self.load(DEBUG='False', EMAIL_BACKEND=backend)
