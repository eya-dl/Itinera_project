import { DecimalPipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { Itinerary } from './models';

@Component({
  selector: 'app-itinerary-view',
  imports: [DecimalPipe],
  template: `
    <section class="totals" [class.over]="!plan().totals.within_budget">
      <strong>{{ plan().city }}</strong> — {{ plan().days.length }} jour(s), {{ plan().totals.places }} lieux ·
      {{ plan().totals.cost_per_person_eur | number: '1.0-2' }} € / personne
      @if (plan().totals.budget_eur) {
        sur {{ plan().totals.budget_eur }} € de budget
      }
      · {{ plan().totals.distance_km | number: '1.0-1' }} km de trajets
    </section>

    @for (w of plan().warnings; track w) {
      <p class="warn">{{ w }}</p>
    }

    @for (d of plan().days; track d.day) {
      <section class="day">
        <h3>Jour {{ d.day }}</h3>
        <p class="summary">{{ d.summary }} · {{ d.cost_eur | number: '1.0-2' }} € · {{ d.distance_km | number: '1.0-1' }} km</p>
        <ol>
          @for (s of d.stops; track s.place_id) {
            <li>
              @if (s.travel_minutes > 0) {
                <span class="travel">↳ {{ s.travel_minutes }} min de trajet ({{ s.travel_km | number: '1.0-1' }} km)</span>
              }
              <div class="stop">
                <span class="time">{{ s.start_time }}–{{ s.end_time }}</span>
                <div>
                  <strong>{{ s.name }}</strong>
                  <span class="chip">{{ s.category_label }}</span>
                  <div class="meta">{{ s.is_free ? 'Gratuit' : '≈ ' + (s.price_eur | number: '1.0-2') + ' €' }} · ★ {{ s.rating | number: '1.1-1' }}</div>
                  <div class="meta">{{ s.reasons[0] }}</div>
                </div>
              </div>
            </li>
          }
        </ol>
      </section>
    }
  `,
  styles: `
    .totals { background: var(--accent-soft); border-radius: 10px; padding: .75rem 1rem; margin-bottom: 1rem; }
    .totals.over { background: #fde8e8; }
    .warn { background: #fff4d6; border-radius: 8px; padding: .6rem .9rem; }
    .day { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }
    h3 { margin: 0; }
    .summary { color: var(--muted); font-size: .9rem; margin: .2rem 0 .8rem; }
    ol { list-style: none; margin: 0; padding: 0; }
    .stop { display: flex; gap: .8rem; padding: .35rem 0; }
    .time { font-variant-numeric: tabular-nums; color: var(--accent); min-width: 6.5rem; font-weight: 600; }
    .travel { display: block; color: var(--muted); font-size: .8rem; margin-left: 7.3rem; }
    .chip { background: var(--accent-soft); color: var(--accent); border-radius: 999px; padding: .05rem .5rem; font-size: .75rem; margin-left: .4rem; }
    .meta { color: var(--muted); font-size: .85rem; }
  `,
})
export class ItineraryView {
  readonly plan = input.required<Itinerary>();
}
