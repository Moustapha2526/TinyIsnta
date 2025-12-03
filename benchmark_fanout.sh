#!/bin/bash

# Configuration du test de FANOUT
URL="https://tinyinsta1.ew.r.appspot.com/timeline"
CONCURRENCY=50
N_REQUESTS=500
FANOUT_VALUES=(10 50 100)
OUTPUT_FILE="out/fanout.csv"
OUT_DIR="out"

mkdir -p $OUT_DIR
echo "PARAM,AVG_TIME,RUN,FAILED" > $OUTPUT_FILE
echo "Démarrage du benchmark sur le Fanout..."

for F in "${FANOUT_VALUES[@]}"; do
    
    # 🚨 Étape Cruciale 1 : RE-PEUPLEMENT DE LA BASE DE DONNÉES
    # Assurez-vous d'appeler votre script de seed pour la configuration (1000 utilisateurs, 100 posts, F followees)
    echo "-> Peuplement des données : F = $F followees par utilisateur..."
    # [COMMANDE_SEED] (Ex: python seed.py --posts 100 --followees $F)
    
    # Étape Cruciale 2 : Exécution des 3 runs de benchmark
    for RUN in {1..3}; do
        echo "Test : Fanout=$F, Run=$RUN"
        
        AB_OUTPUT=$(ab -n $N_REQUESTS -c $CONCURRENCY "$URL" 2>&1)
        AVG_TIME=$(echo "$AB_OUTPUT" | grep "Time per request:" | head -1 | awk '{print $4}')
        
        FAILED=0
        if [ -z "$AVG_TIME" ] || echo "$AB_OUTPUT" | grep -q "failed requests"; then
            FAILED=1
            AVG_TIME="N/A"
        fi

        echo "$F,$AVG_TIME,$RUN,$FAILED" >> $OUTPUT_FILE
        sleep 2 
    done
done

echo "Génération de $OUTPUT_FILE terminée."