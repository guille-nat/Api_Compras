# Generated by Django 5.1.5 on 2025-02-04 23:08

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_code', models.CharField(help_text='Código del producto.', max_length=40, unique=True)),
                ('name', models.CharField(help_text='Nombre del producto.', max_length=100)),
                ('brand', models.CharField(help_text='Marca asociada al producto.', max_length=45)),
                ('model', models.CharField(help_text='Modelo asociado al producto.', max_length=100)),
                ('unit_price', models.DecimalField(decimal_places=2, help_text='Precio del producto por unidad.', max_digits=10)),
                ('stock', models.PositiveIntegerField(help_text='Cantidad del producto en stock')),
            ],
            options={
                'verbose_name': 'Producto',
                'verbose_name_plural': 'Productos',
            },
        ),
    ]
