import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# --- Configuration des fichiers et des titres ---
# Le dossier 'out' doit contenir les fichiers CSV
OUT_DIR = 'out' 
FILES = {
    # Fichier CSV : (Titre du graphique, Label de l'axe X)
    'conc.csv': ('Temps moyen par requête selon la concurrence (ms)', 'Nombre d\'utilisateurs concurrents'),
    'post.csv': ('Temps moyen par requête selon le volume de posts (ms)', 'Nombre de posts par utilisateur'),
    'fanout.csv': ('Temps moyen par requête selon le fan-out (ms)', 'Nombre de followees par utilisateur')
}


def process_and_plot(filename, title, xlabel):
    """Charge un fichier CSV, calcule la moyenne et la variance, puis génère le barplot avec barres d'erreur."""
    
    csv_path = os.path.join(OUT_DIR, filename)
    
    if not os.path.exists(csv_path):
        print(f"⚠️ Fichier {csv_path} introuvable. Veuillez vérifier le chemin et le nom.")
        return

    try:
        # Lire le fichier CSV
        # On utilise le premier en-tête comme index/paramètre
        df = pd.read_csv(csv_path, sep=',', header=0)
        
        # S'assurer que les noms de colonnes sont conformes (ex: RUN_1_TEMPS_MS)
        time_cols = [col for col in df.columns if 'TEMPS' in col.upper() or 'RUN' in col.upper()]
        
        if len(time_cols) < 2:
            print(f"❌ Erreur: Le fichier {filename} doit contenir au moins 2 colonnes de temps (RUN_1, RUN_2, etc.).")
            return

        # Calculer la moyenne et l'écart-type (variance) pour les barres d'erreur
        df['MEAN'] = df[time_cols].mean(axis=1)
        df['STD_DEV'] = df[time_cols].std(axis=1) # std() pour l'écart-type
        
        # Le nom de la colonne des paramètres est généralement la première
        param_col = df.columns[0]
        
        # --- Génération du graphique ---
        
        # Création de la figure
        plt.figure(figsize=(10, 6))
        
        # Barplot avec barres d'erreur (écart-type)
        plt.bar(df[param_col].astype(str), # X: Les labels de paramètres
                df['MEAN'],                # Y: La moyenne du temps
                yerr=df['STD_DEV'],        # Les barres d'erreur (écart-type)
                capsize=5,                 # Taille des capuchons de barres d'erreur
                color='skyblue',
                edgecolor='black',
                alpha=0.7)

        # Ajouter les titres et labels
        plt.title(title, fontsize=16)
        plt.xlabel(xlabel, fontsize=12)
        plt.ylabel('Temps moyen par requête (ms)', fontsize=12)
        plt.grid(axis='y', linestyle='--', alpha=0.6)
        
        # Rotation des labels X pour une meilleure lisibilité si les valeurs sont grandes
        plt.xticks(rotation=0)
        
        # S'assurer que le graphique est bien ajusté
        plt.tight_layout()
        
        # Sauvegarde du graphique au format .png (nom de fichier basé sur le CSV)
        output_filename = filename.replace('.csv', '.png')
        output_path = os.path.join(OUT_DIR, output_filename)
        
        # Créer le dossier 'out' s'il n'existe pas
        if not os.path.exists(OUT_DIR):
            os.makedirs(OUT_DIR)
            
        plt.savefig(output_path)
        print(f"✅ Graphique généré et sauvegardé : {output_path}")

    except Exception as e:
        print(f"Une erreur est survenue lors du traitement de {filename}: {e}")


def main():
    print("--- Démarrage de la génération des graphiques de benchmark ---")
    
    for filename, (title, xlabel) in FILES.items():
        process_and_plot(filename, title, xlabel)
    
    print("--- Tous les graphiques ont été traités. ---")


if __name__ == '__main__':
    # Installer les librairies si ce n'est pas déjà fait :
    # pip install pandas matplotlib numpy
    main()