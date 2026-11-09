import { DecimalPipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { Place } from './models';

@Component({
  selector: 'app-place-card',
  imports: [DecimalPipe],
  template: `
    <article class="card">
      <header>
        <h3>{{ place().name }}</h3>
        <span class="chip">{{ place().category_label }}</span>
      </header>
      <p class="meta">
        {{ place().city }} ·
        {{ place().is_free ? 'Entrée gratuite' : '≈ ' + (place().price_eur | number: '1.0-2') + ' €' }} ·
        {{ place().visit_minutes }} min{{ place().duration_estimated ? ' (estimée)' : '' }} ·
        ★ {{ place().rating | number: '1.1-1' }}
      </p>
      <div class="bar" [attr.aria-label]="'Score ' + (place().score * 100 | number: '1.0-0') + ' sur 100'">
        <span [style.width.%]="place().score * 100"></span>
      </div>
      <p class="score">Score {{ place().score * 100 | number: '1.0-0' }}/100</p>
      <ul>
        @for (r of place().reasons; track r) {
          <li>{{ r }}</li>
        }
      </ul>
    </article>
  `,
  styles: `
    .card { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 1rem; }
    header { display: flex; justify-content: space-between; gap: .5rem; align-items: start; }
    h3 { margin: 0; font-size: 1.05rem; }
    .chip { background: var(--accent-soft); color: var(--accent); border-radius: 999px; padding: .1rem .6rem; font-size: .78rem; white-space: nowrap; }
    .meta { color: var(--muted); font-size: .88rem; margin: .4rem 0; }
    .bar { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
    .bar span { display: block; height: 100%; background: var(--accent); }
    .score { font-size: .8rem; color: var(--muted); margin: .25rem 0 .5rem; }
    ul { margin: 0; padding-left: 1.1rem; font-size: .9rem; }
  `,
})
export class PlaceCard {
  readonly place = input.required<Place>();
}
