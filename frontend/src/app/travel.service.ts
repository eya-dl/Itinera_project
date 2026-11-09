import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Itinerary, ItineraryRequest, Meta, RecommendRequest, RecommendResponse } from './models';

/** Appels à l'API Spring Boot (/api est redirigé par proxy.conf.json en dev, par nginx en Docker). */
@Injectable({ providedIn: 'root' })
export class TravelService {
  private readonly http = inject(HttpClient);

  meta() {
    return this.http.get<Meta>('/api/meta');
  }

  recommend(request: RecommendRequest) {
    return this.http.post<RecommendResponse>('/api/recommendations', request);
  }

  itinerary(request: ItineraryRequest) {
    return this.http.post<Itinerary>('/api/itineraries', request);
  }
}
