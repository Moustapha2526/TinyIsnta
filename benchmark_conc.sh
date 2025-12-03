#!/bin/bash

# --- Configuration ---
# L'URL de votre application (avec l'endpoint /timeline)
URL="https://tinyinsta1.ew.r.appspot.com/timeline"
N_REQUESTS=500  # Nombre total de requêtes par run
CONCURRENCIES=(1 10 20 50 100 1000)
OUTPUT_FILE="out/conc.csv"
OUT_DIR="out"

# Créer le répertoire de sortie s'il n'existe pas
mkdir -p $OUT_DIR

# Initialisation du fichier CSV
echo "PARAM,AVG_TIME,RUN,FAILED" > $OUTPUT_FILE
echo "Démarrage du benchmark de Charge..."

# --- Boucle principale sur la concurrence ---
for C in "${CONCURRENCIES[@]}"; do
    # Boucle sur les 3 runs
    for RUN in {1..3}; do
        echo "Test : Concurrence=$C, Run=$RUN (URL: $URL)"

        # Exécution de la commande AB et capture de la sortie complète
        # On utilise une commande simple pour extraire la valeur en millisecondes.
        AB_OUTPUT=$(ab -n $N_REQUESTS -c $C "$URL" 2>&1)
        
        # Tentative d'extraction du temps moyen par requête (en ms)
        # La valeur est le 4ème champ de la ligne "Time per request:"
        AVG_TIME=$(echo "$AB_OUTPUT" | grep "Time per request:" | head -1 | awk '{print $4}')

        # Détection d'échec
        FAILED=0
        # AB retourne un message spécifique en cas d'échec ou de non-connexion
        if [ -z "$AVG_TIME" ] || echo "$AB_OUTPUT" | grep -q "failed requests" || echo "$AB_OUTPUT" | grep -q "non-HTTP response"; then
            FAILED=1
            AVG_TIME="N/A" 
            echo "ATTENTION: Échec détecté pour C=$C, Run=$RUN."
        fi

        # Écriture dans le fichier CSV
        echo "$C,$AVG_TIME,$RUN,$FAILED" >> $OUTPUT_FILE
        
        # Pause de sécurité pour ne pas surcharger la connexion
        sleep 2 
    done
done

echo "Génération de $OUTPUT_FILE terminée."