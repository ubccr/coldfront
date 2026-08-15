# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import coldfront.users.models.users


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="ObjectPermission",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="name")),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                ("enabled", models.BooleanField(default=True, verbose_name="enabled")),
                (
                    "actions",
                    models.JSONField(
                        blank=True,
                        help_text="The list of actions granted by this permission",
                        null=True,
                        verbose_name="actions",
                    ),
                ),
                (
                    "constraints",
                    models.JSONField(
                        blank=True,
                        help_text="Queryset filter matching the applicable objects of the selected type(s)",
                        null=True,
                        verbose_name="constraints",
                    ),
                ),
                (
                    "object_types",
                    models.ManyToManyField(related_name="object_permissions", to="contenttypes.contenttype"),
                ),
            ],
            options={
                "verbose_name": "permission",
                "verbose_name_plural": "permissions",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="name")),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "weight",
                    models.PositiveSmallIntegerField(
                        default=100,
                        help_text="Weight is used for ordering and precedence resolution.",
                        verbose_name="weight",
                    ),
                ),
                (
                    "object_permissions",
                    models.ManyToManyField(blank=True, related_name="roles", to="users.objectpermission"),
                ),
            ],
            options={
                "verbose_name": "role",
                "verbose_name_plural": "roles",
                "ordering": ("weight", "name"),
            },
        ),
        migrations.CreateModel(
            name="Group",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True, verbose_name="name")),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                (
                    "permissions",
                    models.ManyToManyField(
                        blank=True,
                        related_name="groups",
                        related_query_name="group",
                        to="auth.permission",
                        verbose_name="permissions",
                    ),
                ),
                (
                    "object_permissions",
                    models.ManyToManyField(blank=True, related_name="groups", to="users.objectpermission"),
                ),
                ("roles", models.ManyToManyField(blank=True, related_name="groups", to="users.role")),
            ],
            options={
                "verbose_name": "group",
                "verbose_name_plural": "groups",
                "ordering": ("name",),
            },
            managers=[
                ("objects", coldfront.users.models.users.GroupManager()),
            ],
        ),
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={"unique": "A user with that username already exists."},
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[django.contrib.auth.validators.UnicodeUsernameValidator()],
                        verbose_name="username",
                    ),
                ),
                ("first_name", models.CharField(blank=True, max_length=150, verbose_name="first name")),
                ("last_name", models.CharField(blank=True, max_length=150, verbose_name="last name")),
                ("email", models.EmailField(blank=True, max_length=254, verbose_name="email address")),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now, verbose_name="date joined")),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="users",
                        related_query_name="user",
                        to="users.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "object_permissions",
                    models.ManyToManyField(blank=True, related_name="users", to="users.objectpermission"),
                ),
                ("roles", models.ManyToManyField(blank=True, related_name="users", to="users.role")),
            ],
            options={
                "verbose_name": "user",
                "verbose_name_plural": "users",
                "ordering": ("username",),
            },
            managers=[
                ("objects", coldfront.users.models.users.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Token",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("description", models.CharField(blank=True, max_length=200, verbose_name="description")),
                ("created", models.DateTimeField(auto_now_add=True, verbose_name="created")),
                ("expires", models.DateTimeField(blank=True, null=True, verbose_name="expires")),
                ("last_used", models.DateTimeField(blank=True, null=True, verbose_name="last used")),
                (
                    "enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Disable to temporarily revoke this token without deleting it.",
                        verbose_name="enabled",
                    ),
                ),
                (
                    "write_enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Permit create/update/delete operations using this token",
                        verbose_name="write enabled",
                    ),
                ),
                (
                    "key",
                    models.CharField(
                        help_text="v2 token identification key",
                        max_length=12,
                        unique=True,
                        validators=[django.core.validators.MinLengthValidator(12)],
                        verbose_name="key",
                    ),
                ),
                (
                    "pepper_id",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        help_text="ID of the cryptographic pepper used to hash the token",
                        null=True,
                        verbose_name="pepper ID",
                    ),
                ),
                (
                    "hmac_digest",
                    models.CharField(
                        help_text="SHA256 hash of the token and pepper (v2 only)", max_length=64, verbose_name="digest"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="tokens", to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "verbose_name": "token",
                "verbose_name_plural": "tokens",
                "ordering": ("-created",),
            },
        ),
        migrations.CreateModel(
            name="UserConfig",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.JSONField(default=dict)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE, related_name="config", to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                "verbose_name": "user preferences",
                "verbose_name_plural": "user preferences",
                "ordering": ["user"],
            },
        ),
    ]
