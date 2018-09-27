from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth.models import Group

class OIDCMokeyAuthenticationBackend(OIDCAuthenticationBackend):

    def create_user(self, claims):
        email = claims.get('email')
        username = claims.get('uid')
        if not username:
            return None

        user = self.UserModel.objects.create_user(username, email)

        user.first_name = claims.get('first', '')
        user.last_name = claims.get('last', '')

        groups = claims.get('groups', '')
        user.groups.clear()
        for group_name in groups.split(';'):
            group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

        user.save()

        return user

    def update_user(self, user, claims):
        print(claims)
        user.first_name = claims.get('first', '')
        user.last_name = claims.get('last', '')
        user.email = claims.get('email')

        groups = claims.get('groups', '')
        user.groups.clear()
        for group_name in groups.split(';'):
            group, created = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

        user.save()

        return user

    def filter_users_by_claims(self, claims):
        uid = claims.get('uid')
        if not uid:
            return self.UserModel.objects.none()

        try:
            return self.UserModel.objects.filter(username=uid)
        except self.UserModel.DoesNotExist:
            return self.UserModel.objects.none()
