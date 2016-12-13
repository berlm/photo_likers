from datetime import datetime
from django.core.cache import cache
from photo_likers.models import Tag
from photo_likers.photo_caches import SortedPhotoCacheBase, SortedPhotoLikeCache, SortedPhotoDateCache
from photo_likers.utils.dummy_tag import DummyTag
from photo_likers.utils.photo_request import SortType, PhotosRequest
from photo_likers.utils.sorted_list_searcher import SearchRequestInfo


class CacheManager:
    """Класс менеджер для изменения и получения кэшей"""
    CACHE_TYPES = {SortType.likes: SortedPhotoLikeCache(),
                   SortType.dates: SortedPhotoDateCache()}  # type: dict[SortType,SortedPhotoCacheBase]
    SEARCH_CACHES_SECONDS_TIMEOUT = 600
    # с каким шагом запоминать отметки (указатели в упорядоченных списках)
    # для ускорения поиска по кэшируемым запросам
    SEARCH_CACHES_MEMORY_PAGE_STEP = 50
    NUM_PAGES_KEY = 'num_pages'
    CHECKPOINTS_KEY = 'checkpoints'

    @staticmethod
    def get_sorted_photo_cache(photo_request: PhotosRequest):
        return CacheManager.CACHE_TYPES[photo_request.sort_field]

    @staticmethod
    def load_photos_cache():
        """Загрузка кэшей с фотками по всем тегам и видам сортировки"""
        cache.clear()
        tags = list(Tag.objects.all())
        tags.append(DummyTag())
        for tag in tags:
            snapshot_date = datetime.now()
            tag_photos = tag.photo_set.filter(created_date__lte=snapshot_date)
            for cache_type_id, photo_cache in CacheManager.CACHE_TYPES.items():
                photo_cache.load_one_tag_cache(tag=tag, tag_photos=tag_photos, snapshot_date=snapshot_date)

    @staticmethod
    def get_search_cache(photo_request: PhotosRequest) -> SearchRequestInfo:
        return cache.get(CacheManager.__get_search_cache_key(photo_request))

    @staticmethod
    def save_search_cache(photo_request: PhotosRequest, search_info: SearchRequestInfo):
        cache.set(
            CacheManager.__get_search_cache_key(photo_request),
            search_info,
            CacheManager.SEARCH_CACHES_SECONDS_TIMEOUT)

    @staticmethod
    def __get_search_cache_key(photo_request: PhotosRequest):
        return str(photo_request.sort_field.value) + "#" + ";".join(
            str(x.tag.id) for x in photo_request.tags_conditions)
