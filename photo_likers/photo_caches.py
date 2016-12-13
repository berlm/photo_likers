from datetime import datetime, date
from django.core.cache import cache
from photo_likers.models import Photo, Tag
from photo_likers.settings import LIKES_CACHE_TEMPLATE_KEY, DATE_CACHE_TEMPLATE_KEY
from photo_likers.utils.dummy_tag import DummyTag

PHOTO_KEY = 'photo'


class SortedPhotoCacheBase:
    """Базовый класс для работы с кэшем по фото для заданной сортировки

       todo: snapshot-ы можно задействовать при необходимости обновлении фото -
       чтобы обновлять соответственно и кэши
    """
    sort_field = None  # type: int

    def get_photo_hashes_for_tag(self, tag_id: int):
        return cache.get(self.get_tag_cache_key(tag_id))[PHOTO_KEY]

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

    def load_necessary_caches(self, tag_conditions):
        """Загрузка недостающих кэшей по тегам
            (при режиме подгрузки кэша "по необходимости")

        :param tag_conditions: list[TagCondition]
        :return: list[list[tuple]]
        """
        for condition in tag_conditions:
            key = self.get_tag_cache_key(condition.tag.id)
            if key not in cache:
                tag = Tag.objects.get(id=condition.tag.id) if DummyTag().id != condition.tag.id else DummyTag()
                snapshot_date = datetime.now()
                tag_photos = tag.photo_set.filter(created_date__lte=snapshot_date)
                yield self.load_one_tag_cache(tag=tag, tag_photos=tag_photos, snapshot_date=snapshot_date)
            else:
                yield cache.get(key)[PHOTO_KEY]

    def load_one_tag_cache(self, tag: Tag, tag_photos: list, snapshot_date: datetime):
        tag_photo_hashes = sorted([self.get_photo_hash(photo) for photo in tag_photos], reverse=True)
        # добавляем фиктивное значение в конец списка,
        # чтобы не проверять при поиске на каждой итерации
        tag_photo_hashes.append(self.get_min_hash())
        tag_res = {'snapshot': snapshot_date, PHOTO_KEY: tag_photo_hashes}
        cache.set(self.get_tag_cache_key(tag.id), tag_res)
        return tag_photo_hashes


class SortedPhotoLikeCache(SortedPhotoCacheBase):
    """Класс для работы с кэшем по фото для сортировки по лайкам"""
    sort_field = 0  # type: int

    @staticmethod
    def get_tag_cache_key(tag_id: int) -> str:
        return LIKES_CACHE_TEMPLATE_KEY.format(tag_id)

    @staticmethod
    def get_photo_hash(photo: Photo) -> tuple:
        return photo.likes_cnt, photo.id


class SortedPhotoDateCache(SortedPhotoCacheBase):
    """Класс для работы с кэшем по фото для сортировки по дате"""
    sort_field = 1  # type: int
    SMALL_DATE = date(year=1, month=1, day=1)

    @staticmethod
    def get_tag_cache_key(tag_id: int) -> str:
        return DATE_CACHE_TEMPLATE_KEY.format(tag_id)

    @staticmethod
    def get_photo_hash(photo: Photo) -> tuple:
        return (photo.created_date - SortedPhotoDateCache.SMALL_DATE).days, photo.id
