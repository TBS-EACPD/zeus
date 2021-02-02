import asyncio
from inspect import isawaitable

from aiodataloader import DataLoader as BaseAsyncDataLoader


class AsyncDataLoader(BaseAsyncDataLoader):
    async def batch_load_fn(self, keys):
        result = self.batch_load(keys)
        if isawaitable(result):
            return await result
        return result

    def reset_loop(self, loop):
        """
            instances each hold a ref to the event loop
            to allow re-using an instance (and more importantly, its cache) accross loops, we must change the loop ref
            In addition, every cached value is wrapped in a future, which also contains a ref to the loop.
            so we start with a new cache, and prime it with all the old results
        """
        self.loop = loop
        old_cache = self._cache
        self._cache = {}
        for k, v in old_cache.items():
            if asyncio.isfuture(v):
                v = v.result()
            self.prime(k, v)


class AsyncSingletonDataLoader(AsyncDataLoader):
    dataloader_instance_cache = None

    def __new__(cls, dataloader_instance_cache):
        if cls not in dataloader_instance_cache:
            dataloader_instance_cache[cls] = super().__new__(cls)
        loader = dataloader_instance_cache[cls]
        assert isinstance(loader, cls)
        return loader

    def __init__(self, dataloader_instance_cache):
        if self.dataloader_instance_cache != dataloader_instance_cache:
            self.dataloader_instance_cache = dataloader_instance_cache
            super().__init__()


class AbstractModelByIdLoader(AsyncSingletonDataLoader):
    model = None  # override this part

    @classmethod
    def batch_load(cls, ids):
        records = list(cls.model.objects.filter(id__in=ids))
        by_id = {record.id: record for record in records}
        return [by_id[id] for id in ids]


class PrimaryKeyDataLoaderFactory:
    """
        This ensures the same _class_ for a single model can only be created once. 
        This is because some consumers dynamically create dataloaders based on models not yet known
    """

    dataloader_classes_by_model = {}

    @staticmethod
    def _create_dataloader_cls_for_model(model_cls):
        return type(
            f"{model_cls.__name__}ByIDLoader",
            (AbstractModelByIdLoader,),
            dict(model=model_cls),
        )

    @classmethod
    def get_model_by_id_loader(cls, model_cls):
        if model_cls in cls.dataloader_classes_by_model:
            return cls.dataloader_classes_by_model[model_cls]
        else:
            loader = cls._create_dataloader_cls_for_model(model_cls)
            cls.dataloader_classes_by_model[model_cls] = loader
            return loader
