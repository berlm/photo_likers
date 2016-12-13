from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render

from photo_likers.models import Tag
from photo_likers.utils.photo_request import PhotosRequest
from .page_searcher import PageSearcher
from .cache_manager import CacheManager


def index(request: HttpRequest):
    return HttpResponse("Hello, world!")


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
    photo_request = PhotosRequest(page_number=page_number, sort_field=sort_field, tags_conditions=tags_list, tags = Tag.objects.all())
    tag_refs = photo_request.get_tag_conditions_references()

    sorted_cache = CacheManager.get_sorted_photo_cache(photo_request)
    page = PageSearcher(sorted_cache).get_pagination_by_request(photo_request)

    return render(request, 'photos.html',
                  {'photos': page, 'page_number': page_number, 'sort_field': sort_field, 'tags_list': tags_list,
                   'tag_refs': tag_refs})
