from django.contrib.auth import get_user_model

import graphene

from zeus.graphql.dataloader import PrimaryKeyDataLoaderFactory
from zeus.graphql.utils import NonSerializable, non_serializable_field


class Version(graphene.ObjectType):
    edited_by = NonSerializable()
    instance = NonSerializable()

    @staticmethod
    def resolve_edited_by(parent, info):
        UserModel = get_user_model()
        UserDataloader = PrimaryKeyDataLoaderFactory.get_model_by_id_loader(UserModel)
        user_dataloader = UserDataloader(info.context.dataloaders)
        return user_dataloader.load(parent["instance"].edited_by_id)

    @staticmethod
    def resolve_instance(parent, _info):
        return parent["instance"]
