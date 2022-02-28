from django.db import models
from django.db.models import F, Manager, OuterRef, QuerySet, Subquery
from django.db.models.base import ModelBase
from django.db.models.signals import m2m_changed, post_save
from django.utils import timezone

# other imports, to remove


class VersioningException(Exception):
    pass


class VersioningConfigException(VersioningException):
    pass


def find_m2m_field(from_class, to_class):
    return next(
        rel
        for rel in from_class._meta.get_fields()
        if isinstance(rel, models.ManyToManyField) and rel.related_model is to_class
    )


def on_m2m_change(instance, action, model, pk_set, **_kwargs):
    field = find_m2m_field(instance.__class__, model)

    hidden_attr = f"_{field.name}_m2m_ids"
    if not hasattr(instance, hidden_attr):

        # m2m changes, when performed on their own, wont trigger a new version. So we call .save() to force a new version
        # BUT, a form is expected to create a single version
        # so we keep track of this state manually via an attribute
        # TODO: find a way to autmatically clear this attribute
        if not (
            hasattr(instance, "_apply_changes_to_last_ver")
            and instance._apply_changes_to_last_ver
        ):
            instance.save()

        initial_ids = [obj.pk for obj in getattr(instance, field.name).all()]
        setattr(instance, hidden_attr, initial_ids)

    if action in ("post_add", "post_remove"):
        old_ids = getattr(instance, hidden_attr)
        if action == "post_remove":
            new_ids = set(old_ids) - set(pk_set)

        if action == "post_add":
            new_ids = set(old_ids).union(set(pk_set))

        new_ids = sorted(new_ids)
        setattr(instance, hidden_attr, new_ids)

        related_versions = instance.versions
        related_versions.last().set_m2m(field, new_ids)


def save_copy_post_save(sender, instance, **_kwargs):
    if hasattr(sender, "_history_class"):
        if (
            hasattr(instance, "_apply_changes_to_last_ver")
            and instance._apply_changes_to_last_ver
        ):
            sender._history_class.update_instance_version(instance)
        else:
            sender._history_class.create_from_original(instance)

        setattr(instance, "_apply_changes_to_last_ver", True)

    setattr(instance, "_apply_changes_to_last_ver", True)


class HistoryQueryset(QuerySet):
    def with_previous_version_id(self):
        # we need a non-filtered QS clone of the same type
        another_qs = HistoryQueryset(self.model, self._db)
        prev_version_id_subquery = Subquery(
            another_qs.filter(
                eternal_id=OuterRef("eternal_id"),
                business_date__lt=OuterRef("business_date"),
            )
            .order_by("-business_date")
            .values("id")[:1]
        )
        return self.annotate(previous_version_id=prev_version_id_subquery)

    def with_most_recent_version_id(self):
        most_recent_version_id_subquery = Subquery(
            self.model.objects.filter(eternal_id=OuterRef("eternal_id"))
            .order_by("-business_date")
            .values("pk")[:1]
        )
        return self.annotate(most_recent_version_id=most_recent_version_id_subquery)

    def only_most_recent_versions(self):
        return self.with_most_recent_version_id().filter(id=F("most_recent_version_id"))


class HistoryManager(Manager):
    def get_queryset(self):
        return HistoryQueryset(self.model, using=self._db)

    def latest_versions_for_eternal_ids(self, eternal_ids):

        return self.model.objects.filter(
            eternal_id__in=eternal_ids
        ).only_most_recent_versions()


def m2m_default_empty_list():
    return []


def create_version_field_from_live_field(field):
    name = field.attname

    ## forces uses of id as the primary key
    if name == "id":
        new_field = models.ForeignKey(
            field.model, on_delete=models.CASCADE, related_name="versions",
        )
        return "eternal", new_field

    if isinstance(field, models.ForeignKey):
        FieldClass = field.__class__
        related_model = field.remote_field.model
        related_name = "+"
        if field.many_to_one:
            new_field = FieldClass(
                related_model,
                verbose_name=field.verbose_name,
                null=True,
                on_delete=models.SET_NULL,
                default=field.default,
                related_name=related_name,
            )
            name = field.name
        elif field.one_to_one:
            # 1-1 with live table becomes 1-many with version table
            new_field = models.ForeignKey(
                field.target_field.model,
                verbose_name=field.verbose_name,
                null=True,
                on_delete=models.SET_NULL,
                default=field.default,
                related_name=related_name,
            )
            name = field.name
        else:
            raise VersioningConfigException("Unexpected foreignkey type")

    else:
        new_field = clone_with_unique_false(field)
        new_field.primary_key = False

    new_field.choices = field.choices

    return name, new_field


def clone_with_unique_false(field):
    name, path, args, kwargs = field.deconstruct()
    if kwargs.get("unique", False):
        new_kwargs = {
            **kwargs,
            "unique": False,
        }
    else:
        new_kwargs = kwargs
    return field.__class__(*args, **new_kwargs)


