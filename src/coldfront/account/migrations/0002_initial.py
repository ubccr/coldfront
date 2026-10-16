# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("account", "0001_initial"),
        ("users", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserToken",
            fields=[],
            options={
                "verbose_name": "token",
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("users.token",),
        ),
        migrations.AddField(
            model_name="thirdpartyaccount",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="third_party_accounts",
                to=settings.AUTH_USER_MODEL,
                verbose_name="user",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="thirdpartyaccount",
            unique_together={("provider", "account_id"), ("user", "provider")},
        ),
    ]
