import asyncio
import inspect

from django.utils.html import escape
from django.db.models import ForeignKey, ManyToManyField

from django.utils.functional import cached_property

import graphene

from zeus.changelog.text import tm
from zeus.graphql.utils import (
    non_serializable_field,
    NonSerializable,
)
from zeus.graphql.dataloader import PrimaryKeyDataLoaderFactory

from zeus.changelog.diff_utils import text_compare_inline, list_diff


# this is used by the parent resolver and fed to the below graphene type
class DiffObject:
    def __init__(self, current_version, previous_version, field_obj, dataloader_cache):
        self.current_version = current_version
        self.previous_version = previous_version
        self.field = field_obj
        self.dataloader_cache = dataloader_cache


class ScalarDiffObject(DiffObject):
    @cached_property
    def _diffs(self):
        prev_db_value = self.previous_version.serializable_value(self.field.name)
        current_db_value = self.current_version.serializable_value(self.field.name)

        if self.field.choices:
            # if a field is a choice field e.g. chars or ints used to represent a list of choices,
            # then its value is just that database, non-bilingual char/int value
            # fortunately model instances provide a hook to get the displayed, translated value
            choices_by_attr_value = dict(self.field.choices)
            if not choices_by_attr_value.get(None, None):
                choices_by_attr_value[None] = tm("empty")
            previous_value = choices_by_attr_value.get(prev_db_value, prev_db_value)
            current_value = choices_by_attr_value.get(current_db_value, current_db_value)

        else:  # just use the normal attribute
            previous_value = prev_db_value
            current_value = current_db_value

        joint, before, after = text_compare_inline(
            get_str_val(previous_value), get_str_val(current_value),
        )

        return (joint, before, after)

    def get_combined_diff(self):
        return self._diffs[0]

    def get_before_diff(self):
        return self._diffs[1]

    def get_after_diff(self):
        return self._diffs[2]


class CreateDiff:
    def __init__(self):
        self.field = None

    def _get_created_str(self):
        return escape(tm("created"))

    def get_before_diff(self):
        return ""

    def get_after_diff(self):
        return self._get_created_str()

    def get_combined_diff(self):
        return self._get_created_str()


class DeleteDiff:
    def __init__(self):
        self.field = None

    def _get_deleted_str(self):
        return escape(tm("deleted"))

    def get_before_diff(self):
        return ""

    def get_after_diff(self):
        return self._get_deleted_str()

    def get_combined_diff(self):
        return self._get_deleted_str()


class AsyncDiffObject(DiffObject):
    async def _compute_diffs(self):
        raise NotImplementedError()

    async def _get_diffs(self):
        if hasattr(self, "_diff_result"):
            return self._diff_result

        diffs = await self._compute_diffs()
        self._diff_result = diffs
        return diffs

    async def get_combined_diff(self):
        diffs = await self._get_diffs()
        return diffs[0]

    async def get_before_diff(self):
        diffs = await self._get_diffs()
        return diffs[1]

    async def get_after_diff(self):
        diffs = await self._get_diffs()
        return diffs[2]


class M2MDiffObject(AsyncDiffObject):
    async def _compute_diffs(self):
        prev_id_list = self.previous_version.get_m2m_ids(self.field.name)
        current_id_list = self.current_version.get_m2m_ids(self.field.name)

        related_model = self.field.related_model
        related_dataloader_cls = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(
            related_model
        )
        related_dataloader = related_dataloader_cls(self.dataloader_cache)

        prev_instances, current_instances = await asyncio.gather(
            related_dataloader.load_many(prev_id_list),
            related_dataloader.load_many(current_id_list),
        )

        get_name = lambda inst: inst.name
        before_list = sorted([*prev_instances], key=get_name)
        after_list = sorted([*current_instances], key=get_name)

        joint, before, after = list_diff(before_list, after_list)

        return (joint, before, after)


class ForeignKeyDiffObject(AsyncDiffObject):
    async def _compute_diffs(self):
        prev_db_value = self.previous_version.serializable_value(self.field.name)
        current_db_value = self.current_version.serializable_value(self.field.name)

        related_model = self.field.remote_field.model
        related_dataloader_cls = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(
            related_model
        )
        dataloader = related_dataloader_cls(self.dataloader_cache)

        if prev_db_value is None:
            previous_instance = None
            current_instance = await dataloader.load(current_db_value)
        elif current_db_value is None:
            previous_instance = await dataloader.load(prev_db_value)
            current_instance = None
        else:
            previous_instance, current_instance = await dataloader.load_many(
                [prev_db_value, current_db_value]
            )

        joint, before, after = text_compare_inline(
            get_str_val(previous_instance), get_str_val(current_instance),
        )

        return joint, before, after


