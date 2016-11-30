import pandas as pd

from .models import Photo, Tag


class PhotoEnvironment:
    """Генерация данных по фото для тестирования

       setup_tags: генерация тегов
       setup_photos: генерация фото и связей с тегами
    """
    SAMPLE_PHOTOS_PATH = 'photo_likers\\data\\test-photo.csv'

    @staticmethod
    def setup_tags(cnt: int, name_function) -> list:
        """:return: list[Tag]"""
        res = []
        for i in range(cnt):
            tag = Tag(name=name_function(i))
            tag.save()
            res.append(tag)
        return res

    def setup_photos(self, cnt: int, likes_function, date_function, tags_function=None):
        """:return: list[Photo]"""

        def get_photo_from_dict(row: dict, i: int):
            return Photo(path=row['src'], created_date=date_function(i), likes_cnt=likes_function(i))

        def create_photo(row: dict, i: int):
            photo = get_photo_from_dict(row, i)
            photo.save()
            if tags_function is not None:
                photo.tags.add(*tags_function(photo))

            return photo

        df_photos = pd.read_csv(self.SAMPLE_PHOTOS_PATH, sep=';', parse_dates=True, infer_datetime_format=True)
        if len(df_photos) > cnt:
            df_photos = df_photos.iloc[:cnt, :]

        df_photos = df_photos.applymap(lambda x: str(x).strip('"'))

        res = []
        i = 0
        for id, row in df_photos.iterrows():
            res.append(create_photo(row, i))
            i += 1

        if cnt > len(res):
            for id, row in df_photos.sample(cnt - len(res), replace=True).iterrows():
                res.append(create_photo(row, i))
                i += 1

        return res
