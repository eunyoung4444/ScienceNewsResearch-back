# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-07-29 02:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cq', '0002_auto_20180728_0144'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='created_phase',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]