class VersionModelMeta(ModelBase):
    def __new__(cls, cls_name, bases, cls_attrs, **kwargs):

        options = cls_attrs.get("Meta", None)

        if getattr(options, "abstract", False):
            return super().__new__(cls, cls_name, bases, cls_attrs, **kwargs)
        else:
            return cls._create_version_class(cls, cls_name, bases, cls_attrs, **kwargs)

    @staticmethod
    def _create_version_class(cls, cls_name, bases, cls_attrs, **kwargs):

        try:
            live_model = cls_attrs["live_model"]
        except (AttributeError, KeyError) as e:
            raise VersioningConfigException(
                "must define live_model attribute on version class"
            )

        if hasattr(live_model, "_history_class"):
            raise VersioningConfigException(
                "cannot define 2 history classes for a single model"
            )

        version_cls = super().__new__(cls, cls_name, bases, cls_attrs, **kwargs)

        versioned_fields = cls._get_versioned_fields(live_model, version_cls)
        for name, field_obj in versioned_fields.items():
            field_obj.contribute_to_class(version_cls, name)

        # many-to-many
        versioned_m2m_fields = cls._create_m2m_fields(version_cls, live_model)
        version_cls.m2m_fields = versioned_m2m_fields.values()
        for name, field_obj in versioned_m2m_fields.items():
            field_obj.contribute_to_class(version_cls, name)

        live_model._history_class = version_cls
        cls._attach_signals(live_model)
        live_model.reset_version_attrs = VersionModelMeta.reset_version_attrs

        return version_cls

    @staticmethod
    def _get_versioned_fields(live_model, version_cls):
        tracked_fields = version_cls.get_fields_to_version()

        versioned_fields = {}
        for field in tracked_fields:
            new_name, new_field = create_version_field_from_live_field(field)
            versioned_fields[new_name] = new_field

        return versioned_fields

    @staticmethod
    def _create_m2m_fields(version_cls, live_model):
        m2m_fields_to_add = {}
        for field in version_cls.get_m2m_fields_to_version():
            new_field = models.JSONField(default=m2m_default_empty_list)
            m2m_fields_to_add[field.name] = new_field

        return m2m_fields_to_add

    @staticmethod
    def _attach_signals(live_model):
        post_save.connect(save_copy_post_save, live_model)

        for field in live_model._meta.many_to_many:
            through_model = getattr(live_model, field.name).through
            m2m_changed.connect(on_m2m_change, sender=through_model)

    # 'self' here refers to live model, we attach this dynamically
    def reset_version_attrs(self):
        if hasattr(self, "_apply_changes_to_last_ver"):
            del self._apply_changes_to_last_ver

        for field in self._meta.many_to_many:
            hidden_attr = f"_{field.name}_m2m_ids"
            if hasattr(self, hidden_attr):
                delattr(self, hidden_attr)


class VersionModel(models.Model, metaclass=VersionModelMeta):
    # you can subclass this class to add versioning columns (e.g. version-name, timestamp)
    class Meta:
        abstract = True

    objects = HistoryManager()

    system_date = models.DateTimeField(default=timezone.now)

    @classmethod
    def get_fields_to_version(cls):
        # override to include/exclude individual fields from the live model
        return cls.live_model._meta.fields

    @classmethod
    def get_m2m_fields_to_version(cls):
        # override to include/exclude individual fields from the live model
        return cls.live_model._meta.many_to_many

    @classmethod
    def build_from_original(cls, live_instance, m2m_dict=None):
        instance_dict = {
            f.attname: live_instance.serializable_value(f.name)
            for f in cls.get_fields_to_version()
            if not f.name in ["id"]
        }

        instance_dict.update(
            {
                f.attname: cls.serialize_m2m_ids(
                    [related.id for related in getattr(live_instance, f.name).all()]
                )
                for f in cls.m2m_fields
            }
        )

        instance_dict["eternal"] = live_instance
        ver = cls(**instance_dict)
        return ver

    @classmethod
    def create_from_original(cls, live_instance):
        ver = cls.build_from_original(live_instance)
        ver.save()
        return ver

    @classmethod
    def update_instance_version(cls, instance):
        version = instance.versions.last()
        # update all non-m2m fields
        for f in cls.live_model._meta.fields:
            if not f.name in ["id", "system_date"]:
                setattr(version, f.attname, instance.serializable_value(f.name))

        version.save()

    @staticmethod
    def serialize_m2m_ids(pk_list):
        return sorted(pk_list)

    def get_m2m_ids(self, key):
        getattr(self, key)

    def set_m2m(self, field, pk_set):
        setattr(self, field.name, self.serialize_m2m_ids(pk_set))
        self.save()

    def recreate_original(self):
        live_fields = [f for f in self.live_model._meta.fields if f.name != "id"]
        record_attrs = {f.attname: getattr(self, f.attname) for f in live_fields}

        obj = self.live_model(**record_attrs)
        obj.id = obj.pk = self.eternal_id

        # defensively remove this temporary object's save method
        def new_save():
            raise VersioningException("can't save live-obj recreated from a version")

        setattr(obj, "save", new_save)

        return obj
