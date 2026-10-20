"""Configuração de produção para Cloud Run (sem carregar o .env local)."""
import os

from django.core.exceptions import ImproperlyConfigured

os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ['DEBUG'] = 'False'

from .settings import *  # noqa: F403


def required_env(name):
    value = os.getenv(name, '')
    if not value.strip():
        raise ImproperlyConfigured(f'A variável {name} é obrigatória em produção.')
    return value


DEBUG = False
SECRET_KEY = required_env('SECRET_KEY')
if len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith('django-insecure-'):
    raise ImproperlyConfigured('SECRET_KEY deve ser uma chave aleatória de produção com ao menos 50 caracteres.')

ALLOWED_HOSTS = [host.strip() for host in required_env('ALLOWED_HOSTS').split(',') if host.strip()]
if not ALLOWED_HOSTS or any(host == '*' or '://' in host for host in ALLOWED_HOSTS):
    raise ImproperlyConfigured('ALLOWED_HOSTS deve conter domínios, sem protocolo ou curinga global.')

# O vínculo Cloud SQL do serviço fornece este socket; não é necessário SDK Firebase.
if os.getenv('INSTANCE_CONNECTION_NAME'):
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': '/cloudsql/' + required_env('INSTANCE_CONNECTION_NAME').strip(),
        'NAME': required_env('DB_NAME'),
        'USER': required_env('DB_USER'),
        'PASSWORD': required_env('DB_PASSWORD'),
    }}
else:
    import dj_database_url
    DATABASES = {'default': dj_database_url.parse(required_env('DATABASE_URL'))}

if DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('Produção exige PostgreSQL; SQLite não é persistente no Cloud Run.')
DATABASES['default'].update(CONN_MAX_AGE=60, CONN_HEALTH_CHECKS=True)

# O proxy do Cloud Run termina TLS e informa o protocolo original.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
# Firebase Hosting encaminha somente o cookie __session ao Cloud Run.
SESSION_COOKIE_NAME = "__session"
CSRF_USE_SESSIONS = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
# Habilitar subdomínios/preload somente após configurar um domínio próprio.
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