def is_field_different_accross_versions(current_version, previous_version, field_name):
    current_db_value = current_version.serializable_value(field_name)
    prev_db_value = previous_version.serializable_value(field_name)
    if current_db_value == prev_db_value or (
        # consider "" vs. None to be non-diff worthy
        {current_db_value, prev_db_value}.issubset({None, ""})
    ):
        return False
    return True


def get_field_diff_for_version_pair(
    current_version, previous_version, field_obj, dataloaders
):
    if not is_field_different_accross_versions(
        current_version, previous_version, field_obj.name
    ):
        return None

    if isinstance(field_obj, ManyToManyField):
        DiffClass = M2MDiffObject
    elif isinstance(field_obj, ForeignKey):
        DiffClass = ForeignKeyDiffObject
    else:
        DiffClass = ScalarDiffObject

    diff_obj = DiffClass(current_version, previous_version, field_obj, dataloaders)
    return diff_obj


def get_str_val(fetched_field_value):
    if isinstance(fetched_field_value, str):
        return escape(fetched_field_value)
    elif fetched_field_value in (None, ""):
        return escape(tm("empty"))
    if isinstance(fetched_field_value, object):
        return escape(fetched_field_value.__str__())


async def m2m_display_value(version, field_obj, dataloader_cache):
    id_list = version.get_m2m_ids(field_obj.name)
    if not id_list:
        return tm("empty")
    related_model = field_obj.related_model
    related_dataloader_cls = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(
        related_model
    )
    related_dataloader = related_dataloader_cls(dataloader_cache)
    related_instances = await related_dataloader.load_many(id_list)

    sorted_names = sorted([inst.name for inst in related_instances])
    return "".join([f"<p>{name}</p>" for name in sorted_names])


async def foreign_key_display_value(version, field_obj, dataloader_cache):
    related_id = version.serializable_value(field_obj.name)
    if related_id is None:
        return tm("empty")
    related_model = field_obj.related_model
    related_dataloader_cls = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(
        related_model
    )
    related_dataloader = related_dataloader_cls(dataloader_cache)

    related_instance = await related_dataloader.load(related_id)
    return get_str_val(related_instance)


def get_display_value(version, field_obj, dataloader_cache):
    if isinstance(field_obj, ManyToManyField):
        return m2m_display_value(version, field_obj, dataloader_cache)

    if isinstance(field_obj, ForeignKey):
        return foreign_key_display_value(version, field_obj, dataloader_cache)

    if field_obj.choices:
        db_value = version.serializable_value(field_obj.name)
        choices_by_attr_value = dict(field_obj.choices)
        if not choices_by_attr_value.get(None, None):
            choices_by_attr_value[None] = tm("empty")
        str_val = choices_by_attr_value.get(db_value, db_value)
        return get_str_val(str_val)

    else:
        # use normal attribute
        val = getattr(version, field_obj.name)
        if not val:
            return tm("empty")
        return val


class Diff(graphene.ObjectType):
    diffed_before = graphene.String()
    diffed_after = graphene.String()
    diffed_combined = graphene.String()
    action = graphene.String()
    field_name = graphene.String()
    field = NonSerializable()

    @staticmethod
    @non_serializable_field
    def resolve_field(parent, _info):
        return parent.field

    @staticmethod
    def resolve_field_name(parent, _info):
        field_obj = parent.field
        if field_obj is None:
            return None
        return field_obj.name

    @staticmethod
    def resolve_action(parent, _info):
        if isinstance(parent, CreateDiff):
            return tm("created")
        elif isinstance(parent, DeleteDiff):
            return tm("deleted")
        else:
            return tm("edited")

    @staticmethod
    def resolve_diffed_before(parent, _info):
        return parent.get_before_diff()

    @staticmethod
    def resolve_diffed_after(parent, _info):
        return parent.get_after_diff()

    @staticmethod
    def resolve_diffed_combined(parent, _info):
        return parent.get_combined_diff()
