from .cache_manager import CacheManager
from photo_likers.settings import LOAD_CACHES_ON_START, LOAD_CACHES_ON_START_ASYNC
import threading


def load_start_cache():
    """Загрузка исходных кэшей"""
    if LOAD_CACHES_ON_START:
        load_cache_func = CacheManager.load_photos_cache
        if LOAD_CACHES_ON_START_ASYNC:
            t = threading.Thread(target=load_cache_func)
            t.start()
        else:
            load_cache_func()
