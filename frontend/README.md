# frontend — Angular

Interface : formulaire de profil (ville, jours, budget, intérêts), recommandations de lieux et itinéraire jour par jour.

```bash
npm install
npm start          # http://localhost:4200, /api redirigé vers http://localhost:8080 (proxy.conf.json)
npm run build
```
Structure : `src/app/app.ts` (formulaire et état), `place-card.ts`, `itinerary-view.ts`, `travel.service.ts` (appels HTTP), `models.ts` (types de l'API).
