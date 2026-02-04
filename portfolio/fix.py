from portfolio.models import Project, Category, Institution, ProjectMedia
from django.db import transaction

# Compteurs pour suivre la progression
projets_migres = 0
categories_migrees = 0
institutions_migrees = 0
media_migres = 0

with transaction.atomic():
    # ========== PROJETS ==========
    print("\n📦 Migration des projets...")
    for p in Project.objects.all():
        updated = False

        # Copier title vers title_fr et title_en
        if p.title and not p.title_fr:
            p.title_fr = p.title
            p.title_en = p.title  # Copie temporaire en attendant traduction
            updated = True

        # Copier description
        if p.description and not p.description_fr:
            p.description_fr = p.description
            p.description_en = p.description
            updated = True

        # Copier short_description
        if p.short_description and not p.short_description_fr:
            p.short_description_fr = p.short_description
            p.short_description_en = p.short_description
            updated = True

        # Copier technologies
        if p.technologies and not p.technologies_fr:
            p.technologies_fr = p.technologies
            p.technologies_en = p.technologies
            updated = True

        if updated:
            p.save()
            projets_migres += 1
            print(f"  ✅ {p.title[:50]}...")

    # ========== CATÉGORIES ==========
    print("\n📁 Migration des catégories...")
    for c in Category.objects.all():
        updated = False

        if c.name and not c.name_fr:
            c.name_fr = c.name
            c.name_en = c.name
            updated = True

        if c.description and not c.description_fr:
            c.description_fr = c.description
            c.description_en = c.description
            updated = True

        if updated:
            c.save()
            categories_migrees += 1
            print(f"  ✅ {c.name}")

    # ========== INSTITUTIONS ==========
    print("\n🏛️  Migration des institutions...")
    for i in Institution.objects.all():
        updated = False

        if i.name and not i.name_fr:
            i.name_fr = i.name
            i.name_en = i.name
            updated = True

        if updated:
            i.save()
            institutions_migrees += 1
            print(f"  ✅ {i.name}")

    # ========== MEDIA ==========
    print("\n🖼️  Migration des légendes média...")
    for m in ProjectMedia.objects.all():
        if m.caption and not m.caption_fr:
            m.caption_fr = m.caption
            m.caption_en = m.caption
            m.save()
            media_migres += 1
            print(f"  ✅ Média #{m.id}")

print("\n" + "=" * 50)
print("🎉 MIGRATION TERMINÉE !")
print("=" * 50)
print(f"📦 Projets migrés: {projets_migres}")
print(f"📁 Catégories migrées: {categories_migrees}")
print(f"🏛️  Institutions migrées: {institutions_migrees}")
print(f"🖼️  Médias migrés: {media_migres}")
print("\n✨ Vos données sont maintenant disponibles en FR et EN !")
print("💡 Les versions EN sont pour l'instant des copies - vous pouvez les traduire dans l'admin.")