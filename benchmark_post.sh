#!/bin/bash

# Configuration du test de POSTS
URL="https://tinyinsta1.ew.r.appspot.com/timeline"
CONCURRENCY=50
N_REQUESTS=500
POST_VALUES=(10 100 1000)
OUTPUT_FILE="out/post.csv"
OUT_DIR="out"

mkdir -p $OUT_DIR
echo "PARAM,AVG_TIME,RUN,FAILED" > $OUTPUT_FILE
echo "Démarrage du benchmark sur la Taille des Posts..."

for P in "${POST_VALUES[@]}"; do
    
    # 🚨 Étape Cruciale 1 : RE-PEUPLEMENT DE LA BASE DE DONNÉES
    # Assurez-vous d'appeler votre script de seed pour la configuration (1000 utilisateurs, P posts, 20 followees)
    echo "-> Peuplement des données : P = $P posts par utilisateur..."
    # [COMMANDE_SEED] (Ex: python seed.py --posts $P --followees 20)
    # Assurez-vous que l'opération de seed est bien terminée avant le benchmark.
    
    # Étape Cruciale 2 : Exécution des 3 runs de benchmark
    for RUN in {1..3}; do
        echo "Test : Posts=$P, Run=$RUN"
        
        AB_OUTPUT=$(ab -n $N_REQUESTS -c $CONCURRENCY "$URL" 2>&1)
        AVG_TIME=$(echo "$AB_OUTPUT" | grep "Time per request:" | head -1 | awk '{print $4}')
        
        FAILED=0
        if [ -z "$AVG_TIME" ] || echo "$AB_OUTPUT" | grep -q "failed requests"; then
            FAILED=1
            AVG_TIME="N/A"
        fi

        echo "$P,$AVG_TIME,$RUN,$FAILED" >> $OUTPUT_FILE
        sleep 2 
    done
done

echo "Génération de $OUTPUT_FILE terminée."