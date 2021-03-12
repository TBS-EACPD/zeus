import functools
import inspect

from django.db.models import Model

import graphene

from promise import is_thenable


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
    def wrapper(*args, **kwargs):
        ret = func(*args, **kwargs)

        info = args[1]
        if len(args) == 3:
            # if we're dealing with a class or instance method, info will be third
            info = args[2]

        if info.context.requires_serializable:
            if is_thenable(ret):
                return ret.then(lambda val: _stringify_internal_python_value(val))

            return _stringify_internal_python_value(ret)

        return ret

    return wrapper


class HasNonSerializableRecordMixin(graphene.ObjectType):
    record = graphene.Field(NonSerializable)

    def resolve_record(self, _info):
        return self


def genfunc_to_prom(func):
    """
        turns a function returning a generator into a function returning a promise
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        generator = func(*args, **kwargs)
        if not inspect.isgenerator(generator):
            return generator

        return promise_from_generator(generator)

    return wrapper


def promise_from_generator(generator):
    """
        assumes the generator is not yet started
    """
    try:
        first_val = next(generator)
    except StopIteration as e:
        next_val = e.value
        return next_val

    return _ongoing_gen_to_prom(generator, first_val)


def _ongoing_gen_to_prom(generator, current_val=None):
    """
        recursive helper
    """
    if inspect.isgenerator(current_val):
        current_val = promise_from_generator(current_val)
    if not is_thenable(current_val):
        # this must be the final return
        return current_val

    def resolve_next(resolved_current):
        try:
            next_val = generator.send(resolved_current)
        except StopIteration as e:
            next_val = e.value
            return next_val

        return _ongoing_gen_to_prom(generator, next_val)

    return current_val.then(resolve_next)
