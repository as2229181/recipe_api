"""
Tests for recipe APIs.
"""
from decimal import Decimal

import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPES_URL = reverse("recipe:recipe-list")


def detail_url(recipe_id):
    """Create and return a recipe detai url."""
    return reverse("recipe:recipe-detail", args=[recipe_id])


def image_upload_url(recipe_id):
    """Create and return an image upload URL."""
    return reverse("recipe:recipe-upload-image", args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        "title": "sample title",
        "time_minutes": 22,
        "price": Decimal(22.99),
        "description": "Sample description",
        "link": "http://example.com.recipe.pdf",
    }
    defaults.update(params)
    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a new user."""
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Test unautheticated APU requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="user@example.com", password="testpass123")
        self.client.force_authenticate(self.user)

    def test_retrive_recipes(self):
        """Test retrieving a list of recipes."""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by("-id")
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user."""
        other_user = create_user(email="other@example.com", password="otherpassword123")

        create_recipe(user=self.user)
        create_recipe(user=other_user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail ."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.data, serializer.data)

    def test_creatie_recipe(self):
        """Test creating a recipe"""
        payload = {"title": "Sample test", "time_minutes": 30, "price": Decimal("5.99")}
        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(
            res.status_code, status.HTTP_201_CREATED
        )  # /api/recipes/recipe
        recipe = Recipe.objects.get(id=res.data["id"])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update."""
        original_link = "https://example.com/recipe.pdf"
        recipe = create_recipe(
            user=self.user,
            title="sample recipe title",
            link=original_link,
        )

        payload = {"title": "New recipe title"}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload["title"])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """Test full uodate of recipe."""
        recipe = create_recipe(
            user=self.user,
            title="Sample title",
            link="https://example.com/recipe.pdf",
            description="Sample recipe description",
        )

        payload = {
            "title": "New recipe title",
            "link": "https://new_example.com/recipe.pdf",
            "description": "New sample recipe descriptrion",
            "time_minutes": 10,
            "price": Decimal("2.50"),
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_update_user_return_error(self):
        """Test changing the recipe user results in an error."""
        new_user = create_user(email="user2@example.com", password="test123")
        recipe = create_recipe(user=self.user)

        payload = {"user": new_user.id}
        url = detail_url(recipe.id)

        self.client.patch(url, payload)
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe successful."""
        recipe = create_recipe(user=self.user)
        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_recipe_other_user_recipe_error(self):
        """Test trying to delete another users recipe gives error."""
        new_user = create_user(email="user2@example.com", password="test123")
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_tag(self):
        payload = {
            "title": "Sample test",
            "time_minutes": 30,
            "price": Decimal("5.99"),
            "tag": [{"name": "Thai"}, {"name": "Dinner"}],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tag.count(), 2)
        for tag in payload["tag"]:
            exists = recipe.tag.filter(name=tag["name"], user=self.user).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Test creating a recipe with existing tag."""
        tag_Indian = Tag.objects.create(user=self.user, name="Indian")
        payload = {
            "title": "Pongal",
            "time_minutes": 60,
            "price": Decimal("4.50"),
            "tag": [{"name": "Indian"}, {"name": "Breakfast"}],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tag.count(), 2)
        self.assertIn(tag_Indian, recipe.tag.all())
        for tag in payload["tag"]:
            exists = recipe.tag.filter(name=tag["name"], user=self.user).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating tag when updating a recipe"""
        recipe = create_recipe(user=self.user)

        payload = {"tag": [{"name": "Lunch"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name="Lunch")
        self.assertIn(new_tag, recipe.tag.all())

    def test_update_recipe_assign_tag(self):
        """Test assigning an existing tag when updating a recipe."""
        tag_breakfast = Tag.objects.create(user=self.user, name="Breakfast")
        recipe = create_recipe(user=self.user)
        recipe.tag.add(tag_breakfast)
        tag_lunch = Tag.objects.create(user=self.user, name="Launch")

        payload = {"tag": [{"name": "Launch"}]}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertIn(tag_lunch, recipe.tag.all())
        self.assertNotIn(tag_breakfast, recipe.tag.all())

    def test_clear_recipe_tags(self):
        """Test clear a recipe tags."""
        tag = Tag.objects.create(user=self.user, name="Dessert")
        recipe = create_recipe(user=self.user)
        recipe.tag.add(tag)
        payload = {"tag": []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")
        recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(tag, recipe.tag.all())
        self.assertEqual(recipe.tag.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test create recipe with new ingredients."""
        payload = {
            "title": "Cauliflower Tacos",
            "time_minutes": 60,
            "price": Decimal("4.30"),
            "ingredient": [{"name": "Cauliflower"}, {"name": "Salt"}],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipes[0].ingredient.count(), 2)
        for ingredient in payload["ingredient"]:
            exist = Ingredient.objects.filter(
                user=self.user, name=ingredient["name"]
            ).exists()
            self.assertTrue(exist)

    def test_create_recipe_with_ingredient(self):
        """Test creating a new recipe with existing ingredient"""
        ingredient_noodles = Ingredient.objects.create(user=self.user, name="Noodles")
        payload = {
            "title": "Radman",
            "time_minutes": 50,
            "price": Decimal("20.99"),
            "ingredient": [{"name": "Egg"}, {"name": "Noodles"}],
        }
        res = self.client.post(RECIPES_URL, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipes[0].ingredient.count(), 2)
        self.assertIn(ingredient_noodles, recipes[0].ingredient.all())
        for ingredient in payload["ingredient"]:
            exist = Ingredient.objects.filter(
                user=self.user, name=ingredient["name"]
            ).exists()
            self.assertTrue(exist)

    def test_create_ingredient_on_update(self):
        """Test create ingredient_when_update_recipe."""
        recipe = create_recipe(user=self.user)
        payload = {"ingredient": [{"name": "Salt"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        print(recipe.ingredient.first().name)
        self.assertEqual(
            recipe.ingredient.first().name, payload["ingredient"][0]["name"]
        )
        new_ingredient = Ingredient.objects.get(user=self.user, name="Salt")
        self.assertIn(new_ingredient, recipe.ingredient.all())

    def test_update_recipe_assign_ingredient(self):
        """Test assigning an existing ingredient when updating a recipe"""
        ingredient1 = Ingredient.objects.create(user=self.user, name="Peper")
        recipe = create_recipe(user=self.user)
        recipe.ingredient.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name="Cinnamon")
        payload = {"ingredient": [{"name": "Cinnamon"}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(ingredient1, recipe.ingredient.all())
        self.assertIn(ingredient2, recipe.ingredient.all())

    def test_clear_recipe_ingrendient(self):
        """Test clearing a recipe ingredients"""
        ingredient = Ingredient.objects.create(user=self.user, name="Rice")
        recipe = create_recipe(user=self.user)
        recipe.ingredient.add(ingredient)
        payload = {"ingredient": []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredient.count(), 0)
        self.assertNotIn(ingredient, recipe.ingredient.all())

    def test_filter_by_tags(self):
        """Test filtering  recipes by tags."""
        r1 = create_recipe(user=self.user, title="Chinese Vagetable Dish")
        r2 = create_recipe(user=self.user, title="Japanese Vagetable Dish")
        tag1 = Tag.objects.create(user=self.user, name="Vegan")
        tag2 = Tag.objects.create(user=self.user, name="Vegetarian")
        r1.tag.add(tag1)
        r2.tag.add(tag2)
        r3 = create_recipe(user=self.user, title="American Food")

        params = {"tags": f"{tag1.id},{tag2.id}"}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """Test filtering recipes by ingredients."""
        r1 = create_recipe(user=self.user, title="Beef Noodle")
        r2 = create_recipe(user=self.user, title="Onion Soup")
        in1 = Ingredient.objects.create(user=self.user, name="Beef")
        in2 = Ingredient.objects.create(user=self.user, name="Onion")
        r1.ingredient.add(in1)
        r2.ingredient.add(in2)
        r3 = create_recipe(user=self.user, title="Red Bean Soup")
        params = {"ingredients": f"{in1.id},{in2.id}"}
        res = self.client.get(RECIPES_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)

        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTests(TestCase):
    """Tests for the image upload API."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email="user@example", password="password123")
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as image_file:
            img = Image.new("RGB", (10, 10))
            img.save(image_file, format="JPEG")
            image_file.seek(0)
            payload = {"image": image_file}
            res = self.client.post(url, payload, format="multipart")
        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))
