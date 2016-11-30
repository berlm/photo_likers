from datetime import datetime
from django.core.cache import cache
from django.core.paginator import Page, PageNotAnInteger, EmptyPage
from photo_likers.models import Tag, Photo
from photo_likers.photo_caches import PhotoCacheBase, PhotoLikeCache, PhotoDateCache
from .settings import PHOTOS_PER_PAGE


class DummyTag:
    """Специальный тег для обработки случая,
        когда в запросе присутствуют только исключающие теги.
       Прикреплен ко всем фото.
    """

    def __init__(self):
        self.photo_set = Photo.objects
        self.id = 999999999
        self.name = "All"


class CustomPaginator:
    """Класс подменяет стандартный пагинатор страниц,
        для экономии времени на переделывание шаблона страницы с фото и
    """

    def __init__(self, num_pages: int):
        self.num_pages = num_pages

    def validate_number(self, number: int):
        try:
            number = int(number)
            if 1 <= number <= self.num_pages:
                return number
        except:
            return 1


class CacheManager:
    """Класс менеджер для обновления и использования кэшей

       Основные функции для внешнего вызова:
          get_pagination_for_conditions: запрос пагинации фото по условиям на теги и виду сортировки
          load_photos_cache: Загрузка кэшей с фотками по тегам
    """
    CACHE_TYPES = {0: PhotoLikeCache(), 1: PhotoDateCache()}  # type: dict[int,PhotoCacheBase]
    SEARCH_CACHES_SECONDS_TIMEOUT = 600
    # с каким шагом запоминать отметки (указатели в упорядоченных списках) для ускорения поиска по кэшируемым запросам
    SEARCH_CACHES_MEMORY_PAGE_STEP = 50
    NUM_PAGES_KEY = 'num_pages'
    CHECKPOINTS_KEY = 'checkpoints'

    @staticmethod
    def get_pagination_for_conditions(signed_tags: list, page_number: int, sort_field: int) -> Page:
        if sort_field in CacheManager.CACHE_TYPES:
            return CacheManager.__get_from_cache(signed_tags, page_number, CacheManager.CACHE_TYPES[sort_field])
        else:
            raise ValueError("Wrong sort field chosen!")

    @staticmethod
    def __get_from_cache(signed_tags: list, page_number: int, photo_cache: PhotoCacheBase) -> Page:
        """Подгрузка незагруженных кэшей по тегам и запуск получения пагинации из кэша"""
        signed_tags = sorted(signed_tags, reverse=True)
        if len(signed_tags) == 0 or signed_tags[0] < 0:
            signed_tags.insert(0, DummyTag().id)

        # Загрузка недостающих кэшей по тегам (при режиме подгрузки кэша "по необходимости")
        for signed_tag_id in signed_tags:
            tag_id = abs(signed_tag_id)
            if photo_cache.get_tag_cache_key(tag_id) not in cache:
                tag = Tag.objects.get(id=tag_id) if DummyTag().id != tag_id else DummyTag()
                snapshot_date = datetime.now()
                tag_photos = tag.photo_set.filter(created_date__lte=snapshot_date)
                photo_cache.load_one_tag_cache(tag=tag, tag_photos=tag_photos, snapshot_date=snapshot_date)

        return CacheManager.search_page(photo_cache, page_number, signed_tags)

    @staticmethod
    def search_page(photo_cache: PhotoCacheBase, page_number: int, sorted_signed_tags: list) -> Page:
        """Поиск фото с заданной страницы по заданным условиям на теги
            для заданного типа кэша (по лайкам или по датам).

            Для оптимизации используется временный кэш предыдущих поисков при
            совпадении условий на теги и типа сортировки с расчетом на то,
            что запросы с одинаковыми тегами возникают часто (особенно если их делают роботы)

            Основной алгоритм поиска заключается в том, чтобы идти одновременно по заранее
            загруженным упорядоченным по хэшу 'лайк/дата'+id, спискам фото для тегов из условий
            перемещая указатели в списках так, чтобы не пропускать пересечения со значением
            в первом списке. Таким образом, поиск страницы (и числа страниц) с заданным номером
            при заданной сортировке делается за линейное время от длины всех списков.
            Причем, если поиск выполнялся ранее, то мы знаем общее кол-во страниц и также
            просматривать приходится фоток не более, чем при поиске 50-ти страниц
            (параметр SEARCH_CACHES_MEMORY_PAGE_STEP)
        """
        # 1. Инициализация указателей на позиции в массивах и др.
        num_pages = None  # type: int  общее число страниц при заданном фильтре
        cnt_found = 0  # число найденных фоток, подходящих под фильтр
        cnt = len(sorted_signed_tags)
        pointers = [0] * cnt
        search_cache_checkpoints = [pointers]  # checkpoint-ы найденных страниц для ускорения поиска
        search_not_cached = True
        search_cache_key = CacheManager.get_search_cache_key(sorted_signed_tags=sorted_signed_tags,
                                                             sort_field=photo_cache.sort_field)
        search_cache_data = cache.get(search_cache_key)
        # подгрузка данных о чекпоинтах (если есть)
        if search_cache_data is not None:
            num_pages = search_cache_data[CacheManager.NUM_PAGES_KEY]
            checkpoints = search_cache_data[CacheManager.CHECKPOINTS_KEY]
            checkpoint_index = min(max((page_number - 1) // CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP, 0),
                                   len(checkpoints) - 1)
            if checkpoint_index > 0:
                cnt_found = checkpoint_index * CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP * PHOTOS_PER_PAGE
                pointers = checkpoints[checkpoint_index]
            search_not_cached = False

        tag_signs = [tag_id > 0 for tag_id in sorted_signed_tags]
        tag_sorted_lists = [photo_cache.get_photo_hashes_for_tag(abs(tag_id)) for tag_id in
                            sorted_signed_tags]
        res_list_photo_ids = []  # результирующие фотки (id)
        while (cnt_found < page_number * PHOTOS_PER_PAGE or search_not_cached) \
                and (pointers[0] < len(tag_sorted_lists[0]) - 1):

            # получаем значение хэша в первом списке и
            # соответственно двигаем указатели в остальных
            main_value = tag_sorted_lists[0][pointers[0]]
            for pointer_index in range(1, cnt):
                i = pointers[pointer_index]
                while tag_sorted_lists[pointer_index][i] > main_value:
                    i += 1
                pointers[pointer_index] = i
                # если в соответствующем списке нет заданного фото и условие на тег
                # включающее или наоборот, то это фото не подходит под фильтр
                if (tag_sorted_lists[pointer_index][i] == main_value) != tag_signs[pointer_index]:
                    break
            else:
                # если по break не вышли, значит фото подходит под фильтр
                photo_id = photo_cache.get_photo_id_by_hash(main_value)
                if photo_id > 0:
                    if (page_number - 1) * PHOTOS_PER_PAGE <= cnt_found < page_number * PHOTOS_PER_PAGE:
                        res_list_photo_ids.append(photo_id)
                    cnt_found += 1
                    if search_not_cached:
                        if cnt_found % (PHOTOS_PER_PAGE * CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP) == 0:
                            pointers_copy = pointers.copy()
                            pointers_copy[0] += 1
                            search_cache_checkpoints.append(pointers_copy)

            # не забываем двигать указатель в первом списке
            pointers[0] += 1

        if search_not_cached:
            num_pages = CacheManager.save_search_cache(search_cache_key, search_cache_checkpoints, cnt_found)

        # список фото получаем и переупорядочиваем одним запросом, чтобы не делать 20 запросов к БД
        res_list = sorted(Photo.objects.filter(id__in=res_list_photo_ids).all(),
                          key=lambda photo: res_list_photo_ids.index(photo.id))

        return Page(object_list=res_list, number=page_number,
                    paginator=CustomPaginator(num_pages=num_pages))

    @staticmethod
    def save_search_cache(search_cache_key, search_cache_checkpoints, cnt_found):
        num_pages, rest = divmod(cnt_found, PHOTOS_PER_PAGE)
        if rest > 0: num_pages += 1
        cache.set(
            search_cache_key,
            {CacheManager.NUM_PAGES_KEY: num_pages, CacheManager.CHECKPOINTS_KEY: search_cache_checkpoints},
            CacheManager.SEARCH_CACHES_SECONDS_TIMEOUT)
        return num_pages

    @staticmethod
    def load_photos_cache():
        """Загрузка кэшей с фотками"""
        cache.clear()
        tags = list(Tag.objects.all())

        tags.append(DummyTag())
        for tag in tags:
            snapshot_date = datetime.now()
            tag_photos = tag.photo_set.filter(created_date__lte=snapshot_date)
            for cache_type_id, photo_cache in CacheManager.CACHE_TYPES.items():
                photo_cache.load_one_tag_cache(tag=tag, tag_photos=tag_photos, snapshot_date=snapshot_date)

    @staticmethod
    def get_search_cache_key(sorted_signed_tags: list, sort_field: int):
        return str(sort_field) + "#" + ";".join(str(x) for x in sorted_signed_tags)
