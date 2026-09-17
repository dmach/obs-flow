from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

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


class AuthViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
            is_local_account=True
        )

    @override_settings(AUTH_LOCAL_ENABLED=True, AUTH_OIDC_ENABLED=False)
    def test_login_modal_local_only(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login_modal.html")
        self.assertTrue(response.context["auth_local_enabled"])
        self.assertFalse(response.context["auth_oidc_enabled"])
        # Since OIDC is disabled, local form should be shown directly
        self.assertContains(response, 'name="username"')
        self.assertNotContains(response, "Login with SSO")

    @override_settings(AUTH_LOCAL_ENABLED=False, AUTH_OIDC_ENABLED=True)
    def test_login_modal_oidc_only(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["auth_local_enabled"])
        self.assertTrue(response.context["auth_oidc_enabled"])
        self.assertContains(response, "Login with SSO")
        self.assertNotContains(response, 'name="username"')

    @override_settings(AUTH_LOCAL_ENABLED=True, AUTH_OIDC_ENABLED=True)
    def test_login_modal_both_enabled(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["auth_local_enabled"])
        self.assertTrue(response.context["auth_oidc_enabled"])
        self.assertContains(response, "Login with SSO")
        # Local form should be collapsed behind HTMX button
        self.assertContains(response, "Use local account")
        self.assertNotContains(response, 'name="username"')

    def test_local_login_form_partial(self):
        response = self.client.get(reverse("local_login_form"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/partials/local_login_form.html")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_successful_login_and_logout(self):
        # Login
        response = self.client.post(reverse("login"), {
            "username": "testuser",
            "password": "password123",
            "next": "/git-mappings/"
        })
        self.assertRedirects(response, "/git-mappings/")

        # Logout
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, "/")

    def test_htmx_logout_redirects_via_header(self):
        # Login first
        self.client.login(username="testuser", password="password123")
        # Logout via HTMX
        response = self.client.post(reverse("logout"), HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Redirect"], "/")

    def test_default_login_redirects_to_home(self):
        # Login without next parameter
        response = self.client.post(reverse("login"), {
            "username": "testuser",
            "password": "password123",
        })
        self.assertRedirects(response, "/")

    def test_login_links_contain_next_parameter(self):
        # Get home page
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        # Login links should contain ?next=/
        self.assertContains(response, 'href="/accounts/login/?next=/"')

    def test_local_login_with_external_user_does_not_crash(self):
        # Create external user (password is None)
        User.objects.create_user(
            username="extuser",
            is_local_account=False,
            oidc_sub="auth0|123456"
        )
        # Attempt local login with external user's username
        response = self.client.post(reverse("login"), {
            "username": "extuser",
            "password": "somepassword",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], None, "Please enter a correct username and password. Note that both fields may be case-sensitive.")
