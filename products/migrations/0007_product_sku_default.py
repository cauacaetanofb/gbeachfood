from django.db import migrations, models

import products.models


class Migration(migrations.Migration):
    dependencies = [('products', '0006_populate_product_skus')]

    operations = [
        migrations.AlterField(
            model_name='product', name='sku',
            field=models.CharField(
                max_length=36, unique=True, default=products.models.generate_product_sku,
                editable=False, verbose_name='SKU',
            ),
        ),
    ]
