import inspect
import logging
import asyncio
import traceback


from graphene.test import Client
from graphql.execution.executors.asyncio import AsyncioExecutor

from .dataloader import AsyncDataLoader

from .graphql_context import GraphQLContext


class GraphQLExecutionErrorSet(Exception):
    def __init__(self, graphql_errors):
        self.graphql_errors = graphql_errors
        # err_str = json.dumps(graphql_errors, indent=4, sort_keys=True)
        super().__init__(graphql_errors)


class RaiseExceptionsMiddleware:
    """
        TODO: this makes every single resolver async, which is probably a performance problem later on when we have more fields. Right now most of our resolvers are async anyway. 

        To fix this, we have to manually create a MiddlewareManager that conditionally wraps async resolvers (by checking asyncio.iscoroutinefunction) with async, and leaves non-async resolvers alone
    """

    logger = logging.getLogger("django.request")

    def on_error(self, error, *args, **kwargs):
        traceback_str = "".join(traceback.format_tb(error.__traceback__))
        self.logger.error(f"{error.__class__.__name__}: {error}")
        self.logger.error(traceback_str)

        raise error

    async def resolve(self, next, root, info, **kwargs):
        ret = next(root, info, **kwargs).catch(self.on_error)
        if inspect.isawaitable(ret):
            return await ret
        return ret


class InternalQueryExecutorBase:
    """
        - must define class variable "schema"

        if you want to execute multiple graphQL queries against the same data-loaders
        you must re-use instances of this class
    """

    schema = None

    def __init__(self):
        self.client = Client(self.schema)
        self.dataloaders = {}

    def execute_query(
        self, query: str, root: any = None, context: dict = None, variables: dict = None
    ):
        if context is None:
            context = GraphQLContext(self.dataloaders, requires_serializable=False)

        middleware = [
            RaiseExceptionsMiddleware(),
        ]

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for dataloader_instance in self.dataloaders.values():
            if isinstance(dataloader_instance, AsyncDataLoader):
                dataloader_instance.reset_loop(loop)

        executor = AsyncioExecutor()

        resp = self.client.execute(
            query, root, context, variables, middleware=middleware, executor=executor,
        )
        loop.close()

        if "errors" in resp:
            err = GraphQLExecutionErrorSet(resp["errors"])
            raise err
        return resp["data"]
