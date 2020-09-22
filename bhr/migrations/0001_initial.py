# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import netfields.fields
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Block',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cidr', netfields.fields.CidrAddressField(max_length=43)),
                ('source', models.CharField(max_length=30)),
                ('why', models.TextField()),
                ('added', models.DateTimeField(auto_now_add=True, verbose_name='date added')),
                ('unblock_at', models.DateTimeField(null=True, verbose_name='date to be unblocked')),
                ('flag', models.CharField(default='N', max_length=1, choices=[('N', 'None'), ('I', 'Inbound'),
                                                                               ('O', 'Outbound'), ('B', 'Both')])),
                ('skip_whitelist', models.BooleanField(default=False)),
                ('forced_unblock', models.BooleanField(default=False)),
                ('unblock_why', models.TextField(blank=True)),
                ('who', models.ForeignKey(on_delete=models.PROTECT, editable=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BlockEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ident', models.CharField(max_length=50, verbose_name='blocker ident')),
                ('added', models.DateTimeField(auto_now_add=True, verbose_name='date added')),
                ('removed', models.DateTimeField(null=True, verbose_name='date removed')),
                ('entry', models.ForeignKey(to='bhr.Block', on_delete=models.PROTECT)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WhitelistEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cidr', netfields.fields.CidrAddressField(max_length=43)),
                ('why', models.TextField()),
                ('added', models.DateTimeField(auto_now_add=True, verbose_name='date added')),
                ('who', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL, on_delete=models.PROTECT)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='blockentry',
            unique_together={('entry', 'ident')},
        ),
    ]
