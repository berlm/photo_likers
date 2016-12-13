from django.core.paginator import Page
from photo_likers.cache_manager import CacheManager
from photo_likers.models import Photo
from photo_likers.photo_caches import SortedPhotoCacheBase
from photo_likers.settings import PHOTOS_PER_PAGE
from photo_likers.utils.custom_paginator import CustomPaginator
from photo_likers.utils.dummy_tag import DummyTag
from photo_likers.utils.photo_request import PhotosRequest
from photo_likers.utils.sorted_list_searcher import SortedListSearcher
from photo_likers.utils.tag_condition import TagCondition


class PageSearcher:
    def __init__(self, photo_cache: SortedPhotoCacheBase, searcher_class=SortedListSearcher):
        self.__photo_cache = photo_cache
        self.__searcher_class = searcher_class

    def get_pagination_by_request(self, photo_request: PhotosRequest) -> Page:
        ordered_conditions = self.__order_tag_conditions(photo_request)
        ordered_photo_lists = [x for x in self.__photo_cache.load_necessary_caches(tag_conditions=ordered_conditions)]
        return self.search_page_in_ordered_photo_lists(photo_request, ordered_conditions, ordered_photo_lists)

    def search_page_in_ordered_photo_lists(self, photo_request: PhotosRequest, ordered_conditions,
                                           ordered_photo_lists) -> Page:
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
        photo_cache = self.__photo_cache
        search_info = CacheManager.get_search_cache(photo_request)
        search_not_cached = search_info is None
        searcher = self.__searcher_class(sorted_lists=ordered_photo_lists,
                                         inclusion_indicators=[condition.inclusive for condition in ordered_conditions],
                                         page_step=CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP)

        photo_hashes, search_info = searcher.search_page(page_number=photo_request.page_number,
                                                         search_info=search_info,
                                                         compute_search_info=search_not_cached)

        if search_not_cached:
            CacheManager.save_search_cache(photo_request, search_info)

        # список фото получаем и переупорядочиваем одним запросом,
        # чтобы не делать 20 запросов к БД
        res_list_photo_ids = [photo_cache.get_photo_id_by_hash(hash_value) for hash_value in photo_hashes]
        res_list = sorted(Photo.objects.filter(id__in=res_list_photo_ids).all(),
                          key=lambda photo: res_list_photo_ids.index(photo.id))

        return Page(object_list=res_list, number=photo_request.page_number,
                    paginator=CustomPaginator(num_pages=search_info.num_pages))

    @staticmethod
    def __is_checkpoint(searcher):
        return searcher.cnt_found % (PHOTOS_PER_PAGE * CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP) == 0

    @staticmethod
    def __order_tag_conditions(photo_request):
        ordered_conditions = sorted(photo_request.tags_conditions, key=lambda x: x.key(), reverse=True)
        """ @:type list[TagCondition] """
        if len(ordered_conditions) == 0 or not ordered_conditions[0].inclusive:
            ordered_conditions.insert(0, TagCondition(tag=DummyTag(), inclusive=True))
        return ordered_conditions
