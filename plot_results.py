import pandas as pd
import matplotlib.pyplot as plt
import os

# --- Configuration et Définition des Fichiers ---
OUTPUT_DIR = 'out'
PLOTS_TO_GENERATE = [
    {
        'file': 'conc.csv',
        'title': 'Temps moyen par requête selon la Concurrence',
        'param_name': 'Nombre d\'utilisateurs concurrents',
        'output_png': 'conc.png'
    },
    {
        'file': 'post.csv',
        'title': 'Temps moyen par requête selon le Nombre de Posts',
        'param_name': 'Nombre de posts par utilisateur',
        'output_png': 'post.png'
    },
    {
        'file': 'fanout.csv',
        'title': 'Temps moyen par requête selon le Fanout',
        'param_name': 'Nombre de followees par utilisateur',
        'output_png': 'fanout.png'
    },
]

# --- Fonction de Plotting ---
def generate_plot(config):
    """Lit le CSV au format large, calcule la moyenne/variance et génère le graphique."""
    
    input_path = os.path.join(OUTPUT_DIR, config['file'])
    output_png_path = config['output_png'] # Fichier PNG généré à la racine du projet

    print(f"Traitement de {input_path}...")

    try:
        # 1. Lecture du fichier CSV (format large attendu: PARAM, RUN_1, RUN_2, RUN_3...)
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        print(f"❌ Erreur: Fichier {input_path} non trouvé. Assurez-vous qu'il est dans le répertoire '{OUTPUT_DIR}'.")
        return
    
    # 2. Identification des colonnes de temps (RUN_1, RUN_2, RUN_3)
    run_cols = [col for col in df.columns if col.startswith('RUN_')]
    
    if not run_cols:
        print(f"❌ Erreur: Aucune colonne 'RUN_x' trouvée dans {input_path}. Le fichier n'est pas au format large attendu.")
        return

    # 3. Calcul des statistiques (Moyenne et Écart-type (STD) = Variance)
    # Les calculs sont faits ligne par ligne sur les colonnes RUN
    df['AVG_TIME_MEAN'] = df[run_cols].mean(axis=1) 
    df['AVG_TIME_STD'] = df[run_cols].std(axis=1)   
    
    # 4. Création du Barplot avec Barres d'Erreur
    plt.figure(figsize=(10, 6))
    
    # Utilisez 'PARAM' pour l'axe des X et la moyenne pour la hauteur des barres.
    # yerr est l'écart-type qui représente la variance.
    plt.bar(
        df['PARAM'].astype(str), 
        df['AVG_TIME_MEAN'], 
        yerr=df['AVG_TIME_STD'], 
        capsize=5, # Taille des capuchons sur les barres d'erreur
        color='darkblue', 
        alpha=0.8
    )
    
    # 5. Configuration du graphique
    plt.title(config['title'], fontsize=16)
    plt.xlabel(config['param_name'], fontsize=12)
    plt.ylabel('Temps moyen par requête (ms)', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.xticks(rotation=0)
    plt.tight_layout() # Ajustement automatique

    # 6. Sauvegarde
    try:
        plt.savefig(output_png_path)
        print(f"✅ Graphique généré et enregistré : {output_png_path}")
    except Exception as e:
        print(f"❌ Erreur lors de l'enregistrement de {output_png_path}: {e}")
    finally:
        plt.close()

# --- Exécution Principale ---
if __name__ == '__main__':
    print("--- Démarrage de la génération des graphiques de benchmark ---")
    
    # Créer le répertoire de sortie si nécessaire, pour éviter les erreurs de chemin lors de la sauvegarde du PNG
    if not os.path.exists(OUTPUT_DIR):
        print(f"Répertoire '{OUTPUT_DIR}' non trouvé. Assurez-vous que les CSV y sont stockés.")
        
    # Boucle sur les trois configurations
    for plot_config in PLOTS_TO_GENERATE:
        generate_plot(plot_config)
    
    print("--- Traitement terminé ---")