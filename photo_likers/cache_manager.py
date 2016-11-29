from datetime import datetime, date
from django.core.cache import cache
from django.core.paginator import Page, PageNotAnInteger, EmptyPage
from photo_likers.models import Tag, Photo
from .settings import LIKES_CACHE_TEMPLATE_KEY, DATE_CACHE_TEMPLATE_KEY, PHOTOS_PER_PAGE
from math import floor

PHOTO_KEY = 'photo'


class DummyTag:
    def __init__(self):
        self.photo_set = Photo.objects
        self.id = 999999999
        self.name = "All"


class PhotoCacheBase:
    sort_field = None  # type: int

    @staticmethod
    def get_tag_cache_key(tag_id: int) -> str:
        raise NotImplementedError("Not implemented!")

    @staticmethod
    def get_photo_id_by_hash(hash_value: tuple) -> int:
        return hash_value[1]

    @staticmethod
    def get_photo_hash(photo: Photo) -> tuple:
        raise NotImplementedError("Not implemented!")

    @staticmethod
    def get_min_hash() -> tuple:
        return (-1, -1)

    def load_one_tag_cache(self, tag: Tag, tag_photos: list, snapshot_date: datetime):
        tag_photo_hashes = sorted([self.get_photo_hash(photo) for photo in tag_photos], reverse=True)
        tag_photo_hashes.append(self.get_min_hash())
        tag_res = {'snapshot': snapshot_date, PHOTO_KEY: tag_photo_hashes}
        cache.set(self.get_tag_cache_key(tag.id), tag_res)


class PhotoLikeCache(PhotoCacheBase):
    sort_field = 0  # type: int

    @staticmethod
    def get_tag_cache_key(tag_id: int) -> str:
        return LIKES_CACHE_TEMPLATE_KEY.format(tag_id)

    @staticmethod
    def get_photo_hash(photo: Photo) -> tuple:
        return photo.likes_cnt, photo.id


class PhotoDateCache(PhotoCacheBase):
    sort_field = 1  # type: int
    SMALL_DATE = date(year=1, month=1, day=1)

    @staticmethod
    def get_tag_cache_key(tag_id: int) -> str:
        return DATE_CACHE_TEMPLATE_KEY.format(tag_id)

    @staticmethod
    def get_photo_hash(photo: Photo) -> tuple:
        return (photo.created_date - PhotoDateCache.SMALL_DATE).days, photo.id


class CustomPaginator:
    def __init__(self, num_pages: int):
        self.num_pages = num_pages

    def validate_number(self, number: int):
        try:
            number = int(number)
        except (TypeError, ValueError):
            raise PageNotAnInteger('That page number is not an integer')
        if number < 1:
            raise EmptyPage('That page number is less than 1')
        if number > self.num_pages:
            if number == 1 and True:
                pass
            else:
                raise EmptyPage('That page contains no results')
        return number


