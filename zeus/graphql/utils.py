import inspect
import functools

from django.db.models import Model

import graphene


class NonSerializable(graphene.Scalar):
    @staticmethod
    def serialize(obj):
        return obj


def _stringify_internal_python_value(val):
    if isinstance(val, Model):
        # if the model's __str__ methods issues queries
        # it can be misleading when investigating N+1 queries with graphiql
        return f"<{val.__class__.__name__} {val.pk}>"

    return object.__str__(val)


def non_serializable_field(func):
    """
        decorate a resolver
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)

        info = args[1]
        if len(args) == 3:
            # if we're dealing with a class or instance method, info will be third
            info = args[2]

        if info.context.requires_serializable:
            if inspect.isawaitable(ret):
                val = await ret
                return _stringify_internal_python_value(val)

            return _stringify_internal_python_value(ret)

        return ret

    return wrapper


class HasNonSerializableRecordMixin(graphene.ObjectType):
    record = graphene.Field(NonSerializable)

    @non_serializable_field
    def resolve_record(self, _info):
        return self
