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


class SortedListSearcher:
    def __init__(self, page_number: int, tag_sorted_lists, tag_signs, search_cache_data):
        self.tag_signs = tag_signs
        self.tag_sorted_lists = tag_sorted_lists
        self.page_number = page_number
        self.cnt_lists = len(tag_signs)
        self.res_values = []  # результирующие значения в пересечении
        if search_cache_data is not None:
            self.__num_pages = search_cache_data[CacheManager.NUM_PAGES_KEY]
            checkpoints = search_cache_data[CacheManager.CHECKPOINTS_KEY]
            checkpoint_index = min(max((page_number - 1) // CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP, 0),
                                   len(checkpoints) - 1)
            self.cnt_found = checkpoint_index * CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP * PHOTOS_PER_PAGE
            self.__pointers = checkpoints[checkpoint_index]
        else:
            self.__num_pages = None  # type: int  общее число страниц при заданном фильтре
            self.cnt_found = 0  # число найденных фоток, подходящих под фильтр
            self.__pointers = [0] * self.cnt_lists

    def next(self):
        def seacrh_first_not_greater(value: int, arr_values, start_index: int) -> int:
            j = start_index
            for step in [2 ** (i - 1) for i in range(15, 0, -1)]:
                while j < len(arr_values) and arr_values[j] > value:
                    j += step
                if j > start_index and step > 1:
                    j -= step
                if arr_values[j] <= value:
                    break
            return j

        if not self.has_next():
            return None
        # получаем значение хэша в первом списке и
        # соответственно двигаем указатели в остальных
        main_value = self.tag_sorted_lists[0][self.__pointers[0]]
        smallest_inclusive_value = main_value
        for pointer_index in range(1, self.cnt_lists):
            i = seacrh_first_not_greater(main_value, self.tag_sorted_lists[pointer_index],
                                         self.__pointers[pointer_index])
            self.__pointers[pointer_index] = i
            # если в соответствующем списке нет заданного фото и условие на тег
            # включающее или наоборот, то это фото не подходит под фильтр
            if self.tag_signs[pointer_index] != (self.tag_sorted_lists[pointer_index][i] == main_value):
                if self.tag_signs[pointer_index]:
                    # для тегов, которые должны присутствовать сохраняем значение,
                    # чтобы сдвинуть первый указатель сразу до соответствующего места
                    smallest_inclusive_value = self.tag_sorted_lists[pointer_index][i]
                main_value = None
                break
        else:
            if (self.page_number - 1) * PHOTOS_PER_PAGE <= self.cnt_found < self.page_number * PHOTOS_PER_PAGE:
                self.res_values.append(main_value)
            self.cnt_found += 1

        # не забываем двигать указатель в первом списке
        self.__pointers[0] = seacrh_first_not_greater(smallest_inclusive_value, self.tag_sorted_lists[0],
                                                      self.__pointers[0] + 1)
        return main_value

    def has_next(self):
        return self.__pointers[0] < len(self.tag_sorted_lists[0]) - 1

    def get_found_pages_count(self):
        num_pages, rest = divmod(self.cnt_found, PHOTOS_PER_PAGE)
        if rest > 0:
            num_pages += 1
        return num_pages

    def get_pages_number(self):
        if self.__num_pages:
            return self.__num_pages
        else:
            return self.get_found_pages_count()

    def get_checkpoint(self):
        return self.__pointers.copy()


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
        search_cache_key = CacheManager.get_search_cache_key(sorted_signed_tags=sorted_signed_tags,
                                                             sort_field=photo_cache.sort_field)
        search_cache_data = cache.get(search_cache_key)
        tag_signs = [tag_id > 0 for tag_id in sorted_signed_tags]
        tag_sorted_lists = [photo_cache.get_photo_hashes_for_tag(abs(tag_id)) for tag_id in
                            sorted_signed_tags]
        searcher = SortedListSearcher(page_number=page_number, tag_sorted_lists=tag_sorted_lists, tag_signs=tag_signs,
                                      search_cache_data=search_cache_data)
        search_cache_checkpoints = [searcher.get_checkpoint()]
        search_not_cached = search_cache_data is None
        while (searcher.cnt_found < page_number * PHOTOS_PER_PAGE or search_not_cached) \
                and searcher.has_next():
            if searcher.next() is not None and search_not_cached \
                    and searcher.cnt_found % (PHOTOS_PER_PAGE * CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP) == 0:
                search_cache_checkpoints.append(searcher.get_checkpoint())

        res_list_photo_ids = [photo_cache.get_photo_id_by_hash(hash_value) for hash_value in searcher.res_values]
        if search_not_cached:
            CacheManager.save_search_cache(search_cache_key, search_cache_checkpoints,
                                           searcher.get_found_pages_count())

        # список фото получаем и переупорядочиваем одним запросом,
        # чтобы не делать 20 запросов к БД
        res_list = sorted(Photo.objects.filter(id__in=res_list_photo_ids).all(),
                          key=lambda photo: res_list_photo_ids.index(photo.id))

        return Page(object_list=res_list, number=page_number,
                    paginator=CustomPaginator(num_pages=searcher.get_pages_number()))

    @staticmethod
    def save_search_cache(search_cache_key, search_cache_checkpoints, num_pages: int):
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
