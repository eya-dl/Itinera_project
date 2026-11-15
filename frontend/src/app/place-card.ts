import { DecimalPipe } from '@angular/common';
import { Component, input, output } from '@angular/core';
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
      <button type="button" class="like" [class.on]="liked()" [attr.aria-pressed]="liked()" (click)="toggleLike.emit(place())">
        {{ liked() ? '✓ Plus comme ça' : '+ Plus comme ça' }}
      </button>
    </article>
  `,
  styles: `
    :host { --delay: 0ms; }
    :host(:nth-child(6n + 2)) { --delay: 70ms; }
    :host(:nth-child(6n + 3)) { --delay: 140ms; }
    :host(:nth-child(6n + 4)) { --delay: 210ms; }
    :host(:nth-child(6n + 5)) { --delay: 280ms; }
    :host(:nth-child(6n + 6)) { --delay: 350ms; }
    .card {
      background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 1.1rem; box-shadow: var(--shadow); border-top: 4px solid var(--accent); height: 100%;
      animation: rise .55s cubic-bezier(.22, .8, .3, 1) var(--delay) backwards;
      transition: transform .3s cubic-bezier(.22, .8, .3, 1), box-shadow .3s ease;
    }
    @keyframes rise { from { opacity: 0; transform: translateY(28px); } }
    @media (hover: hover) {
      .card:hover { transform: translateY(-6px) scale(1.03); box-shadow: 0 22px 38px -14px rgba(10, 52, 64, .4); }
    }
    header { display: flex; justify-content: space-between; gap: .5rem; align-items: start; }
    h3 { margin: 0; font-size: 1.15rem; }
    .chip { background: var(--accent-soft); color: var(--accent); border-radius: 999px; padding: .1rem .6rem; font-size: .78rem; white-space: nowrap; }
    .meta { color: var(--muted); font-size: .88rem; margin: .4rem 0; }
    .bar { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; }
    .bar span { display: block; height: 100%; background: var(--accent); }
    .score { font-size: .8rem; color: var(--muted); margin: .25rem 0 .5rem; }
    ul { margin: 0 0 .8rem; padding-left: 1.1rem; font-size: .9rem; }
    .like { border: 1.5px solid var(--accent); background: #fff; color: var(--accent); border-radius: 999px; padding: .35rem .9rem; font: inherit; font-size: .85rem; font-weight: 600; cursor: pointer; }
    .like.on { background: var(--accent); color: #fff; }
  `,
})
export class PlaceCard {
  readonly place = input.required<Place>();
  readonly liked = input(false);
  readonly toggleLike = output<Place>();
}
