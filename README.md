# Assistant de voyage intelligent

Application qui recommande des lieux à visiter et construit un itinéraire personnalisé selon les
intérêts du voyageur, son budget et la durée de son séjour, en expliquant chaque suggestion.
Données : dataset *Indonesia Tourism Destination* (437 lieux dans 5 villes : Jakarta, Yogyakarta, Bandung, Semarang, Surabaya).

```
Angular (frontend) ──► Spring Boot (backend) ──► FastAPI (ml-service)
   formulaire,            validation, historique,     recommandation,
   résultats              gestion d'erreurs, OpenAPI  itinéraire, explications
                                                              ▲
                                              data-science : nettoyage, preprocessing, évaluation
```

## Structure
| Dossier | Contenu |
|---|---|
| `data-science/` | Données brutes, notebook de nettoyage et preprocessing, tables propres, rapports |
| `ml-service/` | Service Python (FastAPI) : moteur de recommandation, itinéraires, évaluation hors ligne |
| `backend/` | API Spring Boot 3 / Java 21 : passerelle, validation, historique H2, Swagger |
| `frontend/` | Application Angular : formulaire de profil, recommandations, itinéraire |
| `docs/` | Architecture, contrat d'API, feuille de route |

## Démarrage

**Avec Docker** (un seul lancement) :
```bash
docker compose up --build
# interface : http://localhost:4200   API : http://localhost:8080/swagger-ui.html
```

**Sans Docker** (3 terminaux) :
```bash
cd ml-service && pip install -r requirements.txt && uvicorn app.main:app --port 8000
cd backend    && mvn spring-boot:run
cd frontend   && npm install && npm start      # http://localhost:4200
```

## État de validation
| Composant | État |
|---|---|
| `data-science` | Notebook exécuté de bout en bout, 6 tests passent |
| `ml-service` | 9 tests passent, service lancé et interrogé en HTTP |
| `frontend` | Compile sans erreur (`ng build`), **non testé dans un navigateur** |
| `backend` | **Non compilé ni testé** (pas d'accès à Maven Central lors de la génération) : lance `mvn test` en premier |
| `docker-compose` | **Non testé** |

## Limites connues
- Périmètre : 5 villes d'Indonésie. Pas de choix de destination à l'échelle mondiale.
- Pas de saison/météo, d'hébergement ni de transport dans les données (voir `docs/ROADMAP.md`).
- 53 % des durées de visite sont estimées (médiane de la catégorie) ; les prix en euros utilisent un taux approximatif (`IDR_PER_EUR`).
- Les notes utilisateurs n'ont pas de signal exploitable (voir `ml-service/reports/evaluation.md`) : la personnalisation repose sur le profil déclaré, pas sur l'historique.
- 2 lieux ont des coordonnées manifestement erronées ; ils sont signalés et exclus des itinéraires.
