import argparse
import random
from datetime import datetime, timedelta
from google.cloud import datastore

# Taille maximale de lot pour Datastore
BATCH_SIZE = 500


def parse_args():
    parser = argparse.ArgumentParser(description="Seed TinyInsta Datastore pour bench/repro.")
    parser.add_argument('--users', type=int, required=True, help="Nombre d'utilisateurs à créer")
    parser.add_argument('--posts-per-user', type=int, required=True, help="Nombre de posts par utilisateur")
    parser.add_argument('--followees-per-user', type=int, required=True, help="Nombre fixe de followees par utilisateur (différent de soi-même)")
    parser.add_argument('--prefix', type=str, default='user', help="Préfixe pour les usernames")
    parser.add_argument('--seed', type=int, default=None, help="Graine aléatoire pour reproductibilité")
    parser.add_argument('--clean', action='store_true', help="Nettoie le Datastore avant insertion")
    parser.add_argument('--dry-run', action='store_true', help="Affiche le plan sans écrire")
    return parser.parse_args()


def clean_datastore(client):
    """Supprime tous les Users et Posts par lots de BATCH_SIZE."""
    print("[Clean] Suppression des Users et Posts en cours...")
    
    deleted_users = 0
    query_users = client.query(kind='User')
    # Itération par lots de BATCH_SIZE pour éviter de charger toutes les clés en mémoire
    while True:
        keys = [u.key for u in query_users.fetch(limit=BATCH_SIZE)]
        if not keys:
            break
        client.delete_multi(keys)
        deleted_users += len(keys)
    
    deleted_posts = 0
    query_posts = client.query(kind='Post')
    while True:
        keys = [p.key for p in query_posts.fetch(limit=BATCH_SIZE)]
        if not keys:
            break
        client.delete_multi(keys)
        deleted_posts += len(keys)

    print(f"[Clean] Datastore nettoyé. ({deleted_users} users, {deleted_posts} posts supprimés)")


def ensure_users(client, names, dry):
    """Crée les utilisateurs par lots."""
    new_users = []
    
    print(f"[Users] Vérification/Création de {len(names)} utilisateurs...")
    
    # 1. On ne veut créer que les utilisateurs qui n'existent pas
    # Une requête de batch get (lookup) est rapide.
    user_keys = [client.key('User', name) for name in names]
    existing_entities = client.get_multi(user_keys)
    
    existing_names = {e.key.name for e in existing_entities if e}

    for name in names:
        if name not in existing_names:
            key = client.key('User', name)
            entity = datastore.Entity(key)
            entity['follows'] = []
            new_users.append(entity)
            
    if new_users and not dry:
        # 2. Écriture en une seule fois (ou par lots si > BATCH_SIZE)
        for i in range(0, len(new_users), BATCH_SIZE):
            client.put_multi(new_users[i:i + BATCH_SIZE])
            
    return len(new_users)


def assign_follows(client, names, followees_per_user, dry):
    """Assigne les relations de suivi par lots."""
    
    print(f"[Follows] Assignation de {followees_per_user} followees pour {len(names)} users...")
    
    user_keys = [client.key('User', name) for name in names]
    # Récupérer tous les utilisateurs en une seule fois
    entities_to_update = client.get_multi(user_keys)
    
    updated_entities = []

    for entity in entities_to_update:
        if entity is None: continue
        name = entity.key.name
        
        others = [u for u in names if u != name]
        if not others: continue
        
        nb_followees = min(followees_per_user, len(others))
        # Utiliser `random.sample` pour sélectionner un nombre fixe
        selection = random.sample(others, nb_followees)
        
        entity['follows'] = sorted(selection)
        updated_entities.append(entity)

    if updated_entities and not dry:
        # Mettre à jour tous les utilisateurs en une seule fois
        for i in range(0, len(updated_entities), BATCH_SIZE):
            client.put_multi(updated_entities[i:i + BATCH_SIZE])


def create_posts(client, names, posts_per_user, dry):
    """Crée les posts pour tous les utilisateurs, en utilisant put_multi."""
    total_posts = len(names) * posts_per_user
    if total_posts <= 0: return 0

    print(f"[Posts] Création de {total_posts} posts au total...")
    
    posts_buffer = []
    base_time = datetime.utcnow()
    created = 0
    
    for idx, author in enumerate(names):
        for j in range(posts_per_user):
            key = client.key('Post')
            post = datastore.Entity(key)
            post['author'] = author
            post['content'] = f"Seed post {j+1} by {author} (TS: {created})"
            # Décalage unique pour garantir l'ordre
            post['created'] = base_time - timedelta(seconds=created, milliseconds=random.randint(0, 999))
            posts_buffer.append(post)
            created += 1
            
            # Flush du buffer si on atteint la taille max du lot
            if len(posts_buffer) >= BATCH_SIZE and not dry:
                client.put_multi(posts_buffer)
                posts_buffer = []

    # Flush du buffer final
    if posts_buffer and not dry:
        client.put_multi(posts_buffer)
        
    return created


def main():
    args = parse_args()

    # Seed aléatoire pour reproductibilité
    if args.seed is not None:
        random.seed(args.seed)

    client = datastore.Client()

    user_names = [f"{args.prefix}{i}" for i in range(1, args.users + 1)]

    print(f"[Seed] Configuration: {len(user_names)} users | {args.posts_per_user} posts/user | {args.followees_per_user} followees/user")

    if args.dry_run:
        print("\n[Dry-Run] Plan seulement, aucune écriture réalisée.")

    # Nettoyage optionnel (avant car les données changent)
    if args.clean and not args.dry_run:
        clean_datastore(client)

    # 1. Users
    n_new = ensure_users(client, user_names, args.dry_run)
    print(f"[Seed] Utilisateurs ajoutés: {n_new}")

    # 2. Follows
    assign_follows(client, user_names, args.followees_per_user, args.dry_run)
    print("[Seed] Relations de suivi (follows) ajustées/créées.")

    # 3. Posts
    n_posts = create_posts(client, user_names, args.posts_per_user, args.dry_run)
    print(f"[Seed] Posts créés: {n_posts}")

    print("\n[Seed] Terminé.")


if __name__ == '__main__':
    main()