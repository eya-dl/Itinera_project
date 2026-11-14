# Itinera — Explainable Travel Recommender & Itinerary Planner

> Tell Itinera what you like, your budget and how many days you have: it ranks the places worth visiting, **explains every suggestion**, and builds a day-by-day itinerary that fits your time and money.

![Angular](https://img.shields.io/badge/Angular-frontend-DD0031?logo=angular&logoColor=white)
![Spring Boot](https://img.shields.io/badge/Spring%20Boot%203-Java%2021-6DB33F?logo=springboot&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-ML%20service-009688?logo=fastapi&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-data%20science-150458?logo=pandas&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-compose-2496ED?logo=docker&logoColor=white)

Data: *Indonesia Tourism Destination* dataset — 437 places across Jakarta, Yogyakarta, Bandung, Semarang and Surabaya.

## Features

- **Personalised ranking** from a declared profile (interests per category, budget, trip length, places already liked).
- **Transparent score** — each place gets `Σ weight × component` over interests, quality (Bayesian-smoothed ratings), budget fit and similarity to liked places; a diversity penalty avoids five museums in a row.
- **Explanations generated from the score**, never invented ("matches your interest in culture", "free entry", "similar to a place you liked").
- **Itinerary builder** — greedy day planner that trades distance against score, respects a daily time window (visit + travel time) and the total budget, and reports schedules, costs, distances and warnings.
- **Honest evaluation** — offline benchmark of rating prediction and top-10 ranking showed the dataset's ratings carry no usable individual signal, which is why personalisation relies on the declared profile rather than collaborative filtering ([report](ml-service/reports/evaluation.md)).

## Architecture

```mermaid
flowchart LR
  U[Traveller] --> F[Angular UI]
  F -->|/api| B[Spring Boot gateway<br/>validation · history · OpenAPI]
  B -->|JSON| M[FastAPI ml-service<br/>scoring · itinerary · explanations]
  B --> H[(H2 history)]
  M --> D[(cleaned CSV tables)]
  DS[data-science notebook<br/>cleaning · preprocessing] --> D
```

The Java backend owns validation, history and error handling (clear 400 / 422 / 502 / 503 responses); all the intelligence lives in a separate Python service, so the model can evolve (embeddings, LLM) without touching the backend. Details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/API.md](docs/API.md).

<p align="center"><img src="data-science/reports/carte_lieux.png" width="70%"></p>

## Getting started

```bash
git clone https://github.com/eya-dl/Itinera_project.git
cd Itinera_project
docker compose up --build
# UI: http://localhost:4200    API docs: http://localhost:8080/swagger-ui.html
```

Without Docker (three terminals):

```bash
cd ml-service && pip install -r requirements.txt && uvicorn app.main:app --port 8000
cd backend    && mvn spring-boot:run
cd frontend   && npm install && npm start
```

## Project structure

| Folder | Content |
|---|---|
| `data-science/` | raw data, cleaning & preprocessing notebook, clean tables, data report, tests |
| `ml-service/` | FastAPI service: recommender, itinerary planner, offline evaluation, tests |
| `backend/` | Spring Boot 3 / Java 21 gateway: validation, H2 history, Swagger |
| `frontend/` | Angular app: profile form, recommendation cards, itinerary view |
| `docs/` | architecture, API contract, roadmap |

Tests: `pytest` in `data-science/` and `ml-service/`, `mvn test` in `backend/`.

## Limitations & roadmap

- Scope is five Indonesian cities; no season/weather, accommodation or transport data yet.
- Travel times use straight-line distance at an average speed; opening hours are not modelled.
- 53 % of visit durations are imputed from the category median.
- Next steps: real routing, semantic search over place descriptions, user study ([ROADMAP](docs/ROADMAP.md)).

## Author

**Eya Dhambri** — AI engineering student at ENSI (Tunisia) · [LinkedIn](https://www.linkedin.com/in/eya-dhambri) · eya.dhambri@ensi-uma.tn
