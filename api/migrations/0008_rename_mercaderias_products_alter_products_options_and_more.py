# Generated by Django 5.1.5 on 2025-01-21 21:07

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_alter_detallescompras_options'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Mercaderias',
            new_name='Products',
        ),
        migrations.AlterModelOptions(
            name='products',
            options={'verbose_name': 'Product', 'verbose_name_plural': 'Products'},
        ),
        migrations.RenameField(
            model_name='products',
            old_name='cod_mercaderia',
            new_name='cod_products',
        ),
        migrations.RemoveField(
            model_name='detallescompras',
            name='mercaderias',
        ),
        migrations.AddField(
            model_name='detallescompras',
            name='products',
            field=models.ForeignKey(default=1, help_text='Productos asociado a la compra.', on_delete=django.db.models.deletion.CASCADE, to='api.products'),
        ),
        migrations.AlterField(
            model_name='detallescompras',
            name='compras',
            field=models.ForeignKey(help_text='Compra asociada al producto.', on_delete=django.db.models.deletion.CASCADE, to='api.compras'),
        ),
    ]
