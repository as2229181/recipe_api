"""
Serializers for rescipes API view.
"""
from rest_framework import serializers

from core.models import Recipe

from django.contrib.auth import get_user_model


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer for recipes."""

    class Meta:
        model = Recipe
        fields = ["id", "title", "time_minutes", "price", "link"]
        read_only_fields = ["id"]
