from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from bookmarks.models import Bookmark


class BookmarkWebTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="darix",
            password="password123",
            is_local_account=True,
            full_name="Marcus Rueckert",
            email="mrueckert@suse.com",
            is_active=True,
        )
        self.client = Client()
        self.client.login(username="darix", password="password123")

    def test_bookmark_list(self):
        Bookmark.objects.create(user=self.user, name="A Bookmark", url="/foo")
        Bookmark.objects.create(user=self.user, name="B Bookmark", url="/bar")

        response = self.client.get(reverse("bookmark_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A Bookmark")
        self.assertContains(response, "B Bookmark")
        self.assertContains(response, "/foo")
        self.assertContains(response, "/bar")

    def test_bookmark_create_get(self):
        response = self.client.get(reverse("bookmark_create") + "?url=/pull-requests/?author=darix")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Save Bookmark")
        self.assertContains(response, "/pull-requests/?author=darix")
        # Suggested name from URL path
        self.assertContains(response, "Pull Requests")

    def test_bookmark_create_post_success(self):
        response = self.client.post(
            reverse("bookmark_create"),
            {"name": "My Filter", "url": "/pull-requests/"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Refresh"], "true")
        self.assertTrue(Bookmark.objects.filter(user=self.user, name="My Filter").exists())

    def test_bookmark_create_post_validation_empty(self):
        response = self.client.post(
            reverse("bookmark_create"),
            {"name": "", "url": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Name cannot be empty.")
        self.assertContains(response, "URL cannot be empty.")

    def test_bookmark_create_post_validation_duplicate(self):
        Bookmark.objects.create(user=self.user, name="My Filter", url="/foo")
        response = self.client.post(
            reverse("bookmark_create"),
            {"name": "My Filter", "url": "/bar"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A bookmark with this name already exists.")

    def test_bookmark_create_post_validation_unsafe_url(self):
        unsafe_urls = [
            "https://evil.com",
            "javascript:alert(1)",
            "data:text/html,evil",
            "foo/bar",
        ]
        for url in unsafe_urls:
            response = self.client.post(
                reverse("bookmark_create"),
                {"name": "My Filter", "url": url},
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Invalid URL: must be a relative path starting with")

    def test_bookmark_edit_inline_get(self):
        bookmark = Bookmark.objects.create(user=self.user, name="My Filter", url="/foo")
        response = self.client.get(reverse("bookmark_edit_inline", args=[bookmark.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="My Filter"')
        self.assertContains(response, 'value="/foo"')

    def test_bookmark_edit_inline_post_success(self):
        bookmark = Bookmark.objects.create(user=self.user, name="My Filter", url="/foo")
        response = self.client.post(
            reverse("bookmark_edit_inline", args=[bookmark.id]),
            {"name": "Updated Filter", "url": "/bar"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Refresh"], "true")
        bookmark.refresh_from_db()
        self.assertEqual(bookmark.name, "Updated Filter")
        self.assertEqual(bookmark.url, "/bar")

    def test_bookmark_edit_inline_post_validation_duplicate(self):
        Bookmark.objects.create(user=self.user, name="Other Filter", url="/foo")
        bookmark = Bookmark.objects.create(user=self.user, name="My Filter", url="/bar")
        response = self.client.post(
            reverse("bookmark_edit_inline", args=[bookmark.id]),
            {"name": "Other Filter", "url": "/baz"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A bookmark with this name already exists.")

    def test_bookmark_cancel_edit(self):
        bookmark = Bookmark.objects.create(user=self.user, name="My Filter", url="/foo")
        response = self.client.get(reverse("bookmark_cancel_edit", args=[bookmark.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Filter")
        self.assertContains(response, "/foo")

    def test_bookmark_delete_confirm_empty(self):
        response = self.client.post(reverse("bookmark_delete_confirm"), {"selected_bookmarks": []})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No bookmarks selected.")

    def test_bookmark_delete_confirm_with_selection(self):
        b1 = Bookmark.objects.create(user=self.user, name="B1", url="/foo")
        b2 = Bookmark.objects.create(user=self.user, name="B2", url="/bar")
        response = self.client.post(
            reverse("bookmark_delete_confirm"),
            {"selected_bookmarks": [b1.id, b2.id]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Are you sure you want to delete <strong>2</strong> bookmark(s)?")

    def test_bookmark_delete_bulk(self):
        b1 = Bookmark.objects.create(user=self.user, name="B1", url="/foo")
        b2 = Bookmark.objects.create(user=self.user, name="B2", url="/bar")
        response = self.client.post(
            reverse("bookmark_delete_bulk"),
            {"selected_bookmarks": [b1.id, b2.id]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["HX-Refresh"], "true")
        self.assertEqual(Bookmark.objects.count(), 0)


import json
from django_bolt.testing import TestClient
from obs_flow_server.api import api


class BookmarkAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username="darix",
            username_lower="darix",
            full_name="Marcus Rueckert",
            email="mrueckert@suse.com",
            is_active=True,
        )
        from accounts.helpers import generate_secure_token
        from accounts.models import Token
        raw_token, last_eight, token_hash = generate_secure_token()
        Token.objects.create(
            user=self.user,
            last_eight=last_eight,
            token_hash=token_hash,
        )
        self.token = raw_token

    def test_api_list_bookmarks_empty(self):
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/list",
                content="{}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["bookmarks"], [])

    def test_api_list_bookmarks_with_filters(self):
        Bookmark.objects.create(user=self.user, name="Release 16.1", url="/foo")
        Bookmark.objects.create(user=self.user, name="Release 16.2", url="/bar")
        Bookmark.objects.create(user=self.user, name="Staging Batch", url="/baz")

        # Test exact names filter
        payload = {"names": ["Release 16.1", "Staging Batch"]}
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/list",
                content=json.dumps(payload),
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(len(res_data["bookmarks"]), 2)
        names = {b["name"] for b in res_data["bookmarks"]}
        self.assertEqual(names, {"Release 16.1", "Staging Batch"})

        # Test name contains filter
        payload = {"name_contains": ["Release"]}
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/list",
                content=json.dumps(payload),
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(len(res_data["bookmarks"]), 2)
        names = {b["name"] for b in res_data["bookmarks"]}
        self.assertEqual(names, {"Release 16.1", "Release 16.2"})

        # Test both filters combined with OR
        payload = {"names": ["Staging Batch"], "name_contains": ["16.1"]}
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/list",
                content=json.dumps(payload),
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(len(res_data["bookmarks"]), 2)
        names = {b["name"] for b in res_data["bookmarks"]}
        self.assertEqual(names, {"Release 16.1", "Staging Batch"})

    def test_api_add_bookmark_success(self):
        payload = {
            "name": "My Filter",
            "url": "/foo",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/add",
                content=json.dumps(payload),
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        bookmark_data = res_data["bookmark"]
        self.assertEqual(bookmark_data["name"], "My Filter")
        self.assertEqual(bookmark_data["url"], "/foo")
        self.assertTrue(Bookmark.objects.filter(user=self.user, name="My Filter").exists())

    def test_api_add_bookmark_duplicate(self):
        Bookmark.objects.create(user=self.user, name="My Filter", url="/foo")
        payload = {
            "name": "My Filter",
            "url": "/bar",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/add",
                content=json.dumps(payload),
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Bookmark with name 'My Filter' already exists", response.text)

    def test_api_add_bookmark_unsafe_url(self):
        unsafe_urls = [
            "https://evil.com",
            "javascript:alert(1)",
            "data:text/html,evil",
            "foo/bar",
        ]
        for url in unsafe_urls:
            payload = {
                "name": "My Filter",
                "url": url,
            }
            with TestClient(api) as client:
                response = client.post(
                    "/api/v1/bookmark/add",
                    content=json.dumps(payload),
                    headers={"Authorization": f"Bearer {self.token}"},
                )
            self.assertEqual(response.status_code, 400)
            self.assertIn("Invalid URL: must be a relative path starting with '/'", response.text)

    def test_api_remove_bookmark_success(self):
        Bookmark.objects.create(user=self.user, name="My Filter", url="/foo")
        payload = {
            "name": "My Filter",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/remove",
                content=json.dumps(payload),
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertTrue(res_data["success"])
        self.assertFalse(Bookmark.objects.filter(user=self.user, name="My Filter").exists())

    def test_api_remove_bookmark_not_found(self):
        payload = {
            "name": "NonExistent",
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/remove",
                content=json.dumps(payload),
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertFalse(res_data["success"])

    def test_api_import_bookmarks_success(self):
        payload = {
            "items": [
                {"name": "B1", "url": "/foo"},
                {"name": "B2", "url": "/bar"},
            ],
            "force": False,
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/import",
                content=json.dumps(payload),
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["imported_count"], 2)
        self.assertEqual(res_data["updated_count"], 0)
        self.assertEqual(Bookmark.objects.count(), 2)

    def test_api_import_bookmarks_conflict_no_force(self):
        Bookmark.objects.create(user=self.user, name="B1", url="/foo")
        payload = {
            "items": [
                {"name": "B1", "url": "/new-foo"},
                {"name": "B2", "url": "/bar"},
            ],
            "force": False,
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/import",
                content=json.dumps(payload),
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Conflict: Bookmark with name 'B1' already exists", response.text)
        # Transaction should have rolled back, so B2 must not be created
        self.assertEqual(Bookmark.objects.count(), 1)

    def test_api_import_bookmarks_conflict_with_force(self):
        Bookmark.objects.create(user=self.user, name="B1", url="/foo")
        payload = {
            "items": [
                {"name": "B1", "url": "/new-foo"},
                {"name": "B2", "url": "/bar"},
            ],
            "force": True,
        }
        with TestClient(api) as client:
            response = client.post(
                "/api/v1/bookmark/import",
                content=json.dumps(payload),
                headers={"Authorization": f"Bearer {self.token}"},
            )
        self.assertEqual(response.status_code, 200)
        res_data = response.json()
        self.assertEqual(res_data["imported_count"], 1)
        self.assertEqual(res_data["updated_count"], 1)
        self.assertEqual(Bookmark.objects.count(), 2)
        self.assertEqual(Bookmark.objects.get(name="B1").url, "/new-foo")
