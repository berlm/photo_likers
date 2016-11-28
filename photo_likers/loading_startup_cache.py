from .cache_manager import CacheManager


def load_start_cache():
    CacheManager().load_photos_cache()
