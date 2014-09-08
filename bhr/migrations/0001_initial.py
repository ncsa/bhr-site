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
                ('ident', models.CharField(max_length=50, verbose_name=b'blocker ident')),
                ('added', models.DateTimeField(verbose_name=b'date added')),
                ('removed', models.DateTimeField(null=True, verbose_name=b'date removed')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BlockEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cidr', netfields.fields.CidrAddressField(max_length=43)),
                ('source', models.CharField(max_length=30)),
                ('why', models.TextField()),
                ('added', models.DateTimeField(auto_now_add=True, verbose_name=b'date added')),
                ('unblock_at', models.DateTimeField(null=True, verbose_name=b'date to be unblocked')),
                ('flag', models.CharField(default=b'N', max_length=1, choices=[(b'N', b'None'), (b'I', b'Inbound'), (b'O', b'Outbound'), (b'B', b'Both')])),
                ('skip_whitelist', models.BooleanField(default=False)),
                ('forced_unblock', models.BooleanField(default=False)),
                ('unblock_why', models.TextField(blank=True)),
                ('block_count', models.IntegerField()),
                ('who', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
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
                ('added', models.DateTimeField(auto_now_add=True, verbose_name=b'date added')),
                ('who', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='block',
            name='entry',
            field=models.ForeignKey(to='bhr.BlockEntry'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='block',
            unique_together=set([('entry', 'ident')]),
        ),
    ]
