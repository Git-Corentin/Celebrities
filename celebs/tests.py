import datetime
import json
import tempfile
from io import BytesIO
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from . import sync, wiki
from .models import Activity, Category, Celebrity, CelebritySighting

TMP_MEDIA = tempfile.mkdtemp()


def jpeg(w=900, h=600):
    buf = BytesIO()
    Image.new("RGB", (w, h), (30, 60, 200)).save(buf, "JPEG")
    return buf.getvalue()


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class BaseCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("nico", password="pw-test-123")
        self.cinema = Category.objects.get_or_create(name="Cinéma")[0]
        self.sport = Category.objects.get_or_create(name="Sport")[0]
        self.actor = Activity.objects.create(name="Acteur", category=self.cinema)
        self.foot = Activity.objects.create(name="Footballeur", category=self.sport)
        self.omar = Celebrity.objects.create(name="Omar Sy", popularity_score=500)
        self.omar.activities.add(self.actor)
        self.zizou = Celebrity.objects.create(name="Zinédine Zidane", popularity_score=900)
        self.zizou.activities.add(self.foot)
        CelebritySighting.objects.create(celebrity=self.omar, date_seen=datetime.date(2023, 5, 20), location="Cannes, Croisette")
        CelebritySighting.objects.create(celebrity=self.zizou, date_seen=datetime.date(2019, 1, 3), location="Paris, Gare de Lyon")

    def login(self):
        self.client.login(username="nico", password="pw-test-123")


class ListTests(BaseCase):
    def names(self, **params):
        r = self.client.get(reverse("celebrity_list"), params, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.status_code, 200)
        html = r.json()["results"]
        return [n for n in ("Omar Sy", "Zinédine Zidane") if n in html]

    def test_page_renders(self):
        r = self.client.get(reverse("celebrity_list"))
        self.assertContains(r, "Célébrités croisées")
        self.assertContains(r, 'name="csrf-token"')

    def test_filters(self):
        self.assertEqual(self.names(cat=self.cinema.id), ["Omar Sy"])
        self.assertEqual(self.names(act=self.foot.id), ["Zinédine Zidane"])
        self.assertEqual(self.names(loc="croisette"), ["Omar Sy"])
        self.assertEqual(self.names(loc="gare de lyon"), ["Zinédine Zidane"])
        self.assertEqual(self.names(year=2019), ["Zinédine Zidane"])
        self.assertEqual(self.names(**{"from": "2020-01-01"}), ["Omar Sy"])
        self.assertEqual(self.names(q="zinedine"), ["Zinédine Zidane"])  # sans accent
        self.assertEqual(self.names(q="footbal"), ["Zinédine Zidane"])  # par activité

    def test_sort_ids(self):
        r = self.client.get(reverse("celebrity_list"), {"sort": "-pop", "with_ids": 1}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.json()["ids"], [self.zizou.id, self.omar.id])
        for sort in ("name", "-name", "pop", "seen", "-seen", "-count", "act", "-act", "-added", "bogus"):
            self.assertEqual(self.client.get(reverse("celebrity_list"), {"sort": sort}).status_code, 200)

    def test_grid_view(self):
        r = self.client.get(reverse("celebrity_list"), {"view": "grid"})
        self.assertContains(r, 'class="grid"')

    def test_detail(self):
        r = self.client.get(reverse("celebrity_detail", args=[self.omar.id]))
        self.assertContains(r, "Cannes, Croisette")
        self.assertNotContains(r, "Modifier la fiche")  # visiteur anonyme


