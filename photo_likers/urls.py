from django.conf.urls import url
from . import views
from django.contrib.auth.views import login

app_name = 'photo_likers'

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^photos/sort=(?P<sort_field>[0-1])&tags=(?P<tags_list>[0-9|;|-]*)&page=(?P<page_number>[0-9]+)$',
        views.photos_view, name='photos'),
    url(r'^login/$', login, name='login'),
]
