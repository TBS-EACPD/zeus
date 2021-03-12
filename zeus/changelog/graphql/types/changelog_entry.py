from django.db.models import ForeignKey, ManyToManyField

import graphene
from graphene import DateTime, List, String

from zeus.changelog.util import get_diffable_fields_for_model
from zeus.graphql.types.version import Version
from zeus.graphql.utils import NonSerializable, non_serializable_field

from .changelog_entry_field_entry import ChangelogEntryFieldEntry
from .diff import CreateDiff, Diff, get_field_diff_for_version_pair


class ChangelogEntry(graphene.ObjectType):
    diffs = List(Diff,)
    field_entries = List(ChangelogEntryFieldEntry)
    model_name = graphene.String()
    live_name = graphene.String()
    edit_date = graphene.DateTime()

    eternal = NonSerializable()
    version = graphene.Field(Version)
    previous_version = graphene.Field(Version)

    is_annotated = graphene.Boolean()

    @staticmethod
    def resolve_version(parent, _info):
        return {"instance": parent["version"]}

    @staticmethod
    def resolve_previous_version(parent, _info):
        if not parent["previous_version"]:
            return None
        return {"instance": parent["previous_version"]}

    @staticmethod
    @non_serializable_field
    def resolve_eternal(parent, _info):
        return parent["eternal"]

    @staticmethod
    def resolve_edit_date(parent, _info):
        return parent["version"].business_date

    @staticmethod
    def resolve_model_name(parent, _info):
        return parent["eternal"].__class__._meta.verbose_name

    @staticmethod
    def resolve_live_name(parent, _info):
        live_obj = parent["eternal"]
        if hasattr(live_obj, "name"):
            return live_obj.name

        return live_obj.__str__()

    @staticmethod
    def resolve_is_annotated(parent, _info):
        version = parent["version"]

        is_cosmestic_change = version.cosmetic_change
        has_either_lang_filled_out = bool(
            version.reason_for_substantive_change_en
            or version.reason_for_substantive_change_fr
        )
        is_creation = parent["previous_version"] is None

        return is_cosmestic_change or has_either_lang_filled_out or is_creation

    @staticmethod
    def resolve_diffs(parent, info):
        specified_fields = parent.get("fields", None)
        this_version = parent["version"]
        prev_version = parent["previous_version"]

        if prev_version is None:
            # filter out creations if fields are specified
            if specified_fields:
                return []
            eternal = parent["eternal"]
            return [CreateDiff()]

        fields_to_diff = get_diffable_fields_for_model(this_version.live_model)
        if specified_fields:
            fields_to_diff = [f for f in fields_to_diff if f.name in specified_fields]

        field_diff_objs = []
        for f in fields_to_diff:
            field_diff_obj = get_field_diff_for_version_pair(
                this_version, prev_version, f, info.context.dataloaders
            )
            if field_diff_obj is not None:
                field_diff_objs.append(field_diff_obj)

        return field_diff_objs

    @staticmethod
    def resolve_field_entries(parent, _info):
        field_objs = get_diffable_fields_for_model(parent["version"].live_model)

        return [
            {
                "version": parent["version"],
                "previous_version": parent["previous_version"],
                "field": field,
            }
            for field in field_objs
        ]
