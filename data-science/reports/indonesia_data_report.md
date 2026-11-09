# Rapport qualité des données — Indonesia Tourism

- Lieux : **437** dans 5 villes, 6 catégories
- Durée de visite imputée : **232** lieux (53%)
- Entrée gratuite (prix = 0) : **137** lieux (31%)
- Coordonnées hors Indonésie : **0**
- Notes utilisateurs : 10000 brutes -> **9597** après dédoublonnage
- Utilisateurs : 300 ; lieux notés au moins une fois : 437/437
- Notes par lieu : médiane 22, min 12, max 39
- Circuits : 100 ; lieux non rapprochés d'un place_id : **0**/405

## Lieux par ville et catégorie

| city       |   amusement |   culture |   nature |   religious |   sea |   shopping |
|:-----------|------------:|----------:|---------:|------------:|------:|-----------:|
| Bandung    |          39 |        22 |       54 |           8 |     0 |          1 |
| Jakarta    |          27 |        32 |        4 |           3 |     8 |         10 |
| Semarang   |          15 |        15 |       20 |           3 |     4 |          0 |
| Surabaya   |          18 |        18 |        5 |           3 |     1 |          1 |
| Yogyakarta |          36 |        30 |       23 |           0 |    34 |          3 |

## Prix (IDR) par catégorie

| category   |   count |   50% |    max |
|:-----------|--------:|------:|-------:|
| amusement  |     135 | 10000 | 300000 |
| culture    |     117 |  3000 | 250000 |
| nature     |     106 | 10000 | 500000 |
| religious  |      17 |     0 |  10000 |
| sea        |      47 | 10000 | 900000 |
| shopping   |      15 |     0 |      0 |

Figures : `reports/*.png`