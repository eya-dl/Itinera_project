from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
PLACES_CSV = DATA_DIR / "place_features.csv"
RATINGS_TRAIN_CSV = DATA_DIR / "ratings_train.csv"

CATEGORIES = ["sea", "culture", "nature", "amusement", "shopping", "religious"]

CATEGORY_LABELS_FR = {
    "sea": "mer et plages",
    "culture": "culture",
    "nature": "nature",
    "amusement": "parcs de loisirs",
    "shopping": "shopping",
    "religious": "lieux de culte",
}

# Poids des composantes du score (renormalisés sur les composantes actives).
SCORE_WEIGHTS = {"interests": 0.40, "quality": 0.20, "budget": 0.15, "similarity": 0.25}

# Pénalité de diversité par lieu déjà sélectionné de la même catégorie.
DIVERSITY_PENALTY = 0.04
# Part de la note du lieu (catalogue) dans `quality` ; le reste vient des notes utilisateurs.
QUALITY_RATING_SHARE = 0.7

# Mélange de la composante « similarité avec les lieux aimés » (somme = 1).
# content = catégorie / ville / prix ; cf = filtrage collaboratif sur les notes utilisateurs.
SIMILARITY_MIX = {"content": 0.75, "cf": 0.15}

# Hypothèses d'itinéraire.
TRAVEL_SPEED_KMH = 25
HOP_OVERHEAD_MIN = 10
PAID_VISITS_PER_DAY = 3  # sert à répartir le budget d'entrées sur les jours
