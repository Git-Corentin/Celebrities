from django.db import migrations, models
import unicodedata


def _normalize(text):
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())


def fill_name_key(apps, schema_editor):
    Celebrity = apps.get_model("celebs", "Celebrity")
    for c in Celebrity.objects.all().only("id", "name"):
        Celebrity.objects.filter(pk=c.pk).update(name_key=_normalize(c.name))


class Migration(migrations.Migration):

    dependencies = [
        ("celebs", "0009_alter_category_id"),
    ]

    operations = [
        migrations.AlterModelOptions(name="category", options={"ordering": ["name"], "verbose_name": "secteur"}),
        migrations.AlterModelOptions(name="activity", options={"ordering": ["name"], "verbose_name": "activité"}),
        migrations.AlterModelOptions(name="celebrity", options={"ordering": ["name_key"], "verbose_name": "célébrité"}),
        migrations.AlterModelOptions(name="celebritysighting", options={"ordering": ["-date_seen", "-id"], "verbose_name": "rencontre"}),
        migrations.AlterField(
            model_name="activity",
            name="category",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, to="celebs.category"),
        ),
        migrations.AlterField(
            model_name="celebrity",
            name="activities",
            field=models.ManyToManyField(blank=True, related_name="celebrities", to="celebs.activity"),
        ),
        migrations.AlterField(
            model_name="celebrity",
            name="name",
            field=models.CharField(db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name="celebrity",
            name="name_key",
            field=models.CharField(blank=True, db_index=True, editable=False, max_length=255, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="celebrity",
            name="thumbnail",
            field=models.ImageField(blank=True, editable=False, null=True, upload_to="celebs/thumbs/"),
        ),
        migrations.AddField(model_name="celebrity", name="views_fr", field=models.PositiveIntegerField(default=0, editable=False)),
        migrations.AddField(model_name="celebrity", name="views_en", field=models.PositiveIntegerField(default=0, editable=False)),
        migrations.AddField(
            model_name="celebrity",
            name="popularity_updated_at",
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="celebrity",
            name="wikidata_id",
            field=models.CharField(blank=True, max_length=20, verbose_name="Wikidata (Qxxx)", default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="celebrity",
            name="wiki_title_fr",
            field=models.CharField(blank=True, max_length=255, verbose_name="Titre Wikipédia FR", default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="celebrity",
            name="wiki_title_en",
            field=models.CharField(blank=True, max_length=255, verbose_name="Titre Wikipédia EN", default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="celebrity",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="celebritysighting",
            name="date_seen",
            field=models.DateField(blank=True, null=True, verbose_name="date"),
        ),
        migrations.AlterField(
            model_name="celebritysighting",
            name="location",
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name="lieu"),
        ),
        migrations.RunPython(fill_name_key, migrations.RunPython.noop),
    ]
