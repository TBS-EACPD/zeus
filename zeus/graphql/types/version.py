import graphene

from django.contrib.auth import get_user_model
from zeus.graphql.utils import (
    non_serializable_field,
    NonSerializable,
)
from zeus.graphql.dataloader import PrimaryKeyDataLoaderFactory


class Version(graphene.ObjectType):
    edited_by = NonSerializable()
    instance = NonSerializable()

    @staticmethod
    @non_serializable_field
    def resolve_edited_by(parent, info):
        user_id = parent["instance"].edited_by_id
        if user_id is None:
            return None

        User = get_user_model()
        UserDataloader = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(User)
        user_dataloader = UserDataloader(info.context.dataloaders)
        return user_dataloader.load(user_id)

    @staticmethod
    @non_serializable_field
    def resolve_instance(parent, _info):
        return parent["instance"]
