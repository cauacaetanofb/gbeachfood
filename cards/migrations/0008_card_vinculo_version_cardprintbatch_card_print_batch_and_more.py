"""Mantém o histórico da migração já aplicada antes da reversão do código."""
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('cards', '0007_recarga_credito'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(model_name='card', name='vinculo_version',
                            field=models.PositiveIntegerField(default=0, editable=False)),
        migrations.CreateModel(name='CardPrintBatch', fields=[
            ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ('quantidade', models.PositiveSmallIntegerField()),
            ('criado_em', models.DateTimeField(auto_now_add=True)),
            ('criado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='card_print_batches', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering': ['-criado_em']}),
        migrations.AddField(model_name='card', name='print_batch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                                    related_name='cards', to='cards.cardprintbatch')),
        migrations.AddConstraint(model_name='card', constraint=models.CheckConstraint(
            condition=models.Q(print_batch__isnull=True) | models.Q(user__isnull=True),
            name='physical_card_without_user')),
    ]
