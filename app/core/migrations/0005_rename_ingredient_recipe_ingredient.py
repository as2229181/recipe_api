# Generated by Django 3.2.20 on 2023-08-07 14:55

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_auto_20230803_1355"),
    ]

    operations = [
        migrations.RenameField(
            model_name="recipe",
            old_name="Ingredient",
            new_name="ingredient",
        ),
    ]