from django.core.validators import RegexValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('products', '0004_physical_card_price')]

    operations = [
        migrations.AddField(
            model_name='product', name='sku',
            field=models.CharField(max_length=36, null=True, unique=True, editable=False, verbose_name='SKU'),
        ),
        migrations.AddField(
            model_name='product', name='ncm',
            field=models.CharField(
                max_length=8, blank=True, default='', verbose_name='NCM',
                validators=[RegexValidator(r'\A[0-9]{8}\Z', 'Informe um NCM com exatamente 8 dígitos.')],
            ),
        ),
    ]
