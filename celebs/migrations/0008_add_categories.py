from django.db import migrations, models


def create_default_categories(apps, schema_editor):
    Category = apps.get_model('celebs', 'Category')
    default = [
        "Musique",
        "Sport",
        "Télévision",
        "Cinéma",
        "Cuisine",
        "Divers",
        "Politique",
    ]
    for name in default:
        Category.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ('celebs', '0007_remove_celebrity_date_seen_remove_celebrity_location_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='activity',
            name='category',
            field=models.ForeignKey(null=True, on_delete=models.deletion.SET_NULL, to='celebs.Category'),
        ),
        migrations.RunPython(create_default_categories),
    ]
