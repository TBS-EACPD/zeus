import graphene

from zeus.graphql.utils import non_serializable_field, NonSerializable
from zeus.graphql.types.version import Version


class HasNonSerializableRecordMixin(graphene.ObjectType):
    class Meta:
        abstract = True

    record = graphene.Field(NonSerializable)
    most_recent_version = graphene.Field(Version)

    @staticmethod
    def get_orm_instance_from_resolver_parent(resolver_parent):
        return resolver_parent

    @classmethod
    @non_serializable_field
    def resolve_record(cls, parent, _info):
        return cls.get_orm_instance_from_resolver_parent(parent)
