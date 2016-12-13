from enum import Enum
from photo_likers.models import Tag
from photo_likers.utils.tag_condition import TagCondition, TagConditionsLink


class SortType(Enum):
    likes = 0
    dates = 1


class PhotosRequest:
    def __init__(self, page_number: str, sort_field: str, tags_conditions: str, tags):
        self.page_number = int(page_number)
        self.sort_field = SortType(int(sort_field))
        self.__tags_dict = {tag.id: tag for tag in tags}
        self.tags_conditions = [TagCondition(tag=self.__tags_dict[abs(int(x))]
                                             , inclusive=int(x) > 0)
                                for x in tags_conditions.split(";")
                                if x != ""]

    def get_tag_conditions_references(self):
        """Генерация ссылок с параметрами для изменения условия на теги"""
        refs = self.get_refs_to_exclude_existing_tag_conditions()
        refs.extend(self.get_refs_to_add_all_tags_conditions())
        return refs

    def get_refs_to_add_all_tags_conditions(self):
        refs = []  # type: list[TagConditionsLink]
        presented_tags = {x.tag.id for x in self.tags_conditions}
        for tag in self.__tags_dict.values():
            if tag.id not in presented_tags:
                for inclusive in [True, False]:
                    refs.append(self.get_ref_with_new_tag_condition(TagCondition(tag, inclusive)))
        return refs

    def get_refs_to_exclude_existing_tag_conditions(self):
        refs = []  # type: list[TagConditionsLink]
        for tag_condition in self.tags_conditions:
            conditions = self.__exclude_tag(self.tags_conditions, tag_condition.tag)
            refs.append(TagConditionsLink("remove {0}".format(tag_condition.name())
                                          , self.__get_reference_by_conditions(conditions)))
        return refs

    def get_ref_with_new_tag_condition(self, new_condition) -> TagConditionsLink:
        conditions = list(self.__exclude_tag(self.tags_conditions, new_condition.tag)) + [new_condition]
        return TagConditionsLink(new_condition.name()
                                 , self.__get_reference_by_conditions(conditions))

    @staticmethod
    def __exclude_tag(tag_conditions, tag: Tag):
        return filter(lambda x: not x.have_tag(tag), tag_conditions)

    @staticmethod
    def __get_reference_by_conditions(tags_conditions):
        """Формирование строки для накладывания условия по набору условий на теги
        :param tags_conditions: iterable[TagCondition]
        :return: str
        """
        return ";".join(str(condition) for condition in tags_conditions)
