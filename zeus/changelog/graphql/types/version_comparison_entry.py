from django.db.models import ForeignKey, ManyToManyField

import graphene
from graphene import DateTime, List, String

from zeus.changelog.graphql.types.version import Version
from zeus.changelog.util import get_diffable_fields_for_model
from zeus.graphql.dataloader import PrimaryKeyDataLoaderFactory
from zeus.graphql.utils import NonSerializable, non_serializable_field

from .diff import CreateDiff, DeleteDiff, Diff, get_field_diff_for_version_pair


class VersionComparisonEntry(graphene.ObjectType):
    model_name = graphene.String()

    @staticmethod
    def resolve_model_name(parent, info):
        return parent["model"].live_model.__name__

    eternal = NonSerializable()

    @staticmethod
    def resolve_eternal(parent, info):
        model = parent["model"].live_model
        id = parent["eternal_id"]
        LoaderCls = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(model)
        return LoaderCls(info.context.dataloaders).load(id)

    left_version = graphene.Field(Version)

    @staticmethod
    def resolve_left_version(parent, info):
        model = parent["model"]
        id = parent["left_id"]

        if id is None:
            return None

        LoaderCls = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(model)
        version = yield LoaderCls(info.context.dataloaders).load(id)
        return {"instance": version}

    right_version = graphene.Field(Version)

    @staticmethod
    def resolve_right_version(parent, info):
        model = parent["model"]
        id = parent["right_id"]

        if id is None:
            return None

        LoaderCls = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(model)
        version = yield LoaderCls(info.context.dataloaders).load(id)
        return {"instance": version}

    diffs = List(Diff)

    @staticmethod
    def resolve_diffs(parent, info):
        if not parent["right_id"]:
            return [DeleteDiff()]
        if not parent["left_id"]:
            return [CreateDiff()]

        history_model = parent["model"]
        live_model = history_model.live_model
        fields_to_diff = get_diffable_fields_for_model(live_model)

        LoaderCls = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(history_model)
        loader_inst = LoaderCls(info.context.dataloaders)
        left_ver = yield loader_inst.load(parent["left_id"])
        right_ver = yield loader_inst.load(parent["right_id"])

        field_diff_objs = []
        for f in fields_to_diff:
            field_diff_obj = get_field_diff_for_version_pair(
                right_ver, left_ver, f, info.context.dataloaders
            )
            if field_diff_obj is not None:
                field_diff_objs.append(field_diff_obj)

        return field_diff_objs
