"""
Comprehensive FastAPI endpoint validation script.

Tests all CRUD operations, references, pagination, search, and error handling.

Run with: uv run python test_api_endpoints.py
(Make sure the FastAPI server is running first)
"""

import asyncio
import httpx
import json
from typing import Any, Optional

# Configuration
BASE_URL = "http://localhost:8000"
TIMEOUT = 30.0

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class APIValidator:
    """Validates FastAPI endpoints."""

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

    async def assert_status(self, response: httpx.Response, expected: int, test_name: str) -> bool:
        """Assert response status code."""
        if response.status_code == expected:
            self.log_pass(f"Status {response.status_code}")
            return True
        else:
            self.log_fail(
                f"Expected status {expected}, got {response.status_code}. "
                f"Response: {response.text[:200]}"
            )
            return False

    async def assert_field(self, data: dict, field: str, test_name: str) -> Optional[Any]:
        """Assert field exists in response."""
        if field in data:
            self.log_pass(f"Field '{field}' exists")
            return data[field]
        else:
            self.log_fail(f"Field '{field}' missing. Data: {data}")
            return None

    # ========== HEALTH & ROOT TESTS ==========

    async def test_health_check(self):
        """Test health check endpoint."""
        self.log_test("Health Check")
        response = await self.client.get("/health")
        await self.assert_status(response, 200, "health check")
        data = response.json()
        await self.assert_field(data, "message", "health check")

    async def test_root(self):
        """Test root endpoint."""
        self.log_test("Root Endpoint")
        response = await self.client.get("/")
        await self.assert_status(response, 200, "root")
        data = response.json()
        await self.assert_field(data, "service", "root")
        await self.assert_field(data, "version", "root")

    # ========== AUTHOR CRUD TESTS ==========

    async def test_create_author_valid(self):
        """Test creating an author with valid data."""
        self.log_test("Create Author (Valid)")
        payload = {
            "name": "Alice Johnson",
            "email": "alice@example.com",
            "bio": "Tech writer and blogger",
        }
        response = await self.client.post("/authors", json=payload)
        await self.assert_status(response, 201, "create author")
        data = response.json()
        author_id = await self.assert_field(data, "id", "create author")
        if author_id:
            self.author_ids.append(author_id)
            self.log_info(f"Author ID: {author_id}")

    async def test_create_author_invalid(self):
        """Test creating an author with invalid data (missing required field)."""
        self.log_test("Create Author (Invalid - missing email)")
        payload = {"name": "Bob Smith"}
        response = await self.client.post("/authors", json=payload)
        if response.status_code >= 400:
            self.log_pass(f"Correctly rejected with status {response.status_code}")
        else:
            self.log_fail(f"Should reject invalid author, got {response.status_code}")

    async def test_get_author_valid(self):
        """Test getting a valid author."""
        self.log_test("Get Author (Valid)")
        if not self.author_ids:
            self.log_fail("No author ID available")
            return

        author_id = self.author_ids[0]
        response = await self.client.get(f"/authors/{author_id}")
        await self.assert_status(response, 200, "get author")
        data = response.json()
        await self.assert_field(data, "id", "get author")
        await self.assert_field(data, "name", "get author")

    async def test_get_author_invalid_id(self):
        """Test getting an author with invalid ObjectId format."""
        self.log_test("Get Author (Invalid ID format)")
        response = await self.client.get("/authors/invalid-id")
        if response.status_code == 400:
            self.log_pass("Correctly rejected invalid ObjectId")
        else:
            self.log_fail(f"Should return 400 for invalid ID, got {response.status_code}")

    async def test_get_author_not_found(self):
        """Test getting a non-existent author."""
        self.log_test("Get Author (Not Found)")
        valid_oid = "507f1f77bcf86cd799439011"
        response = await self.client.get(f"/authors/{valid_oid}")
        if response.status_code == 404:
            self.log_pass("Correctly returned 404")
        else:
            self.log_fail(f"Should return 404, got {response.status_code}")

    async def test_list_authors(self):
        """Test listing authors with pagination."""
        self.log_test("List Authors")
        response = await self.client.get("/authors?skip=0&limit=10")
        await self.assert_status(response, 200, "list authors")
        data = response.json()
        await self.assert_field(data, "items", "list authors")
        await self.assert_field(data, "total", "list authors")
        await self.assert_field(data, "has_more", "list authors")

    async def test_list_authors_pagination(self):
        """Test author pagination limits."""
        self.log_test("List Authors (Pagination - limit validation)")
        response = await self.client.get("/authors?skip=0&limit=200")
        if response.status_code == 422:
            self.log_pass("Correctly rejected limit > 100")
        else:
            self.log_fail(f"Should reject limit > 100, got {response.status_code}")

    async def test_update_author(self):
        """Test updating an author."""
        self.log_test("Update Author")
        if not self.author_ids:
            self.log_fail("No author ID available")
            return

        author_id = self.author_ids[0]
        payload = {"name": "Alice Johnson Updated", "bio": "Updated bio"}
        response = await self.client.put(f"/authors/{author_id}", json=payload)
        await self.assert_status(response, 200, "update author")
        data = response.json()
        author_data = data.get("id")
        if author_data:
            self.log_pass(f"Author updated: {author_data}")

    # ========== BLOG POST CRUD TESTS ==========

    async def test_create_post_valid(self):
        """Test creating a blog post with valid data."""
        self.log_test("Create Blog Post (Valid)")
        if not self.author_ids:
            self.log_fail("No author ID available")
            return

        payload = {
            "title": "Getting Started with Pygoose",
            "content": "Pygoose is an async MongoDB ODM for Python...",
            "author_id": self.author_ids[0],
            "published": False,
            "tags": ["python", "mongodb", "async"],
        }
        response = await self.client.post("/posts", json=payload)
        await self.assert_status(response, 201, "create post")
        data = response.json()
        post_id = await self.assert_field(data, "id", "create post")
        if post_id:
            self.post_ids.append(post_id)
            self.log_info(f"Post ID: {post_id}")

    async def test_create_post_invalid_author(self):
        """Test creating a post with non-existent author."""
        self.log_test("Create Blog Post (Invalid author)")
        valid_oid = "507f1f77bcf86cd799439011"
        payload = {
            "title": "Test Post",
            "content": "Test content",
            "author_id": valid_oid,
            "tags": [],
        }
        response = await self.client.post("/posts", json=payload)
        if response.status_code == 404:
            self.log_pass("Correctly rejected non-existent author")
        else:
            self.log_fail(f"Should return 404 for non-existent author, got {response.status_code}")

    async def test_create_post_invalid_id_format(self):
        """Test creating a post with invalid author_id format."""
        self.log_test("Create Blog Post (Invalid author_id format)")
        payload = {
            "title": "Test Post",
            "content": "Test content",
            "author_id": "invalid-id",
            "tags": [],
        }
        response = await self.client.post("/posts", json=payload)
        if response.status_code >= 400:
            self.log_pass(f"Correctly rejected invalid author_id format")
        else:
            self.log_fail(f"Should reject invalid author_id, got {response.status_code}")

    async def test_get_post_with_population(self):
        """Test getting a post with author populated."""
        self.log_test("Get Blog Post (With population)")
        if not self.post_ids:
            self.log_fail("No post ID available")
            return

        post_id = self.post_ids[0]
        response = await self.client.get(f"/posts/{post_id}?populate=true")
        await self.assert_status(response, 200, "get post")
        data = response.json()
        await self.assert_field(data, "id", "get post")
        await self.assert_field(data, "title", "get post")
        author = await self.assert_field(data, "author", "get post")
        if author:
            self.log_info(f"Author populated: {author.get('name')}")

    async def test_get_post_without_population(self):
        """Test getting a post without populating author."""
        self.log_test("Get Blog Post (Without population)")
        if not self.post_ids:
            self.log_fail("No post ID available")
            return

        post_id = self.post_ids[0]
        response = await self.client.get(f"/posts/{post_id}?populate=false")
        await self.assert_status(response, 200, "get post")
        data = response.json()
        author = data.get("author")
        if author is None:
            self.log_pass("Author not populated as expected")
        else:
            self.log_fail(f"Author should be None when populate=false")

    async def test_list_posts(self):
        """Test listing posts with pagination."""
        self.log_test("List Posts")
        response = await self.client.get("/posts?skip=0&limit=10&populate=true")
        await self.assert_status(response, 200, "list posts")
        data = response.json()
        await self.assert_field(data, "items", "list posts")
        await self.assert_field(data, "total", "list posts")
        await self.assert_field(data, "has_more", "list posts")

    async def test_list_posts_published_only(self):
        """Test listing only published posts."""
        self.log_test("List Posts (Published only)")
        response = await self.client.get("/posts?published_only=true")
        await self.assert_status(response, 200, "list posts")
        data = response.json()
        for item in data.get("items", []):
            if not item.get("published"):
                self.log_fail("Found unpublished post in published_only query")
                return
        self.log_pass("All returned posts are published")

    async def test_update_post(self):
        """Test updating a blog post."""
        self.log_test("Update Blog Post")
        if not self.post_ids:
            self.log_fail("No post ID available")
            return

        post_id = self.post_ids[0]
        payload = {
            "title": "Updated Title",
            "content": "Updated content...",
        }
        response = await self.client.put(f"/posts/{post_id}", json=payload)
        await self.assert_status(response, 200, "update post")
        data = response.json()
        title = data.get("title")
        if title == "Updated Title":
            self.log_pass(f"Post title updated: {title}")
        else:
            self.log_fail(f"Post title not updated correctly")

    async def test_increment_view_count(self):
        """Test incrementing view count."""
        self.log_test("Increment View Count")
        if not self.post_ids:
            self.log_fail("No post ID available")
            return

        post_id = self.post_ids[0]
        # Get initial views
        get_response = await self.client.get(f"/posts/{post_id}?populate=false")
        initial_views = get_response.json().get("views", 0)

        # Increment
        response = await self.client.post(f"/posts/{post_id}/view")
        await self.assert_status(response, 200, "increment view")

        # Get updated views
        get_response = await self.client.get(f"/posts/{post_id}?populate=false")
        new_views = get_response.json().get("views", 0)

        if new_views == initial_views + 1:
            self.log_pass(f"Views incremented: {initial_views} -> {new_views}")
        else:
            self.log_fail(f"Views not incremented correctly: {initial_views} -> {new_views}")

    async def test_publish_post(self):
        """Test publishing a blog post."""
        self.log_test("Publish Blog Post")
        if not self.post_ids:
            self.log_fail("No post ID available")
            return

        post_id = self.post_ids[0]
        response = await self.client.post(f"/posts/{post_id}/publish")
        await self.assert_status(response, 200, "publish post")
        data = response.json()
        published = data.get("published")
        if published:
            self.log_pass("Post published successfully")
        else:
            self.log_fail("Post not marked as published")

    async def test_publish_already_published(self):
        """Test publishing an already published post."""
        self.log_test("Publish Post (Already published)")
        if not self.post_ids:
            self.log_fail("No post ID available")
            return

        post_id = self.post_ids[0]
        response = await self.client.post(f"/posts/{post_id}/publish")
        if response.status_code == 400:
            self.log_pass("Correctly rejected publishing already-published post")
        else:
            self.log_fail(f"Should return 400, got {response.status_code}")

    # ========== SEARCH TESTS ==========

    async def test_search_posts_by_author(self):
        """Test searching posts by author."""
        self.log_test("Search Posts by Author")
        if not self.author_ids:
            self.log_fail("No author ID available")
            return

        author_id = self.author_ids[0]
        response = await self.client.get(f"/authors/{author_id}/posts?skip=0&limit=10")
        await self.assert_status(response, 200, "search by author")
        data = response.json()
        await self.assert_field(data, "items", "search by author")
        posts = data.get("items", [])
        self.log_info(f"Found {len(posts)} posts by author")

    async def test_search_posts_by_tag(self):
        """Test searching posts by tag."""
        self.log_test("Search Posts by Tag")
        response = await self.client.get("/posts/search/by-tag/python?skip=0&limit=10")
        await self.assert_status(response, 200, "search by tag")
        data = response.json()
        await self.assert_field(data, "items", "search by tag")
        posts = data.get("items", [])
        self.log_info(f"Found {len(posts)} posts with tag 'python'")

    # ========== STATISTICS TESTS ==========

    async def test_statistics(self):
        """Test getting statistics."""
        self.log_test("Statistics")
        response = await self.client.get("/stats")
        await self.assert_status(response, 200, "statistics")
        data = response.json()
        await self.assert_field(data, "total_authors", "statistics")
        await self.assert_field(data, "total_posts", "statistics")
        await self.assert_field(data, "published_posts", "statistics")
        await self.assert_field(data, "draft_posts", "statistics")

    # ========== DELETE TESTS (Run last) ==========

    async def test_delete_post(self):
        """Test deleting a blog post."""
        self.log_test("Delete Blog Post")
        if not self.post_ids:
            self.log_fail("No post ID available")
            return

        post_id = self.post_ids[0]
        response = await self.client.delete(f"/posts/{post_id}")
        await self.assert_status(response, 200, "delete post")
        self.log_info(f"Post deleted: {post_id}")

    async def test_delete_author_with_posts(self):
        """Test that deleting an author with posts fails."""
        self.log_test("Delete Author (With posts)")
        if not self.author_ids:
            self.log_fail("No author ID available")
            return

        # Create another post first (if we have an author)
        author_id = self.author_ids[0]
        payload = {
            "title": "Another Post",
            "content": "Content...",
            "author_id": author_id,
            "tags": [],
        }
        await self.client.post("/posts", json=payload)

        # Try to delete author
        response = await self.client.delete(f"/authors/{author_id}")
        if response.status_code == 400:
            self.log_pass("Correctly prevented deletion of author with posts")
        else:
            self.log_fail(f"Should prevent deletion, got {response.status_code}")

    async def test_delete_author_without_posts(self):
        """Test deleting an author without posts."""
        self.log_test("Delete Author (Without posts)")
        # Create a new author with no posts
        payload = {
            "name": "Bob Smith",
            "email": "bob@example.com",
        }
        create_response = await self.client.post("/authors", json=payload)
        author_id = create_response.json().get("id")

        if not author_id:
            self.log_fail("Could not create test author")
            return

        # Delete the author
        response = await self.client.delete(f"/authors/{author_id}")
        await self.assert_status(response, 200, "delete author")

    # ========== SUMMARY ==========

    async def run_all_tests(self):
        """Run all tests in order."""
        print(f"\n{BOLD}{'=' * 70}")
        print(f"FastAPI Endpoint Validation Suite")
        print(f"{'=' * 70}{RESET}\n")

        try:
            # Health & Root
            await self.test_health_check()
            await self.test_root()

            # Author CRUD
            await self.test_create_author_valid()
            await self.test_create_author_invalid()
            await self.test_get_author_valid()
            await self.test_get_author_invalid_id()
            await self.test_get_author_not_found()
            await self.test_list_authors()
            await self.test_list_authors_pagination()
            await self.test_update_author()

            # Blog Post CRUD
            await self.test_create_post_valid()
            await self.test_create_post_invalid_author()
            await self.test_create_post_invalid_id_format()
            await self.test_get_post_with_population()
            await self.test_get_post_without_population()
            await self.test_list_posts()
            await self.test_list_posts_published_only()
            await self.test_update_post()
            await self.test_increment_view_count()
            await self.test_publish_post()
            await self.test_publish_already_published()

            # Search
            await self.test_search_posts_by_author()
            await self.test_search_posts_by_tag()

            # Statistics
            await self.test_statistics()

            # Delete (last)
            await self.test_delete_post()
            await self.test_delete_author_with_posts()
            await self.test_delete_author_without_posts()

        except Exception as e:
            self.log_fail(f"Unexpected error: {e}")
            import traceback

            traceback.print_exc()

        finally:
            # Print summary
            self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print(f"\n{BOLD}{'=' * 70}")
        print(f"Test Summary")
        print(f"{'=' * 70}{RESET}")
        print(f"Total Tests: {self.test_count}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")

        if self.failed == 0:
            print(f"\n{GREEN}{BOLD}✅ All tests passed!{RESET}")
        else:
            print(f"\n{RED}{BOLD}❌ Some tests failed{RESET}")


async def main():
    """Run validation script."""
    validator = APIValidator()

    try:
        await validator.run_all_tests()
    finally:
        await validator.close()


if __name__ == "__main__":
    asyncio.run(main())
