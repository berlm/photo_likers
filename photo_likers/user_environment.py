from django.contrib.auth.models import User

__author__ = 'berlm'


class UserEnvironment:
    """Создание пользователей для тестирования"""

    def create_user(self, name="Ivan") -> User:
        user = User(username=name)
        user.save()
        return user
