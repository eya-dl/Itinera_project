// Types alignés sur le JSON de l'API (snake_case), identique côté Spring Boot et service Python.

export interface Category {
  key: string;
  label: string;
}

export interface Meta {
  cities: string[];
  categories: Category[];
}

export interface ProfilePayload {
  city?: string;
  interests: Record<string, number>;
  budget_eur?: number;
  days: number;
  travelers: number;
  free_only: boolean;
}

export interface RecommendRequest extends ProfilePayload {
  top_k?: number;
}

export interface ItineraryRequest extends ProfilePayload {
  city: string;
  daily_minutes?: number;
  start_hour?: number;
}

export interface Place {
  place_id: number;
  name: string;
  city: string;
  category: string;
  category_label: string;
  description: string;
  price_idr: number;
  price_eur: number;
  is_free: boolean;
  visit_minutes: number;
  duration_estimated: boolean;
  rating: number;
  lat: number;
  lon: number;
  coords_suspect: boolean;
  score: number;
  breakdown: Record<string, number>;
  reasons: string[];
}

export interface RecommendResponse {
  count: number;
  items: Place[];
}

export interface Stop extends Place {
  travel_minutes: number;
  travel_km: number;
  start_time: string;
  end_time: string;
}

export interface DayPlan {
  day: number;
  stops: Stop[];
  total_minutes: number;
  distance_km: number;
  cost_eur: number;
  summary: string;
}

export interface Totals {
  places: number;
  cost_per_person_eur: number;
  cost_group_eur: number;
  budget_eur: number | null;
  within_budget: boolean;
  distance_km: number;
}

export interface Itinerary {
  city: string;
  days: DayPlan[];
  totals: Totals;
  warnings: string[];
}
