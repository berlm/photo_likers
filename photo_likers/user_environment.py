from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, User
from django.contrib.auth.models import Permission
from django.conf import settings


__author__ = 'berlm'


class UserEnvironment:

    def create_user(self, name="Ivan") -> User:
        user = User(username=name)
        user.save()
        return user
    #
    # def setup_security_admin(self) -> User:
    #     user = get_user_model().objects.create(username="SecAdmin", first_name="God", is_staff=True)
    #     self.security_group.user_set.add(user)
    #     return user
