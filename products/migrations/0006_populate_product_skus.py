from uuid import uuid4

from django.db import migrations


def populate_product_skus(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    products = Product.objects.using(schema_editor.connection.alias)
    # Separar dados e schema mantém esta etapa compatível com PostgreSQL.
    for product in products.filter(sku__isnull=True).iterator():
        products.filter(pk=product.pk).update(sku=f'GBF-{uuid4().hex.upper()}')


class Migration(migrations.Migration):
    dependencies = [('products', '0005_product_sku_ncm')]

    operations = [migrations.RunPython(populate_product_skus, migrations.RunPython.noop)]
