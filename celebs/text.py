import unicodedata


def normalize(text):
    """'Émile Zola ' -> 'emile zola' : minuscules, sans accents, espaces réduits."""
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.lower().split())
