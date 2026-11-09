# API

Backend (Spring Boot, port 8080), préfixe `/api`. JSON en `snake_case`. Documentation interactive : `/swagger-ui.html`.

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/meta` | Villes et catégories disponibles |
| POST | `/api/recommendations` | Lieux recommandés, avec scores et explications |
| POST | `/api/itineraries` | Itinéraire jour par jour (ville obligatoire) |
| GET | `/api/places/{id}` | Détail d'un lieu et lieux similaires |
| GET | `/api/history` | 20 dernières demandes |

## Profil (corps des POST)
| Champ | Type | Défaut | Règle |
|---|---|---|---|
| `city` | texte | toutes (recommandations) | obligatoire pour l'itinéraire |
| `interests` | objet catégorie → 0..5 | `{}` | catégories : `sea`, `culture`, `nature`, `amusement`, `shopping`, `religious` |
| `budget_eur` | nombre > 0 | aucun | budget d'entrées par personne pour tout le séjour |
| `days` | 1..14 | 3 | |
| `travelers` | 1..20 | 1 | |
| `free_only` | booléen | false | |
| `liked_place_ids` | liste d'entiers | `[]` | active la similarité |
| `top_k` | 1..50 | 10 | recommandations uniquement |
| `daily_minutes` | 120..720 | 480 | itinéraire uniquement |
| `start_hour` | 6..12 | 9 | itinéraire uniquement |

## Exemple
```bash
curl -X POST localhost:8080/api/recommendations -H 'content-type: application/json' \
  -d '{"city":"Bandung","interests":{"nature":5},"budget_eur":10,"days":2,"top_k":1}'
```
```json
{ "count": 1, "items": [ {
  "place_id": 323, "name": "Kebun Tanaman Obat Sari Alam", "city": "Bandung",
  "category": "nature", "category_label": "nature", "price_eur": 0.0, "is_free": true,
  "visit_minutes": 90, "rating": 4.9, "score": 0.949,
  "breakdown": { "interests": 1.0, "quality": 0.825, "budget": 1.0 },
  "reasons": ["Correspond à ton intérêt pour « nature » (5/5).", "Entrée gratuite.",
              "Visite d'environ 90 min.", "Très bien noté (4.9/5)."]
} ] }
```
Les descriptions des lieux restent en indonésien (langue de la source).

## Erreurs
| Statut | `error` | Cause |
|---|---|---|
| 400 | `validation` | champ hors limites (`fields` détaille lesquels) |
| 404 / 422 | `ml_service` | lieu introuvable, ville inconnue (message dans `detail`) |
| 502 | `ml_service_failure` | erreur interne du service Python |
| 503 | `ml_service_unavailable` | service Python injoignable |

Service Python (port 8000, interne) : mêmes routes sans préfixe `/api` (`/recommend`, `/itinerary`, `/meta`, `/places/{id}`, `/health`).
