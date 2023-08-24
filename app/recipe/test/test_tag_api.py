"""
Tests for Tag APIs.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag
from recipe.serializers import TagSerializer

TAGS_URL = reverse("recipe:tag-list")


def detail_url(tag_id):
    """Create and return detail a ta g detail."""
    return reverse("recipe:tag-detail", args=[tag_id])


def create_user(email="testtag@example.com", password="test1password"):
    """Create  and return user for test."""
    return get_user_model().objects.create_user(email=email, password=password)


class PubliceTagApiTests(TestCase):
    """Test unautheticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(TAGS_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagApiTests(TestCase):
    """Test autenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrive_tags(self):
        """Test retrieving a list of tags."""
        Tag.objects.create(user=self.user, name="Noodles")
        Tag.objects.create(user=self.user, name="Dessert")

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by("-name")
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user."""
        user2 = create_user(email="user2@example.com", password="otherpassword1234")
        Tag.objects.create(user=self.user, name="Rice")
        Tag.objects.create(user=user2, name="Noodles")

        res = self.client.get(TAGS_URL)
        tags = Tag.objects.filter(user=self.user).order_by("-name")
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.data[0]["name"], tags[0].name)
        self.assertEqual(res.data[0]["id"], tags[0].id)

    def test_update_tag(self):
        """Test updating a tag."""
        tag = Tag.objects.create(user=self.user, name="Rice")

        payload = {"name": "noodles"}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload["name"])

    def test_delete_tag(self):
        """Test delete a tag."""
        tag = Tag.objects.create(user=self.user, name="Rice")

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Tag.objects.filter(id=tag.id).exists())

    def test_filter_tags_assigned_to_recipes(self):
        """Test listing tags to those assigned to recipes."""
        tag1 = Tag.objects.create(user=self.user, name="Breakfast")
        tag2 = Tag.objects.create(user=self.user, name="Launch")

        recipe = Recipe.objects.create(
            user=self.user,
            title="Pork Hamburger",
            time_minutes=40,
            price=Decimal("5.99"),
        )
        recipe.tag.add(tag1)

        res = self.client.get(TAGS_URL, {"assigned_only": 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        """Test filtered tags return a unique lsit."""
        ing = Tag.objects.create(user=self.user, name="Breakfast")
        Tag.objects.create(user=self.user, name="Dinner")

        recipe1 = Recipe.objects.create(
            user=self.user,
            title="Beef Hamburger",
            time_minutes=45,
            price=Decimal("7.99"),
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title="Beef Sandwich",
            time_minutes=35,
            price=Decimal("5.99"),
        )

        recipe1.tag.add(ing)
        recipe2.tag.add(ing)

        res = self.client.get(TAGS_URL, {"assigned_only": 1})
        self.assertEqual(len(res.data), 1)
