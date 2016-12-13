from datetime import datetime, timedelta
from django.test import TestCase
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from PhotoLikers.settings import LOGIN_URL
from photo_likers.utils.photo_request import PhotosRequest, SortType
from photo_likers.utils.tag_condition import TagCondition
from .loading_startup_cache import load_start_cache
from .photo_environment import PhotoEnvironment
from .settings import PHOTOS_PER_PAGE
from .user_environment import UserEnvironment
from .cache_manager import CacheManager
from photo_likers.utils.sorted_list_utils import find_place_in_reversed_list, sorted_list_merge


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

    def test_find_place(self):
        array = list(range(1000, 1, -2))
        self.assertRaises(Exception, lambda: find_place_in_reversed_list(0, array, 0))
        self.assertEqual(find_place_in_reversed_list(2, array, 0), 499)
        self.assertEqual(find_place_in_reversed_list(1000, array, 0), 0)
        self.assertEqual(find_place_in_reversed_list(999, array, 0), 1)
        self.assertEqual(find_place_in_reversed_list(900, array, 0), 50)
        self.assertEqual(find_place_in_reversed_list(899, array, 0), 51)
        self.assertEqual(find_place_in_reversed_list(900, array, 2), 50)

    def test_merger_simple(self):
        sorted_lists = [[12, 10, 8, 6, 4, 2, -1], [12, 8, 4, -1], [8, -1]]
        inclusion_indicators = [True, True, False]
        expected_values = [12, 4]
        expected_pointers = [(0, 0), (4, 2)]
        i = 0
        for value, pointers in sorted_list_merge(sorted_lists=sorted_lists, inclusion_indicators=inclusion_indicators):
            self.assertEqual(value, expected_values[i])
            self.assertTupleEqual(tuple(pointers[:2]), expected_pointers[i])
            i += 1
        self.assertEqual(i, len(expected_values))

    def test_photo_request_wrong_sort_type(self):
        self.assertRaises(Exception,
                          lambda x: PhotosRequest(page_number='1', sort_field='2', tags_conditions='', tags=[]))

    def test_photo_request_wrong_page_format(self):
        self.assertRaises(Exception,
                          lambda x: PhotosRequest(page_number='A', sort_field='0', tags_conditions='', tags=[]))
        self.assertRaises(Exception,
                          lambda x: PhotosRequest(page_number='', sort_field='0', tags_conditions='', tags=[]))

    def test_photo_request_wrong_tag_format(self):
        self.assertRaises(Exception,
                          lambda x: PhotosRequest(page_number='1', sort_field='0', tags_conditions='1;ass', tags=[]))

    def test_photo_request_no_tags(self):
        self.assertRaises(Exception,
                          lambda x: PhotosRequest(page_number='1', sort_field='0', tags_conditions='', tags=[]))

    def test_photo_request_tags_presented(self):
        tags = self.__photo_environment.setup_tags(cnt=3, name_function=lambda i: i)
        tags_condition_expr = "{0};-{1};".format(tags[0].id, tags[1].id)
        photo_request = PhotosRequest(page_number='1', sort_field='0', tags_conditions=tags_condition_expr, tags=tags)
        self.assertEqual(photo_request.page_number, 1)
        self.assertEqual(photo_request.sort_field, SortType.likes)
        self.assertEqual(len(photo_request.tags_conditions), 2)

        tag0_cond = TagCondition(tag=tags[0], inclusive=True)
        tag1_cond = TagCondition(tag=tags[1], inclusive=False)
        tag2_cond_inclusive = TagCondition(tag=tags[2], inclusive=True)
        tag2_cond_exclusive = TagCondition(tag=tags[2], inclusive=False)
        self.assertSetEqual({x.key() for x in photo_request.tags_conditions},
                            {tag0_cond.key(), tag1_cond.key()})

        self.assertEqual(tag0_cond.key(), '{0}'.format(tags[0].id))
        self.assertEqual(tag1_cond.key(), '-{0}'.format(tags[1].id))

        remove_condition_references = photo_request.get_refs_to_exclude_existing_tag_conditions()
        self.assertSetEqual({x.ref for x in remove_condition_references}, {tag0_cond.key(), tag1_cond.key()})

        references = photo_request.get_refs_to_add_all_tags_conditions()
        self.assertSetEqual({x.ref for x in references}, {tags_condition_expr + tag2_cond_inclusive.key(),
                                                          tags_condition_expr + tag2_cond_exclusive.key()})

        all_references = photo_request.get_tag_conditions_references()
        references.extend(remove_condition_references)
        self.assertSetEqual({x.ref for x in all_references}, {x.ref for x in references})

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

    def test_photos_repeat_query_1tag_in_1out(self):
        """Фото по двум тегам один включается другой исключается
          с повторением запроса для проверки кэширования"""
        self.setup_user()
        cnt_tags = 100
        cnt_photos = 800
        # CacheManager.SEARCH_CACHES_MEMORY_PAGE_STEP = 2  # выставляем, чтобы реально проверить кэширования
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
        page_number = 3
        response = self.client.get(
            path=reverse('photo_likers:photos', kwargs={'page_number': page_number, 'sort_field': 1,
                                                        'tags_list': "{0};-{1}".format(tags[0].id, tags[1].id)}))

        photos_list = response.context['photos']
        photos = [photo for photo in photos if tag_suit_photo(tags[0], photo) and not tag_suit_photo(tags[1], photo)]
        photos.reverse()
        self.assertListEqual(list(photos_list),
                             photos[(page_number - 1) * PHOTOS_PER_PAGE:page_number * PHOTOS_PER_PAGE])
