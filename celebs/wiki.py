"""
Tout ce qui parle aux API Wikimedia : identification d'une personne (Wikidata),
popularité (vues Wikipédia fr + en) et suggestions de photos (Commons).

Pourquoi Wikimedia plutôt que Google Images ?
- gratuit, sans clé, autorisé depuis PythonAnywhere (compte gratuit inclus) ;
- l'API Google « Custom Search » est fermée aux nouveaux clients ;
- les photos Commons sont sous licence libre, donc réutilisables sans souci.
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from urllib.parse import quote, urlparse

import requests
from django.conf import settings
from django.utils import timezone

log = logging.getLogger(__name__)

TIMEOUT = 8
WINDOW_DAYS = 60
HUMAN = "Q5"
IMAGE_HOSTS = {"upload.wikimedia.org"}

_session = None


def session():
    global _session
    if _session is None:
        s = requests.Session()
        s.headers["User-Agent"] = settings.CELEBS_WIKI_USER_AGENT
        adapter = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=16, max_retries=1)
        s.mount("https://", adapter)
        _session = s
    return _session


def _get(url, **params):
    params.setdefault("format", "json")
    r = session().get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


# ─────────────────────────── Identification ───────────────────────────

def _claim_ids(entity, prop):
    out = []
    for claim in entity.get("claims", {}).get(prop, []):
        value = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(value, dict) and "id" in value:
            out.append(value["id"])
        elif isinstance(value, str):
            out.append(value)
    return out


def _entities(ids):
    if not ids:
        return {}
    data = _get(
        "https://www.wikidata.org/w/api.php",
        action="wbgetentities", ids="|".join(ids), props="claims|sitelinks|descriptions",
        sitefilter="frwiki|enwiki", languages="fr|en",
    )
    return data.get("entities", {})


def resolve(name, wikidata_id=""):
    """
    Trouve la fiche Wikidata d'une personne.
    Renvoie {"id", "fr", "en", "image", "description"} ou None.
    On privilégie les humains (P31 = Q5) qui ont un article fr ou en.
    """
    try:
        if wikidata_id:
            ids = [wikidata_id]
        else:
            ids = []
            for lang in ("fr", "en"):
                found = _get(
                    "https://www.wikidata.org/w/api.php",
                    action="wbsearchentities", search=name, language=lang, uselang=lang,
                    type="item", limit=6,
                ).get("search", [])
                ids += [hit["id"] for hit in found if hit["id"] not in ids]
                if ids:
                    break
        entities = _entities(ids[:8])
    except requests.RequestException as exc:
        log.warning("Wikidata indisponible pour %s : %s", name, exc)
        return None

    def score(qid):
        e = entities.get(qid, {})
        links = e.get("sitelinks", {})
        return (
            HUMAN in _claim_ids(e, "P31"),
            "frwiki" in links or "enwiki" in links,
            -ids.index(qid) if qid in ids else 0,
        )

    candidates = [q for q in ids if q in entities and "missing" not in entities[q]]
    if not candidates:
        return None
    best = max(candidates, key=score)
    e = entities[best]
    if not wikidata_id and not any(score(best)[:2]):
        return None
    links = e.get("sitelinks", {})
    desc = e.get("descriptions", {})
    images = _claim_ids(e, "P18")
    return {
        "id": best,
        "fr": links.get("frwiki", {}).get("title", ""),
        "en": links.get("enwiki", {}).get("title", ""),
        "image": images[0] if images else "",
        "description": (desc.get("fr") or desc.get("en") or {}).get("value", ""),
    }


# ─────────────────────────── Popularité ───────────────────────────

def pageviews(project, title, days=WINDOW_DAYS):
    """Somme des vues quotidiennes d'un article sur les `days` derniers jours."""
    if not title:
        return 0
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=days - 1)
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{project}/all-access/user/{quote(title.replace(' ', '_'), safe='')}/daily/"
        f"{start:%Y%m%d}00/{end:%Y%m%d}00"
    )
    try:
        r = session().get(url, timeout=TIMEOUT)
        if r.status_code == 404:
            return 0
        r.raise_for_status()
        return sum(item.get("views", 0) for item in r.json().get("items", []))
    except requests.RequestException as exc:
        log.warning("Pageviews %s/%s : %s", project, title, exc)
        raise


