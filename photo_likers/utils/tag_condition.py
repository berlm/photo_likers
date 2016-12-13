from photo_likers.models import Tag


class TagConditionsLink:
    """Сущность для отображения ссылок в шаблоне"""

    def __init__(self, ref_name: str, ref: str):
        self.ref_name = ref_name
        self.ref = ref


class TagCondition:
    """Условие на тег"""

    def __init__(self, tag: Tag, inclusive: bool):
        self.tag = tag
        self.inclusive = inclusive

    def __str__(self):
        return ("-" if not self.inclusive else "") + str(self.tag.id)

    def have_tag(self, tag: Tag) -> bool:
        return tag is not None and tag.id == self.tag.id

    def name(self) -> str:
        return "{sign} #{tag}".format(sign="include" if self.inclusive else "exclude"
                                      , tag=self.tag.name)

    def key(self) -> str:
        return str(self.tag.id * (-1 if not self.inclusive else 1))
