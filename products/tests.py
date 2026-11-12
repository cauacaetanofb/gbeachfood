
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from accounts.models import User
from .models import Category, Product


class ProductCodeTests(TestCase):
    create_url = '/api/products/create/'

    def setUp(self):
        self.admin = User.objects.create_user(username='product-admin', user_type='admin')
        self.client.force_login(self.admin)

    def create_product(self, **fields):
        return self.client.post(self.create_url, {'nome': 'Suco', 'preco': '7.50', **fields})

    def update_product(self, product, **fields):
        return self.client.post(f'/api/products/{product.pk}/update/', fields)

    def test_creation_generates_unique_skus_and_accepts_optional_ncm(self):
        for fields, expected_ncm in (({}, ''), ({'ncm': ' 01012100 '}, '01012100')):
            response = self.create_product(**fields)
            self.assertEqual(response.status_code, 200)
            data = response.json()['product']
            product = Product.objects.get(pk=data['id'])
            self.assertRegex(product.sku, r'^GBF-[0-9A-F]{32}$')
            self.assertEqual(data['sku'], product.sku)
            self.assertEqual(data['ncm'], expected_ncm)
            self.assertEqual(product.ncm, expected_ncm)
        self.assertEqual(len(set(Product.objects.values_list('sku', flat=True))), 2)

    def test_sku_is_generated_for_orm_and_bulk_creation_and_unique_in_database(self):
        first = Product.objects.create(nome='Suco', preco='7.50')
        products = Product.objects.bulk_create([
            Product(nome='Água', preco='4.00'), Product(nome='Café', preco='3.00'),
        ])
        self.assertEqual(len({first.sku, *(p.sku for p in products)}), 3)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.create(nome='Duplicado', preco='1.00', sku=first.sku)

    def test_update_preserves_sku_and_omitted_ncm_and_allows_clearing_ncm(self):
        product = Product.objects.create(nome='Suco', preco='7.50', ncm='01012100')
        original_sku = product.sku
        for fields, expected in (
            ({'nome': 'Suco novo'}, '01012100'),
            ({'ncm': ' 22021000 '}, '22021000'),
            ({'ncm': ''}, ''),
        ):
            response = self.update_product(product, **fields)
            self.assertEqual(response.status_code, 200)
            product.refresh_from_db()
            self.assertEqual(product.sku, original_sku)
            self.assertEqual(product.ncm, expected)
            self.assertEqual(product.nome, 'Suco novo')

    def test_invalid_ncm_does_not_create_or_partially_update_products_or_categories(self):
        product = Product.objects.create(nome='Original', preco='7.50', ncm='01012100')
        for ncm in ('123', '123456789', '0101.21.00', 'abcdefgh', '１２３４５６７８', '1234\n5678'):
            with self.subTest(ncm=ncm):
                fields = {'ncm': ncm, 'nome': 'Alterado', 'preco': '9.00', 'categoria': 'Nova'}
                for response in (self.create_product(**fields), self.update_product(product, **fields)):
                    self.assertEqual(response.status_code, 400)
                    self.assertIn('error', response.json())
                product.refresh_from_db()
                self.assertEqual(product.nome, 'Original')
                self.assertEqual(product.preco, Decimal('7.50'))
                self.assertEqual(product.ncm, '01012100')
                self.assertEqual(Product.objects.count(), 1)
                self.assertFalse(Category.objects.exists())

    def test_ncm_model_validation_preserves_leading_zero_and_allows_blank(self):
        product = Product(nome='Teste', preco='1.00', ncm='01012100')
        product.full_clean()
        self.assertEqual(product.ncm, '01012100')
        product.ncm = ''
        product.full_clean()
        product.ncm = '1234567'
        with self.assertRaises(ValidationError):
            product.full_clean()

    def test_api_rejects_manual_sku_without_changing_other_data(self):
        product = Product.objects.create(nome='Original', preco='7.50', ncm='01012100')
        original_sku = product.sku
        for response in (
            self.create_product(sku='MANUAL', categoria='Nova'),
            self.update_product(product, sku='MANUAL', ncm='22021000', nome='Alterado'),
        ):
            self.assertEqual(response.status_code, 400)
            self.assertIn('automaticamente', response.json()['error'])
        product.refresh_from_db()
        self.assertEqual((product.sku, product.ncm, product.nome), (original_sku, '01012100', 'Original'))
        self.assertEqual(Product.objects.count(), 1)
        self.assertFalse(Category.objects.exists())

    def test_lists_return_codes_and_keep_availability_filter(self):
        product = Product.objects.create(nome='Ativo', preco='7.50', ncm='01012100')
        inactive = Product.objects.create(nome='Inativo', preco='3.00', disponivel=False)
        for url, expected_ids in (
            ('/api/products/', {product.pk}),
            ('/api/products/all/', {product.pk, inactive.pk}),
        ):
            data = self.client.get(url).json()['products']
            self.assertEqual({p['id'] for p in data}, expected_ids)
            item = next(p for p in data if p['id'] == product.pk)
            self.assertEqual((item['sku'], item['ncm']), (product.sku, '01012100'))

    def test_only_admin_profile_can_create_and_update_codes(self):
        product = Product.objects.create(nome='Original', preco='7.50')
        for role in ('caixa', 'balcao', 'cliente'):
            # Ser superusuário não substitui o perfil admin da aplicação.
            user = User.objects.create_user(username=f'product-{role}', user_type=role, is_superuser=True)
            self.client.force_login(user)
            self.assertEqual(self.create_product(ncm='01012100').status_code, 403)
            self.assertEqual(self.update_product(product, ncm='01012100').status_code, 403)
            self.assertEqual(self.client.get('/api/products/all/').status_code, 403)
        self.client.logout()
        self.assertEqual(self.create_product(ncm='01012100').status_code, 302)
        self.assertEqual(self.update_product(product, ncm='01012100').status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.ncm, '')
        self.assertEqual(Product.objects.count(), 1)

    def test_admin_form_renders_readonly_sku_and_optional_text_ncm(self):
        response = self.client.get('/dashboard/')
        self.assertContains(response, 'id="p-sku" type="text" placeholder="Gerado ao salvar o produto" readonly')
        self.assertContains(response, 'id="p-ncm" type="text" inputmode="numeric" maxlength="8" pattern="[0-9]{8}"')
        self.assertContains(response, 'Buscar por nome, SKU ou NCM...')


