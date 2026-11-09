# Évaluation hors ligne

Test : 1917 notes, 300 utilisateurs. Pertinent = note >= 4.

## Prédiction des notes

| Méthode | RMSE | MAE |
|---|---|---|
| Moyenne globale | 1.382 | 1.176 |
| Moyenne utilisateur | 1.387 | 1.193 |
| Moyenne lieu (lissée) | 1.389 | 1.188 |
| Biais utilisateur + lieu | 1.393 | 1.200 |
| Item-kNN (k=20) | 1.460 | 1.239 |

## Classement (top 10)

| Méthode | Precision@10 | Recall@10 |
|---|---|---|
| Aléatoire | 0.009 | 0.028 |
| Popularité | 0.005 | 0.021 |
| Qualité (note + moyenne lissée) | 0.006 | 0.023 |
| Contenu (intérêts déduits des notes) | 0.008 | 0.029 |
| Item-CF (lieux aimés) | 0.008 | 0.037 |

Lecture : aucune méthode ne bat nettement la moyenne globale (RMSE) ni l'aléatoire (Precision@10). Les notes de ce dataset ne contiennent pas de signal individuel exploitable : la personnalisation du moteur repose donc sur le profil déclaré (intérêts, budget, durée), pas sur l'historique de notes. Il faut évaluer ce moteur par ses contraintes (budget, temps, ville) et par un test auprès de vrais utilisateurs.