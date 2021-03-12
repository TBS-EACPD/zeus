from django.db.models import ForeignKey, ManyToManyField

import graphene
from graphene import DateTime, List, String

from zeus.changelog.util import get_diffable_fields_for_model
from zeus.graphql.utils import NonSerializable, non_serializable_field

from .diff import (
    Diff,
    get_display_value,
    get_field_diff_for_version_pair,
    is_field_different_accross_versions,
)


class ChangelogEntryFieldEntry(graphene.ObjectType):
    diff = graphene.Field(Diff)
    field_name = graphene.String()
    field = graphene.String()
    previous_display_value = graphene.String()
    current_display_value = graphene.String()
    has_difference = graphene.Boolean()

    @staticmethod
    def resolve_diff(parent, info):
        if parent["previous_version"] is None:
            return None

        return get_field_diff_for_version_pair(
            parent["version"],
            parent["previous_version"],
            parent["field"],
            info.context.dataloaders,
        )

    @staticmethod
    def resolve_previous_display_value(parent, info):
        if parent["previous_version"] is None:
            return None
        return get_display_value(
            parent["previous_version"], parent["field"], info.context.dataloaders
        )

    @staticmethod
    def resolve_current_display_value(parent, info):
        return get_display_value(
            parent["version"], parent["field"], info.context.dataloaders
        )

    @staticmethod
    def resolve_field(parent, info):
        return parent["field"].name

    @staticmethod
    def resolve_field_name(parent, info):
        return parent["field"].verbose_name

    @staticmethod
    def resolve_has_difference(parent, _info):
        if not parent["previous_version"]:
            return None
        return is_field_different_accross_versions(
            parent["version"], parent["previous_version"], parent["field"].name
        )
