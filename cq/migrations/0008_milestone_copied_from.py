# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2018-07-31 07:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cq', '0007_auto_20180730_0357'),
    ]

    operations = [
        migrations.AddField(
            model_name='milestone',
            name='copied_from',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='milestones', to='cq.Milestone'),
        ),
    ]
