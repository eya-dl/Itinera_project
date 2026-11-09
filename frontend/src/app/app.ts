import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ItineraryView } from './itinerary-view';
import { Itinerary, Meta, Place, ProfilePayload } from './models';
import { PlaceCard } from './place-card';
import { TravelService } from './travel.service';

@Component({
  selector: 'app-root',
  imports: [ReactiveFormsModule, PlaceCard, ItineraryView],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly fb = inject(FormBuilder);
  private readonly api = inject(TravelService);

  protected readonly meta = signal<Meta | null>(null);
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly mode = signal<'recommend' | 'itinerary' | null>(null);
  protected readonly places = signal<Place[]>([]);
  protected readonly itinerary = signal<Itinerary | null>(null);

  protected readonly form = this.fb.nonNullable.group({
    city: [''],
    budget_eur: [null as number | null, [Validators.min(0.01)]],
    days: [3, [Validators.required, Validators.min(1), Validators.max(14)]],
    travelers: [1, [Validators.required, Validators.min(1), Validators.max(20)]],
    free_only: [false],
    interests: this.fb.nonNullable.group({
      sea: [0],
      culture: [3],
      nature: [0],
      amusement: [0],
      shopping: [0],
      religious: [0],
    }),
  });

  constructor() {
    this.api.meta().subscribe({
      next: (m) => this.meta.set(m),
      error: (e) => this.error.set(this.message(e)),
    });
  }

  protected recommend(): void {
    if (this.form.invalid) return this.form.markAllAsTouched();
    this.run('recommend', () =>
      this.api.recommend({ ...this.profile(), top_k: 10 }).subscribe({
        next: (r) => {
          this.places.set(r.items);
          this.done();
        },
        error: (e) => this.fail(e),
      }),
    );
  }

  protected buildItinerary(): void {
    const profile = this.profile();
    const city = profile.city;
    if (!city) {
      this.error.set('Choisis une ville pour construire un itinéraire.');
      return;
    }
    if (this.form.invalid) return this.form.markAllAsTouched();
    this.run('itinerary', () =>
      this.api.itinerary({ ...profile, city }).subscribe({
        next: (r) => {
          this.itinerary.set(r);
          this.done();
        },
        error: (e) => this.fail(e),
      }),
    );
  }

  private profile(): ProfilePayload {
    const v = this.form.getRawValue();
    const interests = Object.fromEntries(Object.entries(v.interests).filter(([, w]) => w > 0));
    return {
      interests,
      days: v.days,
      travelers: v.travelers,
      free_only: v.free_only,
      ...(v.budget_eur ? { budget_eur: v.budget_eur } : {}),
      ...(v.city ? { city: v.city } : {}),
    };
  }

  private run(mode: 'recommend' | 'itinerary', call: () => void): void {
    this.error.set(null);
    this.loading.set(true);
    this.mode.set(mode);
    call();
  }

  private done(): void {
    this.loading.set(false);
  }

  private fail(e: unknown): void {
    this.loading.set(false);
    this.mode.set(null);
    this.error.set(this.message(e));
  }

  private message(e: unknown): string {
    const err = e as HttpErrorResponse;
    const body = err.error;
    if (body?.error === 'validation') {
      return 'Paramètres invalides : ' + Object.entries(body.fields as Record<string, string>).map(([k, v]) => `${k} (${v})`).join(', ');
    }
    if (body?.error === 'ml_service_unavailable') {
      return 'Le service de recommandation est injoignable. Réessaie dans un instant.';
    }
    if (body?.error === 'ml_service') {
      try {
        const detail = JSON.parse(body.detail).detail;
        return typeof detail === 'string' ? detail : JSON.stringify(detail);
      } catch {
        return String(body.detail);
      }
    }
    if (err.status === 0) return 'Impossible de joindre le serveur.';
    return 'Une erreur est survenue.';
  }
}
