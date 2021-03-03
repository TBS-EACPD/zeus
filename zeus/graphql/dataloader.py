from inspect import isgeneratorfunction

from promise import Promise, is_thenable
from promise.dataloader import DataLoader

from .utils import genfunc_to_prom, promise_from_generator


class BaseDataloader(DataLoader):
    # shortcut for instance methods to turn generator instances into promises
    def batch_load_fn(self, keys):
        func = self.batch_load
        if isgeneratorfunction(func):
            func = genfunc_to_prom(func)

        result = func(keys)

        if not is_thenable(result):
            # batch_load_fn must always return a promise
            return Promise.resolve(result)

        return result


class SingletonDataLoader(BaseDataloader):
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


class AbstractModelByIdLoader(SingletonDataLoader):
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
