from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


def create_price(apps, schema_editor):
    apps.get_model('products', 'PhysicalCardPrice').objects.using(
        schema_editor.connection.alias
    ).get_or_create(pk=1, defaults={'preco': Decimal('2.00')})


class Migration(migrations.Migration):
    dependencies = [('products', '0003_product_imagem_base64')]

    operations = [
        migrations.CreateModel(
            name='PhysicalCardPrice',
            fields=[
                ('id', models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ('preco', models.DecimalField(decimal_places=2, default=Decimal('2.00'), max_digits=10,
                    validators=[MinValueValidator(Decimal('0.01'))], verbose_name='Preço')),
            ],
            options={'constraints': [
                models.CheckConstraint(condition=models.Q(id=1), name='physical_card_price_singleton'),
                models.CheckConstraint(condition=models.Q(preco__gte=Decimal('0.01')), name='physical_card_price_positive'),
            ]},
        ),
        migrations.RunPython(create_price, migrations.RunPython.noop),
    ]
