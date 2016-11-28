from django.db.models import *
from django.conf import settings


class Tag(Model):
    name = CharField(max_length=50)

    class Meta:
        managed = True
        app_label = 'photo_likers'


class Photo(Model):
    path = CharField(max_length=200)
    likes_cnt = IntegerField(db_index=True)
    created_date = DateField(db_index=True)
    tags = ManyToManyField(Tag, verbose_name="Tags")


class PhotoLikes(Model):
    photo = ForeignKey(Photo)
    user = ForeignKey(settings.AUTH_USER_MODEL)
    like_date = DateField()