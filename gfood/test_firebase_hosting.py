"""Integração de sessão e CSRF com os cookies filtrados pelo Firebase Hosting."""
import re
from django.test import Client, TestCase, override_settings
from accounts.models import User


@override_settings(
    SESSION_COOKIE_NAME='__session', CSRF_USE_SESSIONS=True,
    SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'),
    ALLOWED_HOSTS=['gbeachfood.web.app'],
    CSRF_TRUSTED_ORIGINS=['https://gbeachfood.web.app'],
)
class FirebaseHostingSessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='hosting-test', password='Test-only-password-123', user_type='cliente')
        self.client = Client(enforce_csrf_checks=True,
            SERVER_NAME='gbeachfood.web.app', HTTP_X_FORWARDED_PROTO='https')

    def filter_hosting_cookies(self):
        for name in list(self.client.cookies):
            if name != "__session":
                del self.client.cookies[name]

    def token(self, response):
        self.assertEqual(response.status_code, 200)
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.content.decode())
        self.assertIsNotNone(match)
        return match.group(1)

    def login_over_https(self):
        response = self.client.get('/login/')
        token = self.token(response)
        self.assertIn('__session', response.cookies)
        self.assertNotIn('csrftoken', response.cookies)
        self.assertTrue(response.cookies['__session']['httponly'])
        self.assertTrue(response.cookies['__session']['secure'])
        self.client.cookies['discarded_by_firebase'] = 'test-only'
        self.filter_hosting_cookies()
        self.assertEqual(set(self.client.cookies), {'__session'})
        response = self.client.post('/login/', {
            'username': self.user.username, 'password': 'Test-only-password-123',
            'csrfmiddlewaretoken': token,
        }, HTTP_ORIGIN='https://gbeachfood.web.app')
        self.assertRedirects(response, '/dashboard/', fetch_redirect_response=False)
        self.filter_hosting_cookies()
        return token

    def test_login_authenticated_write_and_logout_with_one_cookie(self):
        old_token = self.login_over_https()
        token = self.token(self.client.get('/dashboard/'))
        response = self.client.get('/api/profile/')
        self.assertEqual(response.json()['profile']['id'], self.user.pk)
        kwargs = dict(content_type='application/json', HTTP_ORIGIN='https://gbeachfood.web.app')
        self.assertEqual(self.client.post('/api/profile/update/',
            '{"first_name":"Changed"}', HTTP_X_CSRFTOKEN=old_token, **kwargs).status_code, 403)
        self.assertEqual(self.client.post('/api/profile/update/',
            '{"first_name":"Changed"}', HTTP_X_CSRFTOKEN=token, **kwargs).status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Changed')
        self.client.get('/logout/')
        self.assertEqual(self.client.get('/api/profile/').status_code, 302)

    def test_missing_token_and_untrusted_origin_remain_forbidden(self):
        self.login_over_https()
        token = self.token(self.client.get('/dashboard/'))
        self.assertEqual(self.client.post('/api/profile/update/', '{}',
            content_type='application/json', HTTP_ORIGIN='https://gbeachfood.web.app').status_code, 403)
        self.assertEqual(self.client.post('/api/profile/update/', '{}',
            content_type='application/json', HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN='https://untrusted.example').status_code, 403)

    def test_all_dashboards_expose_token_without_csrf_cookie(self):
        self.login_over_https()
        for role in ('admin', 'caixa', 'balcao', 'cliente'):
            with self.subTest(role=role):
                self.user.user_type = role
                self.user.save(update_fields=['user_type'])
                response = self.client.get('/dashboard/')
                self.assertTrue(self.token(response))
                self.assertNotIn('csrftoken', response.cookies)
