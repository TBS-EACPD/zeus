from inspect import isgenerator

from graphql.execution.middleware import make_it_promise
from promise import is_thenable

from .utils import (
    NonSerializable,
    _stringify_internal_python_value,
    promise_from_generator,
)


def promised_generator_middleware(next, root, info, **kwargs):
    next_val = next(root, info, **kwargs)

    if not is_thenable(next_val):
        return next_val

    def handler(resolved_next_val):
        if isgenerator(resolved_next_val):
            prom = promise_from_generator(resolved_next_val)
            return prom
        return resolved_next_val

    return next_val.then(handler)


def conditonal_serialization_middleware(next, root, info, **kwargs):
    next_val = next(root, info, **kwargs)

    is_internal_field = hasattr(info.return_type, "graphene_type") and issubclass(
        info.return_type.graphene_type, NonSerializable
    )
    if not (info.context.requires_serializable and is_internal_field):
        return next_val

    if is_thenable(next_val):
        return next_val.then(lambda val: _stringify_internal_python_value(val))
    else:
        return _stringify_internal_python_value(next_val)


def get_middleware():
    return [
        promised_generator_middleware,
        conditonal_serialization_middleware,
    ]
