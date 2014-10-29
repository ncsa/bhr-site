# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import netfields.fields
from django.conf import settings


class Migration(migrations.Migration):

    replaces = [(b'bhr', '0001_initial'), (b'bhr', '0002_auto_20140908_2307'), (b'bhr', '0003_auto_20140910_2333'), (b'bhr', '0004_auto_20140911_1337'), (b'bhr', '0005_block_unblock_who')]

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
                ('added', models.DateTimeField(auto_now_add=True, verbose_name=b'date added')),
                ('unblock_at', models.DateTimeField(null=True, verbose_name=b'date to be unblocked')),
                ('flag', models.CharField(default=b'N', max_length=1, choices=[(b'N', b'None'), (b'I', b'Inbound'), (b'O', b'Outbound'), (b'B', b'Both')])),
                ('skip_whitelist', models.BooleanField(default=False)),
                ('forced_unblock', models.BooleanField(default=False)),
                ('unblock_why', models.TextField(blank=True)),
                ('who', models.ForeignKey(editable=False, to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BlockEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ident', models.CharField(max_length=50, verbose_name=b'blocker ident')),
                ('added', models.DateTimeField(auto_now_add=True, verbose_name=b'date added')),
                ('removed', models.DateTimeField(null=True, verbose_name=b'date removed')),
                ('entry', models.ForeignKey(to='bhr.Block')),
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
        migrations.AlterUniqueTogether(
            name='blockentry',
            unique_together=set([('entry', 'ident')]),
        ),
        migrations.RenameField(
            model_name='blockentry',
            old_name='entry',
            new_name='block',
        ),
        migrations.AlterUniqueTogether(
            name='blockentry',
            unique_together=set([('block', 'ident')]),
        ),
        migrations.AlterField(
            model_name='block',
            name='cidr',
            field=netfields.fields.CidrAddressField(max_length=43, db_index=True),
        ),
        migrations.AlterField(
            model_name='block',
            name='source',
            field=models.CharField(max_length=30, db_index=True),
        ),
        migrations.AlterField(
            model_name='block',
            name='who',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='block',
            name='forced_unblock',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AlterField(
            model_name='block',
            name='unblock_at',
            field=models.DateTimeField(null=True, verbose_name=b'date to be unblocked', db_index=True),
        ),
        migrations.AlterField(
            model_name='blockentry',
            name='ident',
            field=models.CharField(max_length=50, verbose_name=b'blocker ident', db_index=True),
        ),
        migrations.AlterField(
            model_name='blockentry',
            name='removed',
            field=models.DateTimeField(null=True, verbose_name=b'date removed', db_index=True),
        ),
        migrations.AddField(
            model_name='block',
            name='unblock_who',
            field=models.ForeignKey(related_name=b'+', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]
