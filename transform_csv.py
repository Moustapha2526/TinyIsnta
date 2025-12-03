import pandas as pd
import os

# Définition du répertoire de sortie
OUTPUT_DIR = 'out'
FILES_TO_TRANSFORM = ['conc.csv', 'post.csv', 'fanout.csv']

def transform_to_wide(input_filename):
    input_path = os.path.join(OUTPUT_DIR, input_filename)
    output_path = os.path.join(OUTPUT_DIR, input_filename) # Écrase l'ancien fichier
    
    # 1. Lecture du fichier
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"❌ Erreur: Fichier {input_filename} non trouvé.")
        return

    # S'assurer que les AVG_TIME sont numériques (en gérant les "N/A" si des erreurs subsistent)
    df['AVG_TIME'] = pd.to_numeric(df['AVG_TIME'], errors='coerce')
    
    # Filtrer les erreurs pour le plotting (on ne plotte que ce qui a réussi)
    df_clean = df[df['FAILED'] == 0].copy()
    
    # Si le nombre de runs est trop faible, cela peut poser problème au pivot.
    if df_clean.empty or df_clean['RUN'].nunique() < 3:
        print(f"⚠️ Avertissement: Le fichier {input_filename} n'a pas assez de runs réussis pour être pivoté.")
        # On peut tenter de remplir les valeurs manquantes plus tard si nécessaire
        
    # 2. Préparer la colonne pour le pivot (RUN_1, RUN_2, RUN_3)
    df_clean['RUN_COL'] = 'RUN_' + df_clean['RUN'].astype(str)

    # 3. Pivotage (format long vers format large)
    # Les colonnes de RUN deviennent des colonnes de valeurs de temps
    try:
        df_wide = df_clean.pivot(
            index='PARAM', 
            columns='RUN_COL', 
            values='AVG_TIME'
        ).reset_index()
    except ValueError as e:
        print(f"❌ Erreur lors du pivotage de {input_filename}. Vérifiez si chaque PARAM a 3 runs uniques et non-FAILED.")
        print(e)
        return

    # 4. Assurer l'ordre des colonnes et renommer pour la compatibilité
    required_cols = ['PARAM'] + [f'RUN_{i}' for i in range(1, 4)]
    
    # Remplir les colonnes manquantes avec NaN si un run est manquant
    for col in required_cols:
        if col not in df_wide.columns:
            df_wide[col] = pd.NA

    df_wide = df_wide.reindex(columns=required_cols)
    
    # 5. Écriture du nouveau fichier CSV (format large)
    df_wide.to_csv(output_path, index=False)
    print(f"✅ Fichier transformé et enregistré: {output_path} (Format Large)")

# Exécution pour les trois fichiers
print("--- Démarrage de la transformation Long -> Large ---")
for f in FILES_TO_TRANSFORM:
    transform_to_wide(f)
print("--- Transformation terminée ---")