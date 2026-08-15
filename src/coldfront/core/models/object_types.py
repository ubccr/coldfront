# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import inspect
from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import ManyToOneRel, Q
from django.db.models.fields.json import KT
from django.utils.translation import gettext as _

from coldfront.constants import CORE_APPS
from coldfront.plugins import PluginConfig
from coldfront.registry import registry
from coldfront.utils.strings import title

__all__ = (
    "ObjectType",
    "ObjectTypeManager",
    "ObjectTypeQuerySet",
)


class ObjectTypeQuerySet(models.QuerySet):
    def create(self, **kwargs):
        # If attempting to create a new ObjectType for a given app_label & model, replace those kwargs
        # with a reference to the ContentType (if one exists).
        if (app_label := kwargs.get("app_label")) and (model := kwargs.get("model")):
            try:
                kwargs["contenttype_ptr"] = ContentType.objects.get(app_label=app_label, model=model)
            except ObjectDoesNotExist:
                pass
        return super().create(**kwargs)


class ObjectTypeManager(models.Manager):
    def get_queryset(self):
        return ObjectTypeQuerySet(self.model, using=self._db)

    def get_by_natural_key(self, app_label, model):
        """
        Retrieve an ObjectType by its application label & model name.

        This method exists to provide parity with ContentTypeManager.
        """
        return self.get(app_label=app_label, model=model)

    def get_for_id(self, id):
        """
        Retrieve an ObjectType by its primary key (numeric ID).

        This method exists to provide parity with ContentTypeManager.
        """
        return self.get(pk=id)

    def _get_opts(self, model, for_concrete_model):
        if for_concrete_model:
            model = model._meta.concrete_model
        return model._meta

    def get_for_model(self, model, for_concrete_model=True):
        """
        Retrieve or create and return the ObjectType for a model.
        """

        # TODO: Check the request cache before hitting the database
        # cache = query_cache.get()
        # if cache is not None:
        #     if ot := cache["object_types"].get((model._meta.model, for_concrete_model)):
        #         return ot

        if not inspect.isclass(model):
            model = model.__class__
        opts = self._get_opts(model, for_concrete_model)

        try:
            # Use .get() instead of .get_or_create() initially to ensure db_for_read is honored (Django bug #20401).
            ot = self.get(app_label=opts.app_label, model=opts.model_name)
        except self.model.DoesNotExist:
            # If the ObjectType doesn't exist, create it. (Use .get_or_create() to avoid race conditions.)
            ot = self.get_or_create(
                app_label=opts.app_label,
                model=opts.model_name,
                public=ObjectType.model_is_public(model),
                features=ObjectType.get_model_features_dict(model),
            )[0]

        # TODO: Populate the request cache to avoid redundant lookups
        # if cache is not None:
        #     cache["object_types"][(model._meta.model, for_concrete_model)] = ot

        return ot

    def get_for_models(self, *models, for_concrete_models=True):
        """
        Retrieve or create the ObjectTypes for multiple models, returning a mapping {model: ObjectType}.

        This method exists to provide parity with ContentTypeManager.
        """

        results = {}

        # Compile the model and options mappings
        needed_models = defaultdict(set)
        needed_opts = defaultdict(list)
        for model in models:
            if not inspect.isclass(model):
                model = model.__class__
            opts = self._get_opts(model, for_concrete_models)
            needed_models[opts.app_label].add(opts.model_name)
            needed_opts[(opts.app_label, opts.model_name)].append(model)

        # Fetch existing ObjectType from the database
        condition = Q(
            *(
                Q(("app_label", app_label), ("model__in", model_names))
                for app_label, model_names in needed_models.items()
            ),
            _connector=Q.OR,
        )
        for ot in self.filter(condition):
            opts_models = needed_opts.pop((ot.app_label, ot.model), [])
            for model in opts_models:
                results[model] = ot

        # Create any missing ObjectTypes
        for (app_label, model_name), opts_models in needed_opts.items():
            for model in opts_models:
                results[model] = self.create(
                    app_label=app_label,
                    model=model_name,
                    public=ObjectType.model_is_public(model),
                    features=ObjectType.get_model_features_dict(model),
                )

        return results

    def public(self):
        """
        Includes only ObjectTypes for "public" models.

        Filter the base queryset to return only ObjectTypes corresponding to public models; those which are intended
        for reference by other objects within the application.
        """
        return self.get_queryset().filter(public=True)

    def with_feature(self, feature):
        """
        Return ObjectTypes only for models which support the given feature.

        Only ObjectTypes which list the specified feature will be included. Supported features are declared in the
        application registry under `registry["model_features"]`. For example, we can find all ObjectTypes for models
        which support event rules with:

            ObjectType.objects.with_feature('event_rules')
        """
        if feature not in registry["model_features"]:
            raise KeyError(
                f"{feature} is not a registered model feature! Valid features are: {registry['model_features'].keys()}"
            )
        return self.get_queryset().annotate(feature=KT(f"features__{feature}")).filter(feature="true")


