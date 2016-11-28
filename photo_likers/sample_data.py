import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PhotoLikers.settings")
django.setup()

from photo_likers.photo_environment import PhotoEnvironment
from photo_likers.models import Photo, Tag
from random import randint, sample
from datetime import datetime, timedelta

if __name__ == "__main__":
    env = PhotoEnvironment()
    Photo.objects.all().delete()
    Tag.objects.all().delete()
    env.SAMPLE_PHTOTOS_PATH = 'data\\test-photo.csv'
    tags = env.setup_tags(cnt=100, name_function=lambda i: i)


    # def tag_suit_photo(x, y): return x.id % 10 == y.id % 10

    def tags_function(photo): return sample(tags[(photo.id % 10) * 10: ((photo.id % 10) + 1) * 10], 5)

    env.setup_photos(100000,
                     likes_function=lambda i: randint(1, 1000),
                     date_function=lambda i: datetime.now() - timedelta(days=i),
                     tags_function=tags_function)
