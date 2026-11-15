# Évaluation sur les circuits réels (leave-one-out)

100 circuits, 405 cas (un lieu caché, les autres donnés comme lieux aimés, ville du circuit). Intervalle de confiance à 95 % par bootstrap sur les cas ; p-valeur = bootstrap apparié contre le moteur d'origine. Les cas d'un même circuit ne sont pas indépendants : les p-valeurs sont indicatives.

| Méthode | HR@5 | HR@10 | MRR | NDCG@10 | Δ NDCG@10 vs origine (p) |
|---|---|---|---|---|---|
| Aléatoire (même ville) | 0.077 | 0.143 | 0.067 | 0.064 [0.048; 0.081] | -0.047 (p = 0.000) |
| Popularité (nb de notes, même ville) | 0.062 | 0.141 | 0.064 | 0.062 [0.046; 0.079] | -0.050 (p = 0.000) |
| Moteur d'origine | 0.128 | 0.210 | 0.108 | 0.111 [0.087; 0.136] |  |
| Proposition de l'autre agent (sim 0,05 ; pénalité 0,12 ; qualité 0,9/0,1) | 0.096 | 0.178 | 0.084 | 0.085 [0.066; 0.107] | -0.026 (p = 0.011) |
| Origine + seulement sim 0,05 | 0.089 | 0.185 | 0.088 | 0.090 [0.069; 0.113] | -0.021 (p = 0.013) |
| Origine sans filtrage collaboratif (contenu seul) | 0.269 | 0.351 | 0.192 | 0.213 [0.179; 0.245] | +0.102 (p = 0.000) |
| Contenu seul + sim 0,25 (poids non renormalisés) | 0.316 | 0.417 | 0.213 | 0.246 [0.211; 0.280] | +0.135 (p = 0.000) |
| **RÉGLAGE CHOISI (contenu 0,75 / notes 0,15 ; poids 0,40 / 0,20 / 0,15 / 0,25)** | 0.262 | 0.395 | 0.189 | 0.220 [0.189; 0.253] | +0.109 (p = 0.000) |
| Contenu 0,9 / notes 0,1 ; poids 0,40 / 0,20 / 0,15 / 0,25 | 0.304 | 0.430 | 0.200 | 0.239 [0.207; 0.270] | +0.128 (p = 0.000) |
| Contenu seul (100/0) ; poids 0,40 / 0,20 / 0,15 / 0,25 | 0.328 | 0.440 | 0.218 | 0.255 [0.220; 0.288] | +0.144 (p = 0.000) |
| Contenu seul + sim 0,35 | 0.336 | 0.457 | 0.218 | 0.260 [0.226; 0.292] | +0.149 (p = 0.000) |
| Contenu seul + pénalité 0,12 | 0.210 | 0.291 | 0.177 | 0.186 [0.154; 0.218] | +0.075 (p = 0.000) |

## Balayage de la pénalité de diversité (profil mono-intérêt, note 5, par ville et catégorie)

| pénalité | catégories distinctes / 10 | part dans la catégorie voulue | rang du 1er lieu d'une autre catégorie |
|---|---|---|---|
| 0.04 | 3.00 | 0.65 | 7.47 |
| 0.08 | 4.07 | 0.54 | 6.37 |
| 0.12 | 5.23 | 0.43 | 4.90 |
| 0.15 | 5.40 | 0.40 | 4.30 |