class ObjectType(ContentType):
    """
    Wrap Django's native ContentType model to use our custom manager.
    """

    contenttype_ptr = models.OneToOneField(
        on_delete=models.CASCADE,
        to="contenttypes.ContentType",
        parent_link=True,
        primary_key=True,
        serialize=False,
        related_name="object_type",
    )
    public = models.BooleanField(
        default=False,
    )
    features = models.JSONField(
        blank=True,
        null=True,
    )

    objects = ObjectTypeManager()

    class Meta:
        verbose_name = _("object type")
        verbose_name_plural = _("object types")
        ordering = ("app_label", "model")

    @staticmethod
    def get_model_features(model):
        """
        Return all features supported by the given model as a list.
        """
        return [feature for feature, test_func in registry["model_features"].items() if test_func(model)]

    @staticmethod
    def get_model_features_dict(model):
        """
        Return all features supported by the given model as a dict.
        """
        features = {}
        feature_array = ObjectType.get_model_features(model)
        for f in feature_array:
            features[f] = True

        return features

    @staticmethod
    def model_is_public(model):
        """
        Return True if the model is considered "public use;" otherwise return False.

        All non-core and non-plugin models are excluded.
        """
        opts = model._meta
        if opts.app_label not in CORE_APPS and not isinstance(opts.app_config, PluginConfig):
            return False
        return not getattr(model, "_coldfront_private", False)

    @staticmethod
    def has_feature(model_or_ct, feature):
        """
        Returns True if the model supports the specified feature.
        """
        # If an ObjectType was passed, we can use it directly
        if type(model_or_ct) is ObjectType:
            ot = model_or_ct
        # If a ContentType was passed, resolve its model class
        elif type(model_or_ct) is ContentType:
            ot = ObjectType.objects.get_for_model(model_or_ct.model_class())
        # For anything else, look up the ObjectType
        else:
            ot = ObjectType.objects.get_for_model(model_or_ct)
        return feature in ot.features

    @staticmethod
    def get_related_models(model, ordered=True):
        """
        Return a list of all models which have a ForeignKey to the given model and the name of the field. For example,
        `get_related_models(Tenant)` will return all models which have a ForeignKey relationship to Tenant.
        """
        related_models = [
            (field.related_model, field.remote_field.name)
            for field in model._meta.related_objects
            if type(field) is ManyToOneRel and not getattr(field.related_model, "_coldfront_private", False)
        ]

        if ordered:
            return sorted(related_models, key=lambda x: x[0]._meta.verbose_name.lower())

        return related_models

    @staticmethod
    def identifier_string(object_type):
        """
        Return a "raw" ObjectType identifier string suitable for bulk import/export (e.g. "ras.project").
        """
        return f"{object_type.app_label}.{object_type.model}"

    @staticmethod
    def display_name(object_type, include_app=True):
        """
        Return a human-friendly ObjectType name (e.g. "RAS > Project").
        """
        try:
            meta = object_type.model_class()._meta
            app_label = title(meta.app_config.verbose_name)
            model_name = title(meta.verbose_name)
            if include_app:
                return f"{app_label} > {model_name}"
            return model_name
        except AttributeError:
            # Model does not exist
            return f"{object_type.app_label} > {object_type.model}"

    @property
    def app_labeled_name(self):
        # Override ContentType's "app | model" representation style.
        return f"{self.app_verbose_name} > {title(self.model_verbose_name)}"

    @property
    def app_verbose_name(self):
        if model := self.model_class():
            return model._meta.app_config.verbose_name

    @property
    def model_verbose_name(self):
        if model := self.model_class():
            return model._meta.verbose_name

    @property
    def model_verbose_name_plural(self):
        if model := self.model_class():
            return model._meta.verbose_name_plural

    @property
    def is_plugin_model(self):
        if not (model := self.model_class()):
            return  # Return null if model class is invalid
        return isinstance(model._meta.app_config, PluginConfig)
