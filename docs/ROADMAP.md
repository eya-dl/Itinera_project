# Feuille de route

## Fait
- Nettoyage et preprocessing (notebook), contrôle de qualité, train/test des notes
- Moteur de recommandation explicable, itinéraire, évaluation hors ligne
- API Spring Boot, interface Angular, orchestration Docker

## À valider en premier
1. `cd backend && mvn test` puis `docker compose up --build` : le backend et Docker n'ont pas pu être exécutés lors de la génération.
2. Ouvrir l'interface dans un navigateur et parcourir les deux parcours (recommandation, itinéraire).

## Étapes suivantes (par priorité)
1. **Saison** : climat mensuel par ville (Open-Meteo) et critère « meilleurs mois » dans le score.
2. **Descriptions** : embeddings multilingues (les textes sont en indonésien) pour la recherche par texte libre et la similarité de contenu.
3. **Explications en langage naturel** : LLM qui reformule les `reasons` en s'appuyant uniquement sur les données du lieu (RAG), avec contrôle de fidélité.
4. **Hébergement et transport** : prix par nuit (Inside Airbnb) et estimation des trajets ; budget global par poste.
5. **Itinéraire plus réaliste** : pause déjeuner, horaires d'ouverture, distances routières.
6. **Autres destinations** : ajouter un second adaptateur de données (autres pays) derrière le même format de table.
7. **Qualité produit** : authentification, comptes, favoris (alimentent `liked_place_ids`), tests de bout en bout.

## Évaluation à prévoir pour le rapport
- Contraintes : taux de respect du budget, du temps par jour et de la ville (automatique, déjà testé).
- Cohérence géographique des journées : distance moyenne par jour contre un tirage aléatoire.
- Étude utilisateur : 8 à 10 personnes comparent l'itinéraire généré à un itinéraire de référence (note 1 à 5 sur pertinence, faisabilité, clarté des explications).
- Fidélité des explications : vérifier que chaque affirmation correspond aux données du lieu.
- Limite à documenter : les notes du dataset ne portent pas de signal individuel (`ml-service/reports/evaluation.md`).
