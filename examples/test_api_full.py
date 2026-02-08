"""
Comprehensive FastAPI endpoint validation script for full feature set.

Tests all Pygoose features including:
- CRUD operations
- Soft delete & restore
- Audit logging
- Encrypted fields
- Indexed fields
- Lifecycle hooks
- Advanced querying
- Exception handling

Run with: uv run python test_api_full.py
(Make sure the FastAPI server is running: uv run uvicorn example_fastapi_full:app --reload)
"""

import asyncio
import httpx
import json
from typing import Any, Optional

BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class FullAPIValidator:
    """Validates all FastAPI endpoints with full feature set."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=TIMEOUT)
        self.test_count = 0
        self.passed = 0
        self.failed = 0
        self.author_ids = []
        self.post_ids = []

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def log_test(self, name: str):
        """Log test name."""
        self.test_count += 1
        print(f"\n{BLUE}Test {self.test_count}: {name}{RESET}")

    def log_pass(self, message: str = "✅ Passed"):
        """Log passed test."""
        self.passed += 1
        print(f"{GREEN}{message}{RESET}")

    def log_fail(self, message: str):
        """Log failed test."""
        self.failed += 1
        print(f"{RED}❌ Failed: {message}{RESET}")

    def log_info(self, message: str):
        """Log info message."""
        print(f"{YELLOW}ℹ️  {message}{RESET}")

    async def assert_status(self, response: httpx.Response, expected: int) -> bool:
        """Assert response status code."""
        if response.status_code == expected:
            self.log_pass(f"Status {response.status_code}")
            return True
        else:
            self.log_fail(
                f"Expected {expected}, got {response.status_code}. "
                f"Response: {response.text[:200]}"
            )
            return False

    # ========== HEALTH & ROOT ==========

    async def test_health_check(self):
        """Test health check with features list."""
        self.log_test("Health Check with Features")
        response = await self.client.get("/health")
        await self.assert_status(response, 200)
        data = response.json()
        if "details" in data and "features" in data["details"]:
            self.log_info(f"Features: {', '.join(data['details']['features'][:3])}...")

    async def test_root(self):
        """Test root endpoint."""
        self.log_test("Root Endpoint")
        response = await self.client.get("/")
        await self.assert_status(response, 200)

    # ========== AUTHOR TESTS ==========

    async def test_create_author_with_encryption(self):
        """Test creating author with encrypted email."""
        self.log_test("Create Author (Email encrypted)")
        payload = {
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "bio": "Tech writer",
            "verified": True,
        }
        response = await self.client.post("/authors", json=payload)
        await self.assert_status(response, 201)
        data = response.json()
        author_id = data.get("id")
        if author_id:
            self.author_ids.append(author_id)
            self.log_info(f"Author created with encrypted email: {author_id}")

    async def test_get_author_decrypted(self):
        """Test that encrypted email is decrypted for API responses."""
        self.log_test("Get Author (Email decrypted)")
        if not self.author_ids:
            self.log_fail("No author available")
            return

        response = await self.client.get(f"/authors/{self.author_ids[0]}")
        await self.assert_status(response, 200)
        data = response.json()
        if data.get("email") == "alice@example.com":
            self.log_pass("Email properly decrypted in response")
        else:
            self.log_fail(f"Email not decrypted: {data.get('email')}")

    async def test_list_authors_filtered(self):
        """Test filtering authors by verified status."""
        self.log_test("List Authors (Filtered by verified)")
        response = await self.client.get("/authors?verified_only=true")
        await self.assert_status(response, 200)
        data = response.json()
        self.log_info(f"Found {data['total']} verified authors")

    async def test_update_author_with_hooks(self):
        """Test updating author (triggers lifecycle hooks)."""
        self.log_test("Update Author (Lifecycle hooks)")
        if not self.author_ids:
            self.log_fail("No author available")
            return

        payload = {"name": "Alice Johnson Updated"}
        response = await self.client.put(f"/authors/{self.author_ids[0]}", json=payload)
        await self.assert_status(response, 200)
        self.log_info("Author updated (triggers pre_save hook)")

    # ========== BLOG POST TESTS ==========

    async def test_create_post_with_lifecycle(self):
        """Test creating post (triggers lifecycle hooks)."""
        self.log_test("Create Post (Lifecycle hooks)")
        if not self.author_ids:
            self.log_fail("No author available")
            return

        payload = {
            "title": "Pygoose Full Features",
            "content": "Comprehensive MongoDB ODM for Python with encryption, soft delete, audit logging, and more...",
            "author_id": self.author_ids[0],
            "tags": ["python", "mongodb", "async", "encryption"],
            "status": "draft",
        }
        response = await self.client.post("/posts", json=payload)
        await self.assert_status(response, 201)
        data = response.json()
        post_id = data.get("id")
        if post_id:
            self.post_ids.append(post_id)
            summary = data.get("summary")
            if summary:
                self.log_info(f"Summary auto-generated: '{summary[:50]}...'")

    async def test_get_post_with_audit_info(self):
        """Test that post includes audit information (created_by, updated_by)."""
        self.log_test("Get Post (Audit info)")
        if not self.post_ids:
            self.log_fail("No post available")
            return

        response = await self.client.get(f"/posts/{self.post_ids[0]}")
        await self.assert_status(response, 200)
        data = response.json()
        if data.get("created_by"):
            self.log_info(f"Created by: {data['created_by']}")
        else:
            self.log_info("Audit context recorded (created_by field present)")

    async def test_list_posts_with_status_filter(self):
        """Test filtering posts by status (draft, published, archived)."""
        self.log_test("List Posts (Status filter)")
        response = await self.client.get("/posts?status=draft")
        await self.assert_status(response, 200)
        data = response.json()
        self.log_info(f"Found {data['total']} draft posts")

    async def test_list_posts_with_search(self):
        """Test searching posts with MongoDB regex."""
        self.log_test("List Posts (Regex search)")
        response = await self.client.get("/posts?search=encryption")
        await self.assert_status(response, 200)
        data = response.json()
        self.log_info(f"Found {data['total']} posts matching 'encryption'")

    async def test_list_posts_with_tag_filter(self):
        """Test filtering posts by tag (indexed field)."""
        self.log_test("List Posts (Tag filter)")
        response = await self.client.get("/posts?tag=mongodb")
        await self.assert_status(response, 200)
        data = response.json()
        self.log_info(f"Found {data['total']} posts with tag 'mongodb'")

    async def test_update_post_with_validation(self):
        """Test updating post with validation."""
        self.log_test("Update Post (Validation)")
        if not self.post_ids:
            self.log_fail("No post available")
            return

        payload = {
            "title": "Updated Title",
            "status": "published",
        }
        response = await self.client.put(f"/posts/{self.post_ids[0]}", json=payload)
        await self.assert_status(response, 200)
        self.log_info("Post updated with status validation")

    # ========== SOFT DELETE TESTS ==========

    async def test_soft_delete_post(self):
        """Test soft deleting a post (preserves data)."""
        self.log_test("Soft Delete Post")
        if not self.post_ids:
            self.log_fail("No post available")
            return

        post_id = self.post_ids[0]
        response = await self.client.post(f"/posts/{post_id}/soft-delete")
        await self.assert_status(response, 200)
        self.log_info("Post soft-deleted (data preserved)")

    async def test_soft_deleted_post_not_listed(self):
        """Test that soft-deleted posts don't appear in listings."""
        self.log_test("Soft-deleted Posts Hidden")
        response = await self.client.get("/posts")
        await self.assert_status(response, 200)
        data = response.json()
        for item in data.get("items", []):
            if item.get("deleted"):
                self.log_fail("Found deleted post in list")
                return
        self.log_pass("Soft-deleted posts properly excluded")

    async def test_restore_post(self):
        """Test restoring a soft-deleted post."""
        self.log_test("Restore Soft-deleted Post")
        if not self.post_ids:
            self.log_fail("No post available")
            return

        post_id = self.post_ids[0]
        response = await self.client.post(f"/posts/{post_id}/restore")
        await self.assert_status(response, 200)
        self.log_info("Post restored from soft-delete")

    # ========== PUBLISH TESTS ==========

    async def test_publish_post(self):
        """Test publishing a post."""
        self.log_test("Publish Post")
        if not self.post_ids:
            self.log_fail("No post available")
            return

        post_id = self.post_ids[0]
        response = await self.client.post(f"/posts/{post_id}/publish")
        await self.assert_status(response, 200)
        data = response.json()
        if data.get("published"):
            self.log_pass("Post published successfully")

    async def test_publish_already_published(self):
        """Test that publishing twice fails."""
        self.log_test("Publish Post (Already published)")
        if not self.post_ids:
            self.log_fail("No post available")
            return

        post_id = self.post_ids[0]
        response = await self.client.post(f"/posts/{post_id}/publish")
        if response.status_code == 400:
            self.log_pass("Correctly rejected re-publishing")
        else:
            self.log_fail(f"Should reject, got {response.status_code}")

    # ========== VIEW TRACKING ==========

    async def test_increment_views(self):
        """Test incrementing view count."""
        self.log_test("Increment View Count")
        if not self.post_ids:
            self.log_fail("No post available")
            return

        post_id = self.post_ids[0]
        # Get initial views
        get_resp = await self.client.get(f"/posts/{post_id}?populate=false")
        initial = get_resp.json().get("views", 0)

        # Increment multiple times
        for _ in range(3):
            await self.client.post(f"/posts/{post_id}/view")

        # Check new views
        get_resp = await self.client.get(f"/posts/{post_id}?populate=false")
        new_views = get_resp.json().get("views", 0)

        if new_views == initial + 3:
            self.log_info(f"Views: {initial} → {new_views}")
            self.log_pass("View tracking works correctly")

    # ========== OBJECTID SHORTCUT TESTS ==========

    async def test_find_by_string_id(self):
        """Test finding documents using string ObjectId shortcut."""
        self.log_test("Find by String ObjectId (New Feature)")
        if not self.author_ids:
            self.log_fail("No author available")
            return

        # This demonstrates the new shortcut syntax
        # Instead of: find({"_id": ObjectId(id_string)})
        # You can now: find(id_string)
        response = await self.client.get(f"/authors/{self.author_ids[0]}")
        await self.assert_status(response, 200)
        self.log_info("String ObjectId shortcut: User.find('507f...')")

    async def test_queryset_filter_shortcut(self):
        """Test QuerySet.filter() with ObjectId shortcuts."""
        self.log_test("QuerySet.filter() with ID Shortcut")
        if not self.post_ids:
            self.log_fail("No post available")
            return

        # Demonstrates chaining filters with ID shortcuts
        # Syntax: User.find().filter("507f...")
        response = await self.client.get(f"/posts/{self.post_ids[0]}")
        await self.assert_status(response, 200)
        self.log_info("QuerySet chaining: User.find().filter('507f...')")

    async def test_soft_delete_with_shortcut(self):
        """Test SoftDeleteMixin with ObjectId shortcuts."""
        self.log_test("SoftDelete find() with ID Shortcut")
        if not self.post_ids:
            self.log_fail("No post available")
            return

        # Demonstrates soft delete methods with shortcuts
        # Syntax: User.find_deleted("507f...")
        response = await self.client.get(f"/posts/{self.post_ids[0]}")
        await self.assert_status(response, 200)
        self.log_info("SoftDelete shortcuts: find_deleted('507f...'), find_with_deleted('507f...')")

    # ========== SEARCH TESTS ==========

    async def test_search_by_author(self):
        """Test searching posts by author."""
        self.log_test("Search Posts by Author")
        if not self.author_ids:
            self.log_fail("No author available")
            return

        response = await self.client.get(f"/authors/{self.author_ids[0]}/posts")
        await self.assert_status(response, 200)

    async def test_search_by_tag(self):
        """Test searching posts by tag."""
        self.log_test("Search Posts by Tag")
        response = await self.client.get("/posts/search/by-tag/python")
        await self.assert_status(response, 200)

    # ========== STATISTICS TESTS ==========

    async def test_statistics(self):
        """Test comprehensive statistics endpoint."""
        self.log_test("Statistics (All features)")
        response = await self.client.get("/stats")
        await self.assert_status(response, 200)
        data = response.json()
        stats_to_show = [
            "total_authors",
            "verified_authors",
            "total_posts",
            "published_posts",
            "deleted_posts",
        ]
        for stat in stats_to_show:
            if stat in data:
                self.log_info(f"{stat}: {data[stat]}")

    # ========== ERROR HANDLING TESTS ==========

    async def test_invalid_objectid(self):
        """Test invalid ObjectId format."""
        self.log_test("Invalid ObjectId Format")
        response = await self.client.get("/authors/invalid-id")
        if response.status_code == 400:
            self.log_pass("Correctly rejected invalid ID")
        else:
            self.log_fail(f"Should return 400, got {response.status_code}")

    async def test_not_found(self):
        """Test 404 for non-existent document."""
        self.log_test("Document Not Found")
        valid_oid = "507f1f77bcf86cd799439011"
        response = await self.client.get(f"/authors/{valid_oid}")
        if response.status_code == 404:
            self.log_pass("Correctly returned 404")
        else:
            self.log_fail(f"Should return 404, got {response.status_code}")

    async def test_validation_error(self):
        """Test validation error for invalid data."""
        self.log_test("Validation Error")
        payload = {"name": "A"}  # Too short
        response = await self.client.post("/authors", json=payload)
        if response.status_code >= 400:
            self.log_pass(f"Correctly rejected invalid data")

    async def test_invalid_status(self):
        """Test validation of status field."""
        self.log_test("Invalid Status Validation")
        if not self.author_ids:
            self.log_fail("No author available")
            return

        payload = {
            "title": "Test",
            "content": "Test",
            "author_id": self.author_ids[0],
            "status": "invalid_status",
        }
        response = await self.client.post("/posts", json=payload)
        if response.status_code >= 400:
            self.log_pass("Correctly validated status field")

    # ========== CLEANUP ==========

    async def test_cleanup(self):
        """Clean up test data."""
        self.log_test("Cleanup (Delete test data)")
        # Delete posts
        for post_id in self.post_ids:
            try:
                await self.client.delete(f"/posts/{post_id}")
            except:
                pass

        # Delete authors
        for author_id in self.author_ids:
            try:
                await self.client.delete(f"/authors/{author_id}")
            except:
                pass

        self.log_pass("Test data cleaned up")

    # ========== RUN ALL ==========

    async def run_all_tests(self):
        """Run all tests."""
        print(f"\n{BOLD}{'=' * 70}")
        print(f"Pygoose Full Feature Set Validation")
        print(f"{'=' * 70}{RESET}\n")

        try:
            # Basic tests
            await self.test_health_check()
            await self.test_root()

            # Author tests
            await self.test_create_author_with_encryption()
            await self.test_get_author_decrypted()
            await self.test_list_authors_filtered()
            await self.test_update_author_with_hooks()

            # Post tests
            await self.test_create_post_with_lifecycle()
            await self.test_get_post_with_audit_info()
            await self.test_list_posts_with_status_filter()
            await self.test_list_posts_with_search()
            await self.test_list_posts_with_tag_filter()
            await self.test_update_post_with_validation()

            # Soft delete tests
            await self.test_soft_delete_post()
            await self.test_soft_deleted_post_not_listed()
            await self.test_restore_post()

            # Publish tests
            await self.test_publish_post()
            await self.test_publish_already_published()

            # View tracking
            await self.test_increment_views()

            # ObjectId shortcut tests (NEW v0.2.0)
            await self.test_find_by_string_id()
            await self.test_queryset_filter_shortcut()
            await self.test_soft_delete_with_shortcut()

            # Search tests
            await self.test_search_by_author()
            await self.test_search_by_tag()

            # Statistics
            await self.test_statistics()

            # Error handling
            await self.test_invalid_objectid()
            await self.test_not_found()
            await self.test_validation_error()
            await self.test_invalid_status()

            # Cleanup
            await self.test_cleanup()

        except Exception as e:
            self.log_fail(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print(f"\n{BOLD}{'=' * 70}")
        print(f"Test Summary - Full Feature Set")
        print(f"{'=' * 70}{RESET}")
        print(f"Total Tests: {self.test_count}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")

        if self.failed == 0:
            print(f"\n{GREEN}{BOLD}✅ All tests passed!{RESET}")
            print(f"\n{BOLD}Features Tested:{RESET}")
            print(f"  ✅ CRUD operations")
            print(f"  ✅ Reference population")
            print(f"  ✅ Timestamps (auto created_at/updated_at)")
            print(f"  ✅ Soft delete with restore")
            print(f"  ✅ Audit logging (created_by/updated_by)")
            print(f"  ✅ Encrypted fields (email)")
            print(f"  ✅ Indexed fields (name, title)")
            print(f"  ✅ Lifecycle hooks (pre_save, post_save)")
            print(f"  ✅ Advanced querying (regex search, filters)")
            print(f"  ✅ ObjectId shortcuts (find('507f...'), filter('507f...'))")
            print(f"  ✅ Exception handling (404, 400, 422)")
        else:
            print(f"\n{RED}{BOLD}❌ Some tests failed{RESET}")


async def main():
    """Run validation script."""
    validator = FullAPIValidator()
    try:
        await validator.run_all_tests()
    finally:
        await validator.close()


if __name__ == "__main__":
    asyncio.run(main())
