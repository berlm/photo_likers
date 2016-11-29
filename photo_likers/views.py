from django.shortcuts import render
from django.http import HttpResponse, HttpRequest
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render
from .settings import PHOTOS_PER_PAGE
from photo_likers.models import Photo, Tag
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .cache_manager import CacheManager


def index(request: HttpRequest):
    return HttpResponse("Hello, world!")


class HttpSubRef:
    def __init__(self, ref_name: str, ref: str):
        self.ref_name = ref_name
        self.ref = ref


def ref_by_conditions(tags_conditions: list, check=lambda tag: True, new_tag: int = None):
    new_tag_cond = ";" + str(new_tag) if new_tag is not None else ""
    return ";".join(str(tag) for tag in tags_conditions if check(tag)) + new_tag_cond


def get_tags_refs(signed_tag_ids: list, tags: list):
    """Генерация ссылок с параметрами для изменения условия на теги
    :param signed_tag_ids: list[int]
    :param tags: list[Tag]
    :return: list[HttpSubRef]
    """
    tags_dict = {tag.id: tag for tag in tags}
    refs = [HttpSubRef("remove condition on #{0}".format(tags_dict[abs(tag_condition)].name),
                       ref_by_conditions(signed_tag_ids, lambda tag: tag != tag_condition)) for
            tag_condition
            in signed_tag_ids]
    """ :type list[HttpSubRef] """
    for tag in tags:
        refs.append(HttpSubRef("#" + tag.name, ref_by_conditions(signed_tag_ids, lambda x: abs(x) != tag.id, tag.id)))
        refs.append(
            HttpSubRef("exclude #" + tag.name, ref_by_conditions(signed_tag_ids, lambda x: abs(x) != tag.id, -tag.id)))
    return refs


@login_required
def photos_view(request: HttpRequest, page_number: str = "1", sort_field: str = "0",
                tags_list: str = "") -> HttpResponse:
    """Основная view

    :param request: HttpRequest
    :param page_number: номер страницы
    :param sort_field: 0-сортировка по лайкам, 1-по дате
    :param tags_list: список тегов через ";" со знаком - или без
    :return: HttpResponse
    """
    signed_tag_ids = list(map(lambda x: int(x), filter(lambda x: x != '', tags_list.split(";"))))

    page = CacheManager.get_all_sorted_photos(signed_tags=signed_tag_ids, page_number=int(page_number),
                                              sort_field=int(sort_field))

    tag_refs = get_tags_refs(signed_tag_ids, list(Tag.objects.all()))
    return render(request, 'photos.html',
                  {'photos': page, 'page_number': page_number, 'sort_field': sort_field, 'tags_list': tags_list,
                   'tag_refs': tag_refs})
