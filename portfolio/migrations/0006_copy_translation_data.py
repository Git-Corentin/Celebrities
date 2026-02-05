# portfolio/migrations/0006_copy_translation_data.py
from django.db import migrations


def copy_to_translated_fields(apps, schema_editor):
    """Copie les données des champs originaux vers les champs _fr et _en"""

    Project = apps.get_model('portfolio', 'Project')
    Category = apps.get_model('portfolio', 'Category')
    Institution = apps.get_model('portfolio', 'Institution')
    ProjectMedia = apps.get_model('portfolio', 'ProjectMedia')

    print("\n" + "=" * 60)
    print("🔄 Migration des données vers champs traduits...")
    print("=" * 60)

    # PROJETS
    print("\n📦 Projets...")
    for project in Project.objects.all():
        project.title_fr = project.title
        project.title_en = project.title  # Copie temporaire
        project.description_fr = project.description
        project.description_en = project.description
        project.short_description_fr = project.short_description
        project.short_description_en = project.short_description
        project.technologies_fr = project.technologies
        project.technologies_en = project.technologies
        project.save()
        print(f"  ✅ {project.title[:50]}")

    # CATÉGORIES
    print("\n📁 Catégories...")
    for category in Category.objects.all():
        category.name_fr = category.name
        category.name_en = category.name
        if category.description:
            category.description_fr = category.description
            category.description_en = category.description
        category.save()
        print(f"  ✅ {category.name}")

    # INSTITUTIONS
    print("\n🏛️  Institutions...")
    for institution in Institution.objects.all():
        institution.name_fr = institution.name
        institution.name_en = institution.name
        institution.save()
        print(f"  ✅ {institution.name}")

    # MEDIA
    print("\n🖼️  Médias...")
    for media in ProjectMedia.objects.all():
        if media.caption:
            media.caption_fr = media.caption
            media.caption_en = media.caption
            media.save()
            print(f"  ✅ Média #{media.id}")

    print("\n" + "=" * 60)
    print("🎉 Migration terminée avec succès !")
    print("=" * 60 + "\n")


def reverse_copy(apps, schema_editor):
    """En cas de rollback, ne rien faire (les données originales existent toujours)"""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('portfolio', '0005_category_description_en_category_description_fr_and_more'),
    ]

    operations = [
        migrations.RunPython(copy_to_translated_fields, reverse_copy),
    ]