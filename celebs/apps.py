from django.apps import AppConfig


class CelebsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'celebs'
    verbose_name = "Carnet de célébrités"

    def ready(self):
        # Certains Linux déclarent .js en text/plain : le navigateur refuse alors
        # d'exécuter le script (en-tête « nosniff »). On force le bon type.
        import mimetypes
        mimetypes.add_type("text/javascript", ".js", True)
        mimetypes.add_type("text/css", ".css", True)
