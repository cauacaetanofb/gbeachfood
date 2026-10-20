"""Valida a configuração de deploy em processos isolados, sem banco ou .env."""
import json
import os
from pathlib import Path
import subprocess
import sys

from django.test import SimpleTestCase


class ProductionSettingsTests(SimpleTestCase):
    def run_config(self, changes=None, code=None):
        env = {key: value for key, value in os.environ.items()
               if key.upper() in {'SYSTEMROOT', 'WINDIR', 'PATH', 'TEMP', 'TMP'}}
        env.update({
            'PYTHONDONTWRITEBYTECODE': '1',
            'DJANGO_SETTINGS_MODULE': 'gfood.production',
            'SECRET_KEY': 'test-only-0123456789-abcdefghijklmnopqrstuvwxyz-ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            'ALLOWED_HOSTS': 'gbeachfood.example.com',
            'DATABASE_URL': 'postgresql://test:test@localhost/gbeachfood_test',
        })
        for key, value in (changes or {}).items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        return subprocess.run(
            [sys.executable, '-B', '-c', code or 'import gfood.production'],
            cwd=Path(__file__).resolve().parent.parent, env=env,
            capture_output=True, text=True, timeout=30,
        )

    def test_missing_required_configuration_is_rejected(self):
        for name in ('SECRET_KEY', 'ALLOWED_HOSTS', 'DATABASE_URL'):
            with self.subTest(name=name):
                result = self.run_config({name: None})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(name, result.stderr)

    def test_unsafe_configuration_is_rejected(self):
        for change in (
            {'DATABASE_URL': 'sqlite:///:memory:'},
            {'ALLOWED_HOSTS': '*'},
            {'ALLOWED_HOSTS': 'https://example.com'},
            {'SECRET_KEY': 'short-key'},
            {'EMAIL_BACKEND': 'django.core.mail.backends.console.EmailBackend'},
        ):
            with self.subTest(change=change):
                result = self.run_config(change)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('ImproperlyConfigured', result.stderr)

    def test_cloud_sql_socket_and_credentials_are_required(self):
        cloud_sql = {
            'DATABASE_URL': None,
            'INSTANCE_CONNECTION_NAME': 'gbeachfood:southamerica-east1:gbeachfood-db',
            'DB_NAME': 'gbeachfood', 'DB_USER': 'gbeachfood_app', 'DB_PASSWORD': 'test-only',
        }
        result = self.run_config(cloud_sql, code=(
            'import gfood.production as s; '
            'assert s.DATABASES["default"]["HOST"] == '
            '"/cloudsql/gbeachfood:southamerica-east1:gbeachfood-db"; '
            'assert s.DATABASES["default"]["CONN_HEALTH_CHECKS"] is True'
        ))
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ('DB_NAME', 'DB_USER', 'DB_PASSWORD'):
            with self.subTest(name=name):
                result = self.run_config({**cloud_sql, name: None})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(name, result.stderr)

    def test_debug_is_disabled_and_legacy_key_does_not_override_secret(self):
        result = self.run_config({'DEBUG': 'True', 'TOKEN_CSRF': 'legacy-key'}, code=(
            'import os; import gfood.production as s; '
            'assert s.DEBUG is False; '
            'assert s.SECRET_KEY == os.environ["SECRET_KEY"]; '
            'assert s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE; '
            'assert s.SESSION_COOKIE_NAME == "__session" and s.CSRF_USE_SESSIONS; '
            'assert os.environ["PYTHON_DOTENV_DISABLED"] == "1"'
        ))
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_https_behind_cloud_run_proxy_does_not_redirect_forever(self):
        result = self.run_config(code=(
            'import json; import django; django.setup(); '
            'from django.conf import settings; '
            'settings.SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"; '
            'from django.test import Client; '
            'c = Client(SERVER_NAME="gbeachfood.example.com"); '
            'plain = c.get("/login/"); '
            'secure = c.get("/login/", HTTP_X_FORWARDED_PROTO="https"); '
            'print(json.dumps([plain.status_code, secure.status_code, '
            'bool(secure.cookies["__session"]["secure"])]))'
        ))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), [301, 200, True])
