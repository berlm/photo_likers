class CustomPaginator:
    """Класс подменяет стандартный пагинатор страниц,
        для экономии времени на переделывание шаблона страницы с фото и
    """

    def __init__(self, num_pages: int):
        self.num_pages = num_pages

    def validate_number(self, number: int):
        try:
            number = int(number)
            if 1 <= number <= self.num_pages:
                return number
        except:
            return 1