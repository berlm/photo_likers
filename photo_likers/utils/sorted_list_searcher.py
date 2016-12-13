from photo_likers.settings import PHOTOS_PER_PAGE
from photo_likers.utils.sorted_list_utils import sorted_list_merge


class SearchRequestInfo:
    def __init__(self, num_pages: int, checkpoints):
        self.checkpoints = checkpoints  # type: list[list[int]]
        self.num_pages = num_pages


class SortedListSearcher:
    def __init__(self, sorted_lists, inclusion_indicators,
                 page_step: int = 50):
        self.__page_step = page_step
        self.__inclusion_indicators = inclusion_indicators  # type: list[bool]
        self.__sorted_lists = sorted_lists  # type: list[list[tuple(int,int)]]

    def search_page(self, page_number: int, compute_search_info: bool = False, search_info: SearchRequestInfo = None):
        res_values = []  # результирующие значения в пересечении
        checkpoints = []
        if search_info is None or compute_search_info:
            cnt_found = 0  # число найденных значений, подходящих под фильтр
            start_pointers = [0] * len(self.__inclusion_indicators)
            checkpoints.append(start_pointers.copy())
        else:
            cnt_found, start_pointers = self.__start_from_info(search_info, page_number)

        for value, pointers in sorted_list_merge(sorted_lists=self.__sorted_lists,
                                                 inclusion_indicators=self.__inclusion_indicators,
                                                 start_indices=start_pointers.copy()):
            if self.__belong_to_page(photo_index=cnt_found, page_number=page_number):
                res_values.append(value)
            cnt_found += 1

            if compute_search_info:
                if self.__is_checkpoint(cnt_found):
                    checkpoints.append(pointers.copy())
            elif len(res_values) == PHOTOS_PER_PAGE:
                break
        else:
            if compute_search_info:
                search_info = SearchRequestInfo(num_pages=self.__get_pages_count(cnt_found),
                                                checkpoints=checkpoints)

        return res_values, search_info

    @staticmethod
    def __belong_to_page(photo_index, page_number):
        return (page_number - 1) * PHOTOS_PER_PAGE <= photo_index < page_number * PHOTOS_PER_PAGE

    def __is_checkpoint(self, cnt_found):
        return cnt_found % (PHOTOS_PER_PAGE * self.__page_step) == 0

    def __start_from_info(self, search_info: SearchRequestInfo, page_number: int):
        """Инициализация поиска из сохраненных результатов предыдущего поиска"""
        checkpoint_index = min(
            max((page_number - 1) // self.__page_step, 0),
            len(search_info.checkpoints) - 1)
        cnt_found = checkpoint_index * self.__page_step * PHOTOS_PER_PAGE
        start_pointers = search_info.checkpoints[checkpoint_index]
        return cnt_found, start_pointers

    @staticmethod
    def __get_pages_count(cnt_found):
        num_pages, rest = divmod(cnt_found, PHOTOS_PER_PAGE)
        if rest > 0:
            num_pages += 1
        return num_pages
