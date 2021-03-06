# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-26 09:10
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Photo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path', models.CharField(max_length=200)),
                ('likes_cnt', models.IntegerField()),
                ('created_date', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='PhotoLikes',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('like_date', models.DateField()),
                ('photo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='photo_likers.Photo')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
            ],
            options={
                'managed': True,
            },
        ),
        migrations.AddField(
            model_name='photo',
            name='tags',
            field=models.ManyToManyField(to='photo_likers.Tag', verbose_name='Tags'),
        ),
    ]
