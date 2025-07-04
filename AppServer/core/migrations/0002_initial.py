# Generated by Django 5.2.3 on 2025-06-18 16:52

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Circuit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('circuitRef', models.CharField(help_text='Unique circuit identifier from Ergast API (circuitId).', max_length=50, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('location', models.CharField(blank=True, max_length=100, null=True)),
                ('country', models.CharField(blank=True, max_length=100, null=True)),
                ('lat', models.FloatField(blank=True, null=True)),
                ('lng', models.FloatField(blank=True, null=True)),
                ('alt', models.IntegerField(blank=True, help_text='Altitude in meters', null=True)),
                ('url', models.URLField(blank=True, max_length=255, null=True)),
            ],
            options={
                'verbose_name': 'Circuito',
                'verbose_name_plural': 'Circuitos',
                'db_table': 'f1app_usr.circuits',
                'ordering': ['name'],
            },
        ),
    ]
