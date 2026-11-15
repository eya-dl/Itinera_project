#!/bin/sh
# Lance toutes les évaluations dans l'ordre (depuis le dossier ml-service).
# QUICK=1 sh scripts/run_all_evaluations.sh  -> version rapide de l'évaluation complète (1 graine)
set -e
SEEDS="--seeds 5"; [ -n "$QUICK" ] && SEEDS="--quick"
echo "== 1/5 tests";                 python -m pytest -q
echo "== 2/5 évaluation complète (hybride vs approches vs popularité, cold-start)"; python scripts/evaluate_full.py $SEEDS
echo "== 3/5 circuits réels";        python scripts/evaluate_circuits.py > /dev/null && echo "   -> reports/evaluation_circuits.md"
echo "== 4/5 audit des contraintes"; python scripts/audit_constraints.py | tail -4
echo "== 5/5 diagnostic des notes";  python scripts/diagnose_signal.py > /dev/null && echo "   -> reports/diagnostic_signal.md"
echo "Terminé. Rapports dans ml-service/reports/"
