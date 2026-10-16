"""Configuração isolada: python -B manage.py test --settings=gfood.test_settings."""
import os

os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['DATABASE_URL'] = ''

from .settings import *  # noqa: F403

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:',
    'OPTIONS': {'transaction_mode': 'IMMEDIATE', 'timeout': 20}}}
if os.getenv('TEST_DATABASE_URL'):
    import dj_database_url
    DATABASES = {'default': dj_database_url.parse(os.environ['TEST_DATABASE_URL'])}
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
ASAAS_API_KEY = 'test-api-key'
ASAAS_WEBHOOK_TOKEN = 'test-webhook-token'
ALLOWED_HOSTS = ['testserver', 'localhost']
