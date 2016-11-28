from datetime import datetime, timedelta
from django.test import TestCase
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from PhotoLikers.settings import LOGIN_URL
from .loading_startup_cache import load_start_cache
from .photo_environment import PhotoEnvironment
from .settings import PHOTOS_PER_PAGE
from .user_environment import UserEnvironment
from .cache_manager import CacheManager


class MyTests(TestCase):
    def setUp(self):
        super().setUp()
        self.__user_environment = UserEnvironment()
        self.__photo_environment = PhotoEnvironment()
        load_start_cache()

    def setup_user(self):
        user = self.__user_environment.create_user()
        self.client.force_login(user)
        return user

    def test_index_view(self):
        """Стартовая страница"""
        response = self.client.get(reverse('photo_likers:index'))
        self.assertEqual(response.status_code, 200)

    def test_unauthorized_access(self):
        """Проверка запроса фоток неавторизованным пользователей"""
        response = self.client.get(
            path=reverse('photo_likers:photos', kwargs={'page_number': 1, 'sort_field': 0, 'tags_list': ''}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse(LOGIN_URL)))

    def test_photos_empty(self):
        """Проверка запроса фоток авторизованным пользователей"""
        self.setup_user()
        response = self.client.get(
            path=reverse('photo_likers:photos', kwargs={'page_number': 1, 'sort_field': 0, 'tags_list': ''}))
        self.assertEqual(response.status_code, 200)

    def test_photos_sort_by_likes(self):
        """Проверка количества фоток и сортировки по лайкам"""
        self.setup_user()
        cnt_photos = 10
        photos = self.__photo_environment.setup_photos(cnt=cnt_photos, likes_function=lambda i: i,
                                                       date_function=lambda i: datetime.now() + timedelta(
                                                           days=i - cnt_photos))
        CacheManager().load_photos_cache()

        response = self.client.get(
            path=reverse('photo_likers:photos', kwargs={'page_number': 1, 'sort_field': 0, 'tags_list': ''}))
        self.assertEqual(response.status_code, 200)

        photos_list = response.context['photos']
        photos.reverse()
        self.assertListEqual(list(photos_list), photos)

    def test_photos_sort_by_date(self):
        """Проверка количества фоток и сортировки по дате"""
        self.setup_user()
        cnt_photos = 10
        photos = self.__photo_environment.setup_photos(cnt=cnt_photos, likes_function=lambda i: i,
                                                       date_function=lambda i: datetime.now() + timedelta(
                                                           days=i - cnt_photos))
        CacheManager().load_photos_cache()

        response = self.client.get(
            path=reverse('photo_likers:photos', kwargs={'page_number': 1, 'sort_field': 1, 'tags_list': ''}))
        self.assertEqual(response.status_code, 200)

        photos_list = response.context['photos']
        photos.reverse()
        self.assertListEqual(list(photos_list), photos)

    def test_photos_wrong_sort_type(self):
        """Проверка что нет reverse при неправильном типе сортировки"""
        with self.assertRaises(NoReverseMatch):
            reverse('photo_likers:photos', kwargs={'page_number': 1, 'sort_field': 3, 'tags_list': ''})

    def test_photos_second_page(self):
        """Проверка количества фоток на второй странице и сортировки по лайкам"""
        self.setup_user()
        cnt_photos = 50
        photos = self.__photo_environment.setup_photos(cnt=cnt_photos, likes_function=lambda i: i,
                                                       date_function=lambda i: datetime.now() + timedelta(
                                                           days=i - cnt_photos))
        CacheManager().load_photos_cache()

        response = self.client.get(
            path=reverse('photo_likers:photos', kwargs={'page_number': 2, 'sort_field': 0, 'tags_list': ''}))
        self.assertEqual(response.status_code, 200)

        photos_list = response.context['photos']
        photos.reverse()
        self.assertListEqual(list(photos_list), photos[PHOTOS_PER_PAGE:2 * PHOTOS_PER_PAGE])

    def test_photos_by_tag(self):
        """Фото по одному тегу"""
        self.setup_user()
        cnt_tags = 100
        cnt_photos = 10
        tags = self.__photo_environment.setup_tags(cnt=cnt_tags, name_function=lambda i: i)

        def tag_suit_photo(x, y): return x.id % 10 == y.id % 10

        def tags_function(photo): return [tag for tag in tags if tag_suit_photo(tag, photo)]

        photos = self.__photo_environment.setup_photos(cnt=cnt_photos, likes_function=lambda i: i,
                                                       date_function=lambda i: datetime.now() + timedelta(
                                                           days=i - cnt_photos),
                                                       tags_function=tags_function)
        CacheManager().load_photos_cache()

        response = self.client.get(
            path=reverse('photo_likers:photos', kwargs={'page_number': 1, 'sort_field': 1, 'tags_list': tags[0].id}))
        self.assertEqual(response.status_code, 200)

        photos_list = response.context['photos']
        photos.reverse()
        self.assertListEqual(list(photos_list), [photo for photo in photos if tag_suit_photo(tags[0], photo)])

    def test_photos_exclude_tag(self):
        """Фото по исключению тега"""
        self.setup_user()
        cnt_tags = 100
        cnt_photos = 10
        tags = self.__photo_environment.setup_tags(cnt=cnt_tags, name_function=lambda i: i)

        def tag_suit_photo(x, y): return x.id % 10 == y.id % 10

        def tags_function(photo): return [tag for tag in tags if tag_suit_photo(tag, photo)]

        photos = self.__photo_environment.setup_photos(cnt=cnt_photos, likes_function=lambda i: i,
                                                       date_function=lambda i: datetime.now() + timedelta(
                                                           days=i - cnt_photos),
                                                       tags_function=tags_function)
        CacheManager().load_photos_cache()

        response = self.client.get(
            path=reverse('photo_likers:photos', kwargs={'page_number': 1, 'sort_field': 1, 'tags_list': -tags[0].id}))
        self.assertEqual(response.status_code, 200)

        photos_list = response.context['photos']
        photos.reverse()
        self.assertListEqual(list(photos_list), [photo for photo in photos if not tag_suit_photo(tags[0], photo)])

    def test_photos_by_2tags(self):
        """Фото по двум тегам"""
        self.setup_user()
        cnt_tags = 100
        cnt_photos = 10
        tags = self.__photo_environment.setup_tags(cnt=cnt_tags, name_function=lambda i: i)

        def tag_suit_photo(x, y): return x.id % 10 == y.id % 10

        def tags_function(photo): return [tag for tag in tags if tag_suit_photo(tag, photo)]

        photos = self.__photo_environment.setup_photos(cnt=cnt_photos, likes_function=lambda i: i,
                                                       date_function=lambda i: datetime.now() + timedelta(
                                                           days=i - cnt_photos),
                                                       tags_function=tags_function)
        CacheManager().load_photos_cache()

        response = self.client.get(
            path=reverse('photo_likers:photos', kwargs={'page_number': 1, 'sort_field': 1,
                                                        'tags_list': "{0};{1}".format(tags[0].id, tags[1].id)}))
        self.assertEqual(response.status_code, 200)

        photos_list = response.context['photos']
        photos.reverse()
        self.assertListEqual(list(photos_list), [photo for photo in photos if
                                                 tag_suit_photo(tags[0], photo) and tag_suit_photo(tags[1], photo)])

    def test_photos_1tag_in_1out(self):
        """Фото по двум тегам один включается другой исключается"""
        self.setup_user()
        cnt_tags = 100
        cnt_photos = 10
        tags = self.__photo_environment.setup_tags(cnt=cnt_tags, name_function=lambda i: i)

        def tag_suit_photo(x, y): return x.id % 10 == y.id % 10

        def tags_function(photo): return [tag for tag in tags if tag_suit_photo(tag, photo)]

        photos = self.__photo_environment.setup_photos(cnt=cnt_photos, likes_function=lambda i: i,
                                                       date_function=lambda i: datetime.now() + timedelta(
                                                           days=i - cnt_photos),
                                                       tags_function=tags_function)
        CacheManager().load_photos_cache()

        response = self.client.get(
            path=reverse('photo_likers:photos', kwargs={'page_number': 1, 'sort_field': 1,
                                                        'tags_list': "{0};-{1}".format(tags[0].id, tags[1].id)}))
        self.assertEqual(response.status_code, 200)

        photos_list = response.context['photos']
        photos.reverse()
        self.assertListEqual(list(photos_list), [photo for photo in photos if
                                                 tag_suit_photo(tags[0], photo) and not tag_suit_photo(tags[1], photo)])
