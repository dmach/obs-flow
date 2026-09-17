from django.test import TestCase

from .models import Group, User


class UserModelTests(TestCase):
    def test_user_creation_with_local_account(self):
        user = User.objects.create_user(
            username="TestUser",
            password="password123",
            is_local_account=True
        )
        self.assertTrue(user.is_local_account)
        self.assertIsNone(user.oidc_sub)
        self.assertEqual(user.username_lower, "testuser")
        self.assertTrue(user.check_password("password123"))
        self.assertIsNotNone(user.password)

    def test_user_creation_external_account(self):
        user = User.objects.create_user(
            username="ExtUser",
            is_local_account=False,
            oidc_sub="auth0|123456"
        )
        self.assertFalse(user.is_local_account)
        self.assertEqual(user.oidc_sub, "auth0|123456")
        self.assertEqual(user.username_lower, "extuser")
        self.assertFalse(user.has_usable_password())
        self.assertIsNone(user.password)

    def test_external_account_cannot_have_password(self):
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username="ExtUserWithPass",
                password="password123",
                is_local_account=False
            )

    def test_username_lower_is_automatic(self):
        user = User.objects.create_user(username="CamelCaseUser", is_local_account=False)
        self.assertEqual(user.username_lower, "camelcaseuser")

        user.username = "NEWNAME"
        user.save()

        user.refresh_from_db()
        self.assertEqual(user.username_lower, "newname")

class GroupModelTests(TestCase):
    def test_group_name_lower_is_automatic(self):
        group = Group.objects.create(name="AdminGroup")
        self.assertEqual(group.name_lower, "admingroup")

        group.name = "NEWGROUP"
        group.save()

        group.refresh_from_db()
        self.assertEqual(group.name_lower, "newgroup")
