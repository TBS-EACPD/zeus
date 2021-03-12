import pytest
from promise import get_default_scheduler, set_default_scheduler
from promise.schedulers.asyncio import AsyncioScheduler


@pytest.fixture
def dataloader_test():
    """
        allows promises not to be executed immediately during test runs
    """
    # For some reason, dataloaders .load() method instantly call batch_load when testing, making it impossible to test batching and counting queries.
    # Changing the scheduler during dataloader tests seems to fix the issue without breaking trigerring any async exception
    default_scheduler = get_default_scheduler()
    set_default_scheduler(AsyncioScheduler())
    yield
    set_default_scheduler(default_scheduler)
