# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bhr', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='blockentry',
            old_name='entry',
            new_name='block',
        ),
        migrations.AlterUniqueTogether(
            name='blockentry',
            unique_together=set([('block', 'ident')]),
        ),
    ]
