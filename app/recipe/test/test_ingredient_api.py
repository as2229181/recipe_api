"""
Test for ingredients API.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Ingredient
from recipe.serializers import IngredientSerializer

INGREDIRNT_URL = reverse("recipe:ingredient-list")


def detail_url(ingredient_id):
    """Create and return detail  for an ingredient."""
    return reverse("recipe:ingredient-detail", args=[ingredient_id])


def create_user(email="user@example.com", password="testpassword123"):
    """Create and return user for test."""
    return get_user_model().objects.create(email=email, password=password)


class PublicIngredientAPITests(TestCase):
    """Test unauthenticate API request."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(INGREDIRNT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientAPITests(TestCase):
    """Test autenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrive_tags(self):
        """Test retrieving a list of ingredients."""
        Ingredient.objects.create(user=self.user, name="Carrot")
        Ingredient.objects.create(user=self.user, name="Clump")

        res = self.client.get(INGREDIRNT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredients = Ingredient.objects.filter(user=self.user).order_by("-name")
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        user2 = create_user(email="user2@example.com", password="test2password")
        Ingredient.objects.create(user=self.user, name="Onion")
        Ingredient.objects.create(user=user2, name="New ingredients")

        res = self.client.get(INGREDIRNT_URL)
        ingredients = Ingredient.objects.filter(user=self.user).order_by("-name")
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.data[0]["name"], ingredients[0].name)
        self.assertEqual(res.data[0]["id"], ingredients[0].id)

    def test_update_ingredient(self):
        """Test update ingredient API."""
        ingredients = Ingredient.objects.create(user=self.user, name="Green Onion")
        url = detail_url(ingredients.id)
        payload = {"name": "Onion"}
        res = self.client.patch(url, payload)
        ingredients.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], ingredients.name)
        self.assertEqual(ingredients.name, payload["name"])

    def test_delete_ingredient(self):
        """Test delete ingredient API."""
        ingredients = Ingredient.objects.create(user=self.user, name="Banana")
        url = detail_url(ingredients.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Ingredient.objects.filter(id=ingredients.id).exists())

    def test_filter_ingredients_assigned_to_recipes(self):
        """Test listing ingredients by those assigned to recipes."""
        in1 = Ingredient.objects.create(user=self.user, name="Noodles")
        in2 = Ingredient.objects.create(user=self.user, name="Beef")
        recipe = Recipe.objects.create(
            title="Beef Noodle", time_minutes=5, price=Decimal("5.99"), user=self.user
        )
        recipe.ingredient.add(in1)

        res = self.client.get(INGREDIRNT_URL, {"assigned_only": 1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """Test filtered ingredients returns a unique list."""
        ing = Ingredient.objects.create(user=self.user, name="Egg")
        Ingredient.objects.create(user=self.user, name="Lentils")
        recipe1 = Recipe.objects.create(
            user=self.user,
            title="Egg Benedict",
            time_minutes=20,
            price=Decimal("6.99"),
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title="Herb Egg",
            time_minutes=15,
            price=Decimal("7.99"),
        )
        recipe1.ingredient.add(ing)
        recipe2.ingredient.add(ing)

        res = self.client.get(INGREDIRNT_URL, {"assigned_only": 1})
        self.assertEqual(len(res.data), 1)
