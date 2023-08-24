"""
Test for models.
"""
from unittest.mock import patch

from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from core import models


def create_user(email="test@example.com", password="testpassword"):
    """Create and return a new user ."""
    return get_user_model().objects.create_user(email, password)


class ModelTest(TestCase):
    """Test models."""

    def test_create_user_with_email(self):
        """Test create user with an email is successful."""

        email = "test@example.com"
        password = "testpass123"
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_create_user_email_normalized(self):
        """Test email is nromalized for new users"""
        sample_emails = [
            ["test1@EXAMPLE.com", "test1@example.com"],
            ["Test2@Example.com", "Test2@example.com"],
            ["TEST3@EXAMPLE.COM", "TEST3@example.com"],
            ["test4@example.COM", "test4@example.com"],
        ]

        for email, excepted in sample_emails:
            user = get_user_model().objects.create_user(email, "sample123")
            self.assertEqual(user.email, excepted)

    def test_new_user_without_email_raises_error(self):
        """Test that creating a suer without an email raises a ValueError."""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user("", "test123")

    def test_create_super_user(self):
        """Test create superuser."""
        user = get_user_model().objects.create_superuser("test@example.com", "test123")

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_recipe(self):
        """Test creating a recipe is successful."""
        user = get_user_model().objects.create_user(
            email="test1@example",
            password="test12345678",
        )

        recipe = models.Recipe.objects.create(
            user=user,
            title="Test recipe name",
            time_minutes=5,
            price=Decimal("5.50"),
            description="Test description",
        )

        self.assertEqual(str(recipe), recipe.title)

    def test_create_tag(self):
        """Test create a tag successful ."""
        user = create_user()
        tag = models.Tag.objects.create(user=user, name="tag1")
        self.assertEqual(str(tag), tag.name)

    def test_create_ingredient(self):
        """Test create ingredients of recipe"""
        user = create_user()
        ingredient = models.Ingredient.objects.create(user=user, name="ingredient1")
        self.assertEqual(str(ingredient), ingredient.name)

    @patch("core.models.uuid.uuid4")
    def test_recipe_file_name_uuid(self, mock_uuid):
        """Test generating image path."""
        uuid = "test-uuid"
        mock_uuid.return_value = uuid
        file_path = models.recipe_image_file_path(None, "example.jpg")

        self.assertEqual(file_path, f"uploads/recipe/{uuid}.jpg")
