"""Configuração Asaas compartilhada pelo servidor, sem expor credenciais à UI."""
from django.conf import settings


ASAAS_API_URLS = frozenset({
    'https://api.asaas.com/v3',
    'https://api-sandbox.asaas.com/v3',
})


def asaas_base_url():
    base = settings.ASAAS_BASE_URL.strip().rstrip('/')
    return base if base in ASAAS_API_URLS else ''


def online_payments_enabled():
    api_key = settings.ASAAS_API_KEY.strip()
    webhook_token = settings.ASAAS_WEBHOOK_TOKEN.strip()
    return bool(settings.ASAAS_PAYMENTS_ENABLED and api_key and webhook_token
                and api_key != webhook_token and asaas_base_url())