class CacheManager:
    CACHE_TYPES = {0: PhotoLikeCache(), 1: PhotoDateCache()}  # type: dict[int,PhotoCacheBase]
    SEARCH_CACHES_SECONDS_TIMEOUT = 600
    # с каким шагом запоминать отметки (указатели в упорядоченных списках) для ускорения поиска по кэшируемым запросам
    SEARCH_CACHES_MEMORY_PAGE_STEP = 50
    NUM_PAGES_KEY = 'num_pages'
    CHECKPOINTS_KEY = 'checkpoints'

    @staticmethod
    def get_search_cache_key(sorted_signed_tags: list, sort_field: int):
        return str(sort_field) + "#" + ";".join(str(x) for x in sorted_signed_tags)

    @staticmethod
    def get_all_sorted_photos(signed_tags: list, page_number: int, sort_field: int) -> Page:
        if sort_field in CacheManager.CACHE_TYPES:
            return CacheManager.get_from_cache(signed_tags, page_number, CacheManager.CACHE_TYPES[sort_field])
        else:
            raise ValueError("Wrong sort field chosen!")

    @staticmethod
    def get_from_cache(signed_tags: list, page_number: int, photo_cache: PhotoCacheBase) -> Page:
        signed_tags = sorted(signed_tags, reverse=True)
        if len(signed_tags) == 0 or signed_tags[0] < 0:
            signed_tags.insert(0, DummyTag().id)

        for signed_tag_id in signed_tags:
            tag_id = abs(signed_tag_id)
            if photo_cache.get_tag_cache_key(tag_id) not in cache:
                tag = Tag.objects.get(id=tag_id) if DummyTag().id != tag_id else DummyTag()
                snapshot_date = datetime.now()
                tag_photos = tag.photo_set.filter(created_date__lte=snapshot_date)
                photo_cache.load_one_tag_cache(tag=tag, tag_photos=tag_photos, snapshot_date=snapshot_date)

        return CacheManager.search_page(photo_cache, page_number, signed_tags)

    @staticmethod
    def search_page(photo_cache: PhotoCacheBase, page_number, sorted_signed_tags) -> Page:
        search_cache_checkpoints = []
        num_pages = None  # type: int
        cnt_found = 0  # число найденных фоток, подходящих под фильтр
        cnt = len(sorted_signed_tags)
        pointers = [0] * cnt
        search_not_cached = True
        search_cache_key = CacheManager.get_search_cache_key(sorted_signed_tags=sorted_signed_tags,
                                                             sort_field=photo_cache.sort_field)
        search_cache_data = cache.get(search_cache_key)
        if search_cache_data is not None:
            num_pages = search_cache_data[CacheManager.NUM_PAGES_KEY]
            checkpoints = search_cache_data[CacheManager.CHECKPOINTS_KEY]
            checkpoint_index = min(max((page_number - 1) // CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP, 0),
                                   len(checkpoints) - 1)
            if checkpoint_index > 0:
                cnt_found = checkpoint_index * CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP
                pointers = checkpoints[checkpoint_index]
            search_not_cached = False

        tag_signs = [tag_id > 0 for tag_id in sorted_signed_tags]
        tag_sorted_lists = [cache.get(photo_cache.get_tag_cache_key(abs(tag_id)))[PHOTO_KEY] for tag_id in
                            sorted_signed_tags]
        res_list_photo_ids = []  # результирующие фотки (id)
        start_count = (page_number - 1) * PHOTOS_PER_PAGE
        end_count = page_number * PHOTOS_PER_PAGE
        while (cnt_found < page_number * PHOTOS_PER_PAGE or search_not_cached) \
                and (pointers[0] < len(tag_sorted_lists[0]) - 1):

            if search_not_cached:
                if cnt_found % (page_number * CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP) == 0:
                    search_cache_checkpoints.append(pointers.copy())

            main_value = tag_sorted_lists[0][pointers[0]]
            for pointer_index in range(1, cnt):
                i = pointers[pointer_index]
                while tag_sorted_lists[pointer_index][i] > main_value:
                    i += 1
                pointers[pointer_index] = i
                if (tag_sorted_lists[pointer_index][i] == main_value) != tag_signs[pointer_index]:
                    break
            else:
                photo_id = photo_cache.get_photo_id_by_hash(main_value)
                if photo_id > 0:
                    if start_count <= cnt_found < end_count:
                        res_list_photo_ids.append(photo_id)
                    cnt_found += 1
            pointers[0] += 1

        if search_not_cached:
            num_pages, rest = divmod(cnt_found, PHOTOS_PER_PAGE)
            if rest > 0: num_pages += 1
            cache.set(
                search_cache_key,
                {CacheManager.NUM_PAGES_KEY: num_pages, CacheManager.CHECKPOINTS_KEY: search_cache_checkpoints},
                CacheManager.SEARCH_CACHES_SECONDS_TIMEOUT)

        res_list = sorted(Photo.objects.filter(id__in=res_list_photo_ids).all(),
                          key=lambda photo: res_list_photo_ids.index(photo.id))
        return Page(object_list=res_list, number=page_number,
                    paginator=CustomPaginator(num_pages=num_pages))

    @staticmethod
    def load_photos_cache():
        cache.clear()
        tags = list(Tag.objects.all())

        tags.append(DummyTag())
        for tag in tags:
            snapshot_date = datetime.now()
            tag_photos = tag.photo_set.filter(created_date__lte=snapshot_date)
            for cache_type_id, photo_cache in CacheManager.CACHE_TYPES.items():
                photo_cache.load_one_tag_cache(tag=tag, tag_photos=tag_photos, snapshot_date=snapshot_date)
