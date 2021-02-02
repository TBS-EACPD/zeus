import logging
import asyncio
import traceback

from django.core.exceptions import SuspiciousOperation
from django.conf import settings

from graphene_django.views import GraphQLView
from graphql.execution.executors.asyncio import AsyncioExecutor


from .graphql_context import GraphQLContext


class GraphiQLViewBase(GraphQLView):
    """
        - must provide class attr schema
    """

    logger = logging.getLogger("django.request")
    schema = None

    def __init__(self, *args, executor=None, **kwargs):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        executor = AsyncioExecutor()
        super().__init__(*args, **kwargs, executor=executor)

    @classmethod
    def as_view(cls, *args, **kwargs):
        new_kwargs = {
            "schema": cls.schema,
            "graphiql": True,
            "middleware": [],
            **kwargs,
        }
        return super().as_view(*args, **new_kwargs)

    def dispatch(self, *args, **kwargs):
        if not settings.DEBUG:
            raise SuspiciousOperation("this is a dev-only feature")

        return super().dispatch(*args, **kwargs)

    def get_context(self, request):
        dataloaders = {}
        return GraphQLContext(dataloaders, requires_serializable=True)

    def execute_graphql_request(self, *args, **kwargs):
        result = super().execute_graphql_request(*args, **kwargs)
        self.loop.close()
        if result.errors:
            self._log_exceptions(result.errors)
        return result

    def _log_exceptions(self, errors):
        for error in errors:
            error_to_log = error
            if hasattr(error, "original_error"):
                error_to_log = error.original_error
            traceback_str = "".join(traceback.format_tb(error_to_log.__traceback__))
            self.logger.error(f"{error_to_log.__class__.__name__}: {error_to_log}")
            self.logger.error(traceback_str)
