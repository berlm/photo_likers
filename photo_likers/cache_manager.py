from django.core.cache import cache
from photo_likers.models import Tag, Photo
from datetime import datetime, date
from .settings import LIKES_CACHE_TEMPLATE_KEY, DATE_CACHE_TEMPLATE_KEY, PHOTOS_PER_PAGE

PHOTO_KEY = 'photo'


class DummyTag:
    def __init__(self):
        self.photo_set = Photo.objects
        self.id = 999999999
        self.name = "All"


class CacheManager:
    @staticmethod
    def get_all_sorted_photos(signed_tags: list, page: int, sort_field: int):
        if sort_field == 0:
            return CacheManager.get_from_cache(signed_tags, page, False, CacheManager.get_like_cache_key)
        elif sort_field == 1:
            return CacheManager.get_from_cache(signed_tags, page, False, CacheManager.get_date_cache_key)
        else:
            raise ValueError("Wrong sort field chosen!")

    @staticmethod
    def get_from_cache(signed_tags: list, page: int, get_slice: bool, cache_key_function):
        signed_tags = sorted(signed_tags, reverse=True)
        if len(signed_tags) == 0 or signed_tags[0] < 0:
            signed_tags.insert(0, DummyTag().id)

        cnt = len(signed_tags)
        un_cached_tags = [tag_id for tag_id in signed_tags if cache_key_function(abs(tag_id)) not in cache]
        if un_cached_tags:
            return None

        tag_sorted_lists = [cache.get(cache_key_function(abs(tag_id)))[PHOTO_KEY] for tag_id in signed_tags]
        tag_signs = [tag_id > 0 for tag_id in signed_tags]

        pointers = [0 for tag in signed_tags]
        start_count = (page - 1) * PHOTOS_PER_PAGE
        end_count = page * PHOTOS_PER_PAGE
        cnt_found = 0  # число найденных фоток, подходящих под фильтр
        res_list = []  # результирующие фотки
        while (cnt_found < page * PHOTOS_PER_PAGE or not get_slice) and (pointers[0] < len(tag_sorted_lists[0]) - 1):
            main_value = tag_sorted_lists[0][pointers[0]]

            for pointer_index in range(1, cnt):
                i = pointers[pointer_index]
                while tag_sorted_lists[pointer_index][i] > main_value:
                    i += 1
                pointers[pointer_index] = i
                if (tag_sorted_lists[pointer_index][i] == main_value) != tag_signs[pointer_index]:
                    break
            else:
                photo_id = CacheManager.get_photo_id_by_hash(main_value)
                if photo_id > 0:
                    if (start_count <= cnt_found < end_count) or not get_slice:
                        if start_count <= cnt_found < end_count:
                            res_list.append(Photo.objects.get(id=photo_id))
                        else:
                            res_list.append(photo_id)
                    cnt_found += 1
            pointers[0] += 1

        return res_list

    def load_photos_cache(self):
        tags = list(Tag.objects.all())
        small_date = date(year=1900, month=1, day=1)
        tags.append(DummyTag())
        for tag in tags:
            snapshot_date = datetime.now()
            tag_photos = tag.photo_set.filter(created_date__lte=snapshot_date)
            tag_photo_hashs = sorted([(photo.likes_cnt, photo.id) for photo in tag_photos], reverse=True)
            tag_photo_hashs.append((-1, -1))
            tag_res = {'snapshot': snapshot_date, PHOTO_KEY: tag_photo_hashs}
            cache.set(self.get_like_cache_key(tag.id), tag_res)

            tag_photo_hashs = sorted([((photo.created_date - small_date).days, photo.id) for photo in tag_photos],
                                     reverse=True)
            tag_photo_hashs.append((-1, -1))
            tag_res = {'snapshot': snapshot_date, PHOTO_KEY: tag_photo_hashs}
            cache.set(self.get_date_cache_key(tag.id), tag_res)

    @staticmethod
    def get_photo_id_by_hash(hash_value):
        return hash_value[1]

    @staticmethod
    def get_like_cache_key(tag_id: int):
        return LIKES_CACHE_TEMPLATE_KEY.format(tag_id)

    @staticmethod
    def get_date_cache_key(tag_id: int):
        return DATE_CACHE_TEMPLATE_KEY.format(tag_id)
