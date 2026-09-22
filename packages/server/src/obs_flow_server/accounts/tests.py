from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

from .helpers import generate_secure_token, get_authenticated_user
from .models import Group, Token, User


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


class TokenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tokenuser",
            password="password123",
            is_local_account=True
        )
        # Ensure admin user exists for fallback test
        User.objects.get_or_create(username="admin", defaults={"is_local_account": True})

    def test_token_generation_and_hashing(self):
        raw_token, last_eight, token_hash = generate_secure_token()
        self.assertTrue(raw_token.startswith("flow-"))
        self.assertEqual(len(raw_token), 69)
        self.assertEqual(last_eight, raw_token[-8:])
        self.assertEqual(len(token_hash), 64)

    def test_token_webui_flow(self):
        self.client.login(username="tokenuser", password="password123")

        # 1. View token list (should be empty)
        response = self.client.get(reverse("token_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You don't have any active personal access tokens yet.")

        # 2. Create a new token
        response = self.client.post(reverse("token_list"), {
            "action": "create",
            "description": "My Test Token",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Token Generated Successfully!")
        self.assertContains(response, "My Test Token")

        # Verify token was created in DB
        token = Token.objects.get(user=self.user)
        self.assertEqual(token.description, "My Test Token")
        self.assertEqual(len(token.last_eight), 8)

        # 3. View token list again (raw token should NOT be displayed anymore)
        response = self.client.get(reverse("token_list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Token Generated Successfully!")
        self.assertContains(response, f"flow-...{token.last_eight}")

        # 4. Revoke the token
        response = self.client.post(reverse("token_list"), {
            "action": "delete",
            "token_id": token.id,
        })
        self.assertRedirects(response, reverse("token_list"))
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_api_token_authentication(self):
        raw_token, last_eight, token_hash = generate_secure_token()
        token = Token.objects.create(
            user=self.user,
            last_eight=last_eight,
            token_hash=token_hash,
            description="API Test Token",
        )

        # Authenticate with valid token
        auth_header = f"Bearer {raw_token}"
        request = {"headers": {"authorization": auth_header}}
        authenticated_user = get_authenticated_user(request)
        self.assertEqual(authenticated_user, self.user)

        # Verify last_used_at was updated
        token.refresh_from_db()
        self.assertIsNotNone(token.last_used_at)

        # Authenticate with invalid token
        with self.assertRaises(ValueError):
            get_authenticated_user({"headers": {"authorization": "Bearer invalid-token"}})

        # Authenticate with invalid header format
        with self.assertRaises(ValueError):
            get_authenticated_user({"headers": {"authorization": "invalid-format"}})

        # Authenticate with no header (should raise ValueError)
        with self.assertRaises(ValueError):
            get_authenticated_user({"headers": {}})


class UserPreferencesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="prefuser",
            password="password123",
            is_local_account=True
        )

    def test_default_preferences(self):
        # Accessing properties should return defaults if no preferences object exists
        self.assertEqual(self.user.theme_preference, "auto")
        self.assertEqual(self.user.font_size_preference, 14)

    def test_preferences_creation_and_update(self):
        self.client.login(username="prefuser", password="password123")

        # GET preferences page (should create preferences object)
        response = self.client.get(reverse("preferences"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/preferences.html")

        from accounts.models import UserPreferences
        self.assertTrue(UserPreferences.objects.filter(user=self.user).exists())
        prefs = UserPreferences.objects.get(user=self.user)
        self.assertEqual(prefs.theme, "auto")
        self.assertEqual(prefs.font_size, 14)
        self.assertEqual(prefs.page_size, 100)

        # POST valid preferences update
        response = self.client.post(reverse("preferences"), {
            "theme": "dark",
            "font_size": 16,
            "page_size": 200,
        })
        self.assertRedirects(response, reverse("preferences"))

        prefs.refresh_from_db()
        self.assertEqual(prefs.theme, "dark")
        self.assertEqual(prefs.font_size, 16)
        self.assertEqual(prefs.page_size, 200)
        self.assertEqual(self.user.theme_preference, "dark")
        self.assertEqual(self.user.font_size_preference, 16)
        self.assertEqual(self.user.page_size, 200)

    def test_preferences_validation(self):
        self.client.login(username="prefuser", password="password123")

        # POST invalid font size (too small)
        response = self.client.post(reverse("preferences"), {
            "theme": "light",
            "font_size": 10,
            "page_size": 100,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "font_size", "Font size must be between 12 and 20.")

        # POST invalid font size (too large)
        response = self.client.post(reverse("preferences"), {
            "theme": "light",
            "font_size": 22,
            "page_size": 100,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "font_size", "Font size must be between 12 and 20.")

        # POST invalid page size (too small)
        response = self.client.post(reverse("preferences"), {
            "theme": "light",
            "font_size": 14,
            "page_size": 50,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "page_size", "Page size must be between 100 and 1000.")

        # POST invalid page size (too large)
        response = self.client.post(reverse("preferences"), {
            "theme": "light",
            "font_size": 14,
            "page_size": 2000,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "page_size", "Page size must be between 100 and 1000.")

