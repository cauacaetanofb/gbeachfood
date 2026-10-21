import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Cria um administrador a partir de variáveis de ambiente'

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = os.getenv('DJANGO_SUPERUSER_USERNAME', '').strip()
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', '').strip()
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD', '')

        if not username or not email or not password.strip():
            raise CommandError(
                'Defina DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL e '
                'DJANGO_SUPERUSER_PASSWORD para criar o administrador.'
            )

        existing = User.objects.filter(username=username).first()
        if existing:
            if not (existing.is_active and existing.is_staff and
                    existing.is_superuser and existing.user_type == 'admin' and
                    existing.has_usable_password()):
                raise CommandError(
                    'O nome escolhido já pertence a uma conta sem todas as '
                    'permissões de administrador ou sem acesso ativo. '
                    'Nenhuma alteração foi feita. Escolha outro nome ou revise a conta.'
                )
            self.stdout.write(self.style.SUCCESS(
                'Administrador já existe. A senha e os dados existentes foram preservados.'
            ))
            return

        candidate = User(username=username, email=email, user_type='admin')
        try:
            candidate.full_clean(exclude=['password'])
            validate_password(password, candidate)
        except ValidationError:
            # Não imprimir valores fornecidos em mensagens de validadores.
            raise CommandError(
                'Dados inválidos. Use um nome de usuário e e-mail válidos e uma '
                'senha forte, não comum, com pelo menos 8 caracteres, '
                'que não seja apenas numérica nem parecida com seus dados.'
            ) from None

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            user_type='admin',
        )
        self.stdout.write(self.style.SUCCESS('Administrador criado com sucesso!'))
