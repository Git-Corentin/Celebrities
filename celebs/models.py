from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.name
class Activity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        if not self.name.strip():  # Vérifie si le nom de l'activité est vide
            raise ValueError("Le nom de l'activité ne peut pas être vide.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
class Celebrity(models.Model):
    name = models.CharField(max_length=255)
    popularity_score = models.FloatField(default=0)
    image = models.ImageField(upload_to="celebs/", blank=True, null=True)
    activities = models.ManyToManyField(Activity, blank=False)

    def __str__(self):
        return self.name

class CelebritySighting(models.Model):
    celebrity = models.ForeignKey(Celebrity, on_delete=models.CASCADE, related_name='sightings')
    date_seen = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.celebrity.name} seen on {self.date_seen} at {self.location}"

