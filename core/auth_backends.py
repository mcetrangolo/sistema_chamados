from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CaseInsensitiveModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        login = username or kwargs.get(UserModel.USERNAME_FIELD)
        if login is None or password is None:
            return None

        try:
            user = UserModel._default_manager.get(
                **{f"{UserModel.USERNAME_FIELD}__iexact": login}
            )
        except UserModel.DoesNotExist:
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
