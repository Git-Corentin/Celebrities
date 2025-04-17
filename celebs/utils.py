import requests
from datetime import datetime, timedelta


def get_wikipedia_popularity(name):
    """Récupère le nombre de vues Wikipédia sur les 2 derniers mois."""
    user_agent = "MyCelebrityApp/1.0 (contact@myapp.com)"
    base_url = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/fr.wikipedia/all-access/all-agents/{}/daily/{}/{}"

    headers = {"User-Agent": user_agent}

    # Déterminer les périodes (mois actuel et précédent)
    today = datetime.today()
    last_month = today - timedelta(days=30)

    current_period = today.strftime("%Y%m01")
    last_period = last_month.strftime("%Y%m01")

    total_views = 0

    for period in [last_period, current_period]:
        url = base_url.format(name, period, period)
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if "items" in data and len(data["items"]) > 0:
                total_views += data["items"][0]["views"]

        except requests.exceptions.RequestException as e:
            print(f"Erreur API Wikipédia pour {name}: {e}")

    return total_views
