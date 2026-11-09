from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException

from . import config
from .itinerary import build_itinerary
from .recommender import Recommender, UnknownCityError
from .schemas import ItineraryRequest, RecommendRequest

state = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    places = pd.read_csv(config.PLACES_CSV)
    ratings = pd.read_csv(config.RATINGS_TRAIN_CSV)
    state["rec"] = Recommender(places, ratings)
    yield
    state.clear()


app = FastAPI(title="Voyage AI — service de recommandation", version="0.1.0", lifespan=lifespan)


def rec() -> Recommender:
    return state["rec"]


@app.get("/health")
def health():
    return {"status": "ok", "places": len(rec().places)}


@app.get("/meta")
def meta():
    r = rec()
    return {
        "cities": r.cities,
        "categories": [{"key": k, "label": config.CATEGORY_LABELS_FR[k]} for k in config.CATEGORIES],
    }


@app.post("/recommend")
def recommend(req: RecommendRequest):
    try:
        items = rec().recommend(req, top_k=req.top_k)
    except UnknownCityError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"count": len(items), "items": items}


@app.post("/itinerary")
def itinerary(req: ItineraryRequest):
    try:
        return build_itinerary(rec(), req)
    except UnknownCityError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.get("/places/{place_id}")
def place(place_id: int):
    try:
        return {**rec().get_place(place_id), "similar": rec().similar_places(place_id)}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Lieu {place_id} introuvable")
