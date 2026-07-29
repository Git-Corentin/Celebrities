from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolio', '0006_copy_translation_data'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectmedia',
            name='media_type',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('image', 'Image'),
                    ('video', 'Vidéo'),
                    ('pdf', 'PDF'),
                    ('markdown', 'Markdown / README'),
                ],
                help_text='Type de fichier',
            ),
        ),
    ]