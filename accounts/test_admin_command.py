import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class CreateAdminCommandTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.env = {
            'DJANGO_SUPERUSER_USERNAME': 'siteadmin',
            'DJANGO_SUPERUSER_EMAIL': 'owner@example.com',
            'DJANGO_SUPERUSER_PASSWORD': 'Testing-Only!LongPass-4937',
        }

    def run_command(self, **overrides):
        output = StringIO()
        with patch.dict(os.environ, {**self.env, **overrides}):
            call_command('create_superuser_auto', stdout=output)
        self.assertNotIn(self.env['DJANGO_SUPERUSER_PASSWORD'], output.getvalue())
        return output.getvalue()

    def test_creates_admin_with_hashed_password_and_user_management_access(self):
        self.run_command()
        user = self.User.objects.get(username='siteadmin')
        self.assertTrue(user.is_active and user.is_staff and user.is_superuser)
        self.assertEqual(user.user_type, 'admin')
        self.assertTrue(user.check_password(self.env['DJANGO_SUPERUSER_PASSWORD']))
        self.assertNotEqual(user.password, self.env['DJANGO_SUPERUSER_PASSWORD'])
        self.assertTrue(self.client.login(username=user.username,
                                         password=self.env['DJANGO_SUPERUSER_PASSWORD']))
        from django.urls import reverse
        self.assertEqual(self.client.get(reverse('api_list_staff')).status_code, 200)

    def test_repeat_preserves_existing_password_and_email(self):
        self.run_command()
        original = self.User.objects.get().password
        self.run_command(DJANGO_SUPERUSER_PASSWORD='Another-Valid-Pass!7319',
                         DJANGO_SUPERUSER_EMAIL='different@example.com')
        self.assertEqual(self.User.objects.count(), 1)
        user = self.User.objects.get()
        self.assertEqual(user.password, original)
        self.assertEqual(user.email, 'owner@example.com')

    def test_missing_configuration_fails_without_creating_user(self):
        for key in self.env:
            with self.subTest(key=key), self.assertRaises(CommandError):
                self.run_command(**{key: ' '})
        self.assertFalse(self.User.objects.exists())

    def test_customer_collision_does_not_promote_or_change_password(self):
        user = self.User.objects.create_user(username='siteadmin', password='Original!9238')
        original = user.password
        with self.assertRaises(CommandError):
            self.run_command()
        user.refresh_from_db()
        self.assertEqual(user.user_type, 'cliente')
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(user.password, original)

    def test_legacy_superuser_customer_profile_fails_explicitly(self):
        user = self.User.objects.create_superuser(username='siteadmin', password='Original!9238')
        with self.assertRaises(CommandError):
            self.run_command()
        user.refresh_from_db()
        self.assertEqual(user.user_type, 'cliente')

    def test_inactive_or_unusable_admin_is_not_reported_as_ready(self):
        user = self.User.objects.create_superuser(username='siteadmin', user_type='admin',
                                                password='Original!9238', is_active=False)
        with self.assertRaises(CommandError):
            self.run_command()
        user.is_active = True
        user.set_unusable_password()
        user.save()
        with self.assertRaises(CommandError):
            self.run_command()

    def test_invalid_credentials_fail_without_creating_user(self):
        for overrides in ({'DJANGO_SUPERUSER_PASSWORD': '12345678'},
                          {'DJANGO_SUPERUSER_EMAIL': 'invalid'},
                          {'DJANGO_SUPERUSER_USERNAME': 'invalid name'}):
            with self.subTest(overrides=overrides), self.assertRaises(CommandError):
                self.run_command(**overrides)
        self.assertFalse(self.User.objects.exists())