class AuthTests(BaseCase):
    def test_writes_require_login(self):
        protected = [
            ("get", reverse("add_celebrity")),
            ("get", reverse("celebrity_edit", args=[self.omar.id])),
            ("post", reverse("celebrity_delete", args=[self.omar.id])),
            ("post", reverse("delete_celebrity_sighting", args=[1])),
            ("post", reverse("update_popularity", args=[self.omar.id])),
            ("post", reverse("update_popularity_batch")),
            ("post", reverse("delete_activity", args=[self.actor.id])),
            ("post", reverse("git_sync")),
            ("get", reverse("image_suggestions")),
        ]
        for method, url in protected:
            r = getattr(self.client, method)(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn(reverse("celebs_login"), r["Location"], url)
        self.assertTrue(Celebrity.objects.filter(pk=self.omar.pk).exists())

    def test_anonymous_cannot_add_activity(self):
        self.client.post(reverse("activity_list"), {"name": "Pirate"})
        self.assertFalse(Activity.objects.filter(name="Pirate").exists())


@mock.patch("celebs.views.wiki.refresh_popularity", return_value=0)
class AddTests(BaseCase):
    def test_add_new_with_upload(self, _):
        self.login()
        r = self.client.post(reverse("add_celebrity"), {
            "name": "  Léa   Seydoux ",
            "activities": "Actrice, acteur",
            "image": SimpleUploadedFile("lea.jpg", jpeg(), content_type="image/jpeg"),
            "date_seen": "2024-05-14", "location": "Cannes", "notes": "",
        })
        lea = Celebrity.objects.get(name="Léa Seydoux")
        self.assertRedirects(r, lea.get_absolute_url(), fetch_redirect_response=False)
        self.assertEqual(lea.name_key, "lea seydoux")
        self.assertEqual(sorted(lea.activities.values_list("name", flat=True)), ["Acteur", "Actrice"])
        self.assertEqual(lea.sightings.count(), 1)
        self.assertTrue(lea.thumbnail)
        with Image.open(lea.thumbnail.path) as im:
            self.assertEqual(im.size, (240, 240))

    def test_add_sighting_to_existing(self, _):
        self.login()
        self.client.post(reverse("add_celebrity"), {
            "name": "omar sy", "existing_id": self.omar.id, "date_seen": "2025-01-01", "location": "Lyon",
        })
        self.assertEqual(Celebrity.objects.filter(name_key="omar sy").count(), 1)
        self.assertEqual(self.omar.sightings.count(), 2)

    def test_check_exists_accent_insensitive(self, _):
        r = self.client.get(reverse("check_celebrity_exists"), {"name": "ZINEDINE zidane"}).json()
        self.assertTrue(r["exists"])
        self.assertEqual(r["celebrity_id"], self.zizou.id)
        r = self.client.get(reverse("check_celebrity_exists"), {"name": "Zidane Junior"}).json()
        self.assertFalse(r["exists"])
        self.assertEqual(r["similar"][0]["name"], "Zinédine Zidane")

    def test_edit_replaces_activities_and_resets_wiki(self, _):
        self.login()
        self.omar.wiki_title_fr = "Omar Sy"
        self.omar.save()
        self.client.post(reverse("celebrity_edit", args=[self.omar.id]), {
            "name": "Omar Sy (acteur)", "activities": "Humoriste",
            "wikidata_id": "", "wiki_title_fr": "Omar Sy", "wiki_title_en": "",
        })
        self.omar.refresh_from_db()
        self.assertEqual(list(self.omar.activities.values_list("name", flat=True)), ["Humoriste"])
        # Le nom a changé et le titre n'a pas été retouché : on ré-identifiera la page.
        self.assertEqual(self.omar.wiki_title_fr, "")

    def test_image_url_must_be_wikimedia(self, _):
        self.login()
        r = self.client.post(reverse("celebrity_edit", args=[self.omar.id]), {
            "name": "Omar Sy", "image_url": "https://evil.example.com/x.jpg",
        })
        self.assertContains(r, "ne provient pas de Wikimedia")


class WikiTests(BaseCase):
    def test_resolve_prefers_humans(self):
        search = {"search": [{"id": "Q1"}, {"id": "Q2"}]}
        entities = {"entities": {
            "Q1": {"claims": {"P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q11424"}}}}]},
                   "sitelinks": {"frwiki": {"title": "Film"}}},
            "Q2": {"claims": {"P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q5"}}}}],
                              "P18": [{"mainsnak": {"datavalue": {"value": "Omar.jpg"}}}]},
                   "sitelinks": {"enwiki": {"title": "Omar Sy"}}, "descriptions": {"fr": {"value": "acteur"}}},
        }}
        with mock.patch.object(wiki, "_get", side_effect=[search, entities]):
            info = wiki.resolve("Omar Sy")
        self.assertEqual(info["id"], "Q2")
        self.assertEqual(info["en"], "Omar Sy")
        self.assertEqual(info["fr"], "")
        self.assertEqual(info["image"], "Omar.jpg")

    def test_refresh_sums_fr_and_en(self):
        info = {"id": "Q2", "fr": "", "en": "Omar Sy", "image": "", "description": ""}
        with mock.patch.object(wiki, "resolve", return_value=info), \
             mock.patch.object(wiki, "pageviews", side_effect=lambda proj, title: 0 if not title else 1234):
            score = wiki.refresh_popularity(self.omar)
        self.omar.refresh_from_db()
        self.assertEqual(score, 1234)
        self.assertEqual(self.omar.views_en, 1234)
        self.assertEqual(self.omar.wikidata_id, "Q2")
        self.assertIsNotNone(self.omar.popularity_updated_at)

    def test_network_error_keeps_old_score(self):
        import requests
        self.omar.wiki_title_fr = "Omar Sy"
        self.omar.save()
        with mock.patch.object(wiki, "pageviews", side_effect=requests.ConnectionError):
            res = wiki.refresh_many([self.omar])
        self.assertIsNone(res[self.omar.id])
        self.omar.refresh_from_db()
        self.assertEqual(self.omar.popularity_score, 500)

    def test_batch_endpoint(self):
        self.login()
        with mock.patch.object(wiki, "refresh_popularity", return_value=42):
            r = self.client.post(reverse("update_popularity_batch"), {"ids": [self.omar.id, self.zizou.id]})
        self.assertEqual(sorted(x["id"] for x in r.json()["results"]), sorted([self.omar.id, self.zizou.id]))

    def test_pageviews_url(self):
        resp = mock.Mock(status_code=200)
        resp.json.return_value = {"items": [{"views": 10}, {"views": 5}]}
        with mock.patch.object(wiki.session(), "get", return_value=resp) as get:
            self.assertEqual(wiki.pageviews("fr.wikipedia", "Zinédine Zidane"), 15)
        url = get.call_args[0][0]
        self.assertIn("/fr.wikipedia/all-access/user/Zin%C3%A9dine_Zidane/daily/", url)


class SyncTests(BaseCase):
    def test_export_import_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "celebs.json"
            _, changed, counts = sync.export_data(path)
            self.assertTrue(changed)
            self.assertEqual(counts["celebrity"], 2)
            _, changed_again, _ = sync.export_data(path)
            self.assertFalse(changed_again)  # pas de diff git inutile

            Celebrity.objects.all().delete()
            Activity.objects.create(name="Temporaire")
            sync.import_data(path)
            self.assertEqual(Celebrity.objects.count(), 2)
            self.assertFalse(Activity.objects.filter(name="Temporaire").exists())
            self.assertEqual(Celebrity.objects.get(name="Omar Sy").activities.get().name, "Acteur")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("Zinédine Zidane", path.read_text(encoding="utf-8"))  # UTF-8 lisible
            self.assertTrue(any(o["model"] == "celebs.celebritysighting" for o in data))
