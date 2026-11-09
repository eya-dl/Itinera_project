from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .config import CATEGORIES


class Profile(BaseModel):
    """Profil du voyageur. Le budget couvre les entrées des lieux, par personne, pour tout le séjour."""

    city: Optional[str] = None
    interests: dict[str, int] = Field(default_factory=dict, description="catégorie -> poids 0 à 5")
    budget_eur: Optional[float] = Field(default=None, gt=0)
    days: int = Field(default=3, ge=1, le=14)
    travelers: int = Field(default=1, ge=1, le=20)
    free_only: bool = False
    liked_place_ids: list[int] = Field(default_factory=list)

    @field_validator("interests")
    @classmethod
    def check_interests(cls, v):
        unknown = set(v) - set(CATEGORIES)
        if unknown:
            raise ValueError(f"catégories inconnues : {sorted(unknown)} (attendu : {CATEGORIES})")
        if any(not 0 <= w <= 5 for w in v.values()):
            raise ValueError("les poids d'intérêt doivent être compris entre 0 et 5")
        return v


class RecommendRequest(Profile):
    top_k: int = Field(default=10, ge=1, le=50)


class ItineraryRequest(Profile):
    city: str
    daily_minutes: int = Field(default=480, ge=120, le=720)
    start_hour: int = Field(default=9, ge=6, le=12)
