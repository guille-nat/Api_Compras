# Generated by Django 5.1.5 on 2025-01-24 19:25

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0011_alter_compras_cuotas_totales_alter_cuotas_nro_cuota_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='cuotas',
            name='compra',
            field=models.ForeignKey(help_text='Compra asociada a la cuota.', on_delete=django.db.models.deletion.CASCADE, related_name='cuotas', to='api.compras'),
        ),
        migrations.CreateModel(
            name='Notificacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mensaje', models.TextField()),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('enviada', models.BooleanField(default=False)),
                ('compra', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.compras')),
                ('cuota', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='api.cuotas')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Notificación',
                'verbose_name_plural': 'Notificaciones',
            },
        ),
    ]
