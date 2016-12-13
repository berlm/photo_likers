from photo_likers.models import Photo


class DummyTag:
    """Специальный тег для обработки случая,
        когда в запросе присутствуют только исключающие теги.
       Прикреплен ко всем фото.
    """

    def __init__(self):
        self.photo_set = Photo.objects
        self.id = 999999999
        self.name = "All"