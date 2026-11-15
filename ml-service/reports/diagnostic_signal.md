# Diagnostic du signal dans les notes

9597 notes, 300 utilisateurs, 437 lieux.

## 1. Distribution des notes

Part par note arrondie : 1 : 16.8%, 2 : 21.0%, 3 : 21.6%, 4 : 21.0%, 5 : 19.6%
Khi-deux d'uniformité : p = 1.26e-14. La distribution est quasi plate (chaque note entre 17% et 22%) : l'uniformité exacte est rejetée (la note 1 est un peu sous-représentée), mais une distribution aussi plate ressemble à un tirage au sort ; des notes réelles de voyageurs sont en général concentrées sur 4-5.

## 2. Variance des notes expliquée (R²) contre notes mélangées (200 permutations)

| Effet | R² observé | R² attendu si bruit pur | p (permutation) |
|---|---|---|---|
| utilisateur | 0.0444 | 0.0311 | 0.000 |
| lieu | 0.0488 | 0.0457 | 0.145 |
| utilisateur × catégorie | 0.1890 | 0.1705 | 0.000 |

Lecture : plus il y a de groupes, plus le R² est mécaniquement grand même sans signal, d'où la colonne « attendu ». L'effet utilisateur est faible mais significatif (certains utilisateurs notent plus généreusement) : il décale tous les lieux d'un même utilisateur de la même façon et ne change donc pas leur ordre. L'effet lieu n'est pas distinguable du bruit. L'effet utilisateur × catégorie contient l'effet utilisateur : le test 4 vérifie s'il y a un goût propre à la catégorie.

## 3. Fiabilité par moitiés — la qualité d'un lieu est-elle stable ?

Corrélation entre la note moyenne d'un lieu sur deux moitiés aléatoires de ses notes : r = 0.027 (écart-type 0.035 sur 200 tirages). Un vrai effet « lieu » donnerait r nettement > 0 ; ici l'IC est centré sur 0.

Corrélation entre la note d'un lieu dans `place_features.csv` et les notes des utilisateurs : r = 0.003 (p = 0.78). C'est la base de la composante `quality` du moteur (poids 0,7 sur cette note).

## 4. Stabilité des goûts par catégorie (fondement du « contenu »)

506 couples (utilisateur, catégorie) avec ≥ 3 notes en entraînement et ≥ 2 en test. Corrélation entre l'écart à sa moyenne que l'utilisateur donne à une catégorie en train et en test : r = -0.052 (loi nulle : moyenne -0.001, écart-type 0.044, p = 0.896). Si les utilisateurs avaient des goûts par catégorie, r serait nettement positif.

## 5. Autres indices de données synthétiques

- Chaque utilisateur a noté des lieux dans 4 à 5 villes sur 5 (médiane 5) : un voyageur réel noterait surtout une ou deux villes.
- Nombre de notes par utilisateur : 21 à 53, quasi constant ; notes par lieu : 12 à 39.