def refresh_popularity(celeb, save=True):
    """
    Met à jour la popularité d'une célébrité.
    1. identifie la personne sur Wikidata (une seule fois, puis mémorisé) ;
    2. additionne les vues des articles fr ET en sur 60 jours.
    Un nom sans article français mais avec un article anglais n'est donc plus à 0.
    """
    if not (celeb.wiki_title_fr or celeb.wiki_title_en):
        info = resolve(celeb.name, celeb.wikidata_id)
        if info:
            celeb.wikidata_id = info["id"]
            celeb.wiki_title_fr = info["fr"]
            celeb.wiki_title_en = info["en"]
        else:
            # Dernière chance : un article qui porte exactement ce nom.
            celeb.wiki_title_fr = celeb.name
            celeb.wiki_title_en = celeb.name

    fr = pageviews("fr.wikipedia", celeb.wiki_title_fr)
    en = pageviews("en.wikipedia", celeb.wiki_title_en)
    # Si le titre deviné n'existe pas, on l'oublie pour ne pas afficher de faux lien.
    if not celeb.wikidata_id:
        if not fr:
            celeb.wiki_title_fr = ""
        if not en:
            celeb.wiki_title_en = ""

    celeb.views_fr, celeb.views_en = fr, en
    celeb.popularity_score = fr + en
    celeb.popularity_updated_at = timezone.now()
    if save:
        celeb.save(update_fields=[
            "views_fr", "views_en", "popularity_score", "popularity_updated_at",
            "wikidata_id", "wiki_title_fr", "wiki_title_en",
        ])
    return celeb.popularity_score


def refresh_many(celebs, workers=4):
    """Rafraîchit plusieurs célébrités en parallèle. Renvoie {id: score | None}."""
    def one(c):
        try:
            return c.pk, refresh_popularity(c)
        except Exception as exc:  # une erreur ne doit pas bloquer les autres
            log.warning("Popularité %s : %s", c.name, exc)
            return c.pk, None

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(one, celebs))


# ─────────────────────────── Photos ───────────────────────────

def _commons_files(titles, width):
    if not titles:
        return []
    data = _get(
        "https://commons.wikimedia.org/w/api.php",
        action="query", titles="|".join(titles), prop="imageinfo",
        iiprop="url|mime|extmetadata", iiurlwidth=width, iiextmetadatafilter="Artist|LicenseShortName",
    )
    return _imageinfo(data)


def _imageinfo(data):
    out = []
    pages = data.get("query", {}).get("pages", {})
    for page in sorted(pages.values(), key=lambda p: p.get("index", 0)):
        info = (page.get("imageinfo") or [{}])[0]
        if not info.get("thumburl") or not str(info.get("mime", "")).startswith("image/"):
            continue
        if info.get("mime") in ("image/svg+xml", "image/gif", "image/tiff"):
            continue
        meta = info.get("extmetadata", {})
        out.append({
            "thumb": info["thumburl"],
            "url": info["thumburl"],
            "page": info.get("descriptionurl", ""),
            "license": meta.get("LicenseShortName", {}).get("value", ""),
            "source": "Wikimedia Commons",
        })
    return out


def image_suggestions(name, limit=10, width=640):
    """Photos candidates pour un nom : image Wikidata, image de l'article, puis recherche Commons."""
    results, seen = [], set()

    def add(items, source=None):
        for it in items:
            if it["url"] in seen:
                continue
            seen.add(it["url"])
            if source:
                it["source"] = source
            results.append(it)

    info = None
    try:
        info = resolve(name)
    except Exception:
        pass
    try:
        if info and info.get("image"):
            add(_commons_files(["File:" + info["image"]], width), "Wikidata")
    except requests.RequestException:
        pass
    try:
        data = _get(
            "https://commons.wikimedia.org/w/api.php",
            action="query", generator="search", gsrsearch=f'"{name}" filetype:bitmap',
            gsrnamespace=6, gsrlimit=limit, prop="imageinfo",
            iiprop="url|mime|extmetadata", iiurlwidth=width, iiextmetadatafilter="Artist|LicenseShortName",
        )
        add(_imageinfo(data))
    except requests.RequestException:
        pass
    return {
        "results": results[:limit],
        "wikidata": info["id"] if info else "",
        "description": info["description"] if info else "",
    }


def is_allowed_image_url(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme == "https" and parsed.hostname in IMAGE_HOSTS


def download_image(url, max_bytes=8 * 1024 * 1024):
    """Télécharge une photo choisie parmi les suggestions (hôtes Wikimedia uniquement)."""
    if not is_allowed_image_url(url):
        raise ValueError("Adresse d'image non autorisée.")
    r = session().get(url, timeout=15, stream=True)
    r.raise_for_status()
    chunks, size = [], 0
    for chunk in r.iter_content(64 * 1024):
        size += len(chunk)
        if size > max_bytes:
            raise ValueError("Image trop lourde.")
        chunks.append(chunk)
    return b"".join(chunks)