class ProductCodeMigrationTests(TransactionTestCase):
    def test_existing_products_receive_distinct_skus_without_losing_data(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        try:
            before = [('products', '0004_physical_card_price')]
            executor.migrate(before)
            apps = executor.loader.project_state(before).apps
            OldProduct = apps.get_model('products', 'Product')
            category = apps.get_model('products', 'Category').objects.create(nome='Bebidas')
            originals = [OldProduct.objects.create(
                nome=f'Produto {i}', descricao='Preservar', preco='7.50', categoria_id=category.pk,
                disponivel=False, imagem_base64='data:image/png;base64,teste',
            ) for i in range(2)]
            for original in originals:
                original.refresh_from_db()
            after = [('products', '0007_product_sku_default')]
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            NewProduct = executor.loader.project_state(after).apps.get_model('products', 'Product')
            skus = set()
            for original in originals:
                product = NewProduct.objects.get(pk=original.pk)
                for field in ('nome', 'descricao', 'preco', 'categoria_id', 'disponivel', 'imagem_base64', 'criado_em'):
                    self.assertEqual(getattr(product, field), getattr(original, field))
                self.assertEqual(product.ncm, '')
                self.assertRegex(product.sku, r'^GBF-[0-9A-F]{32}$')
                skus.add(product.sku)
            self.assertEqual(len(skus), len(originals))
        finally:
            MigrationExecutor(connection).migrate(latest)
