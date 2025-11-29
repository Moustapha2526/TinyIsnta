from flask import Flask, request, redirect, url_for, render_template_string, session, jsonify
from google.cloud import datastore
from datetime import datetime, timedelta
import os
import random

app = Flask(__name__)
app.secret_key = 'dev-key'
client = datastore.Client()

# Template HTML minimal
TEMPLATE_INDEX = '''
<h2>Bienvenue sur Tiny Instagram</h2>
{% if user %}
  Connecté en tant que <b>{{ user }}</b> | <a href="/logout">Déconnexion</a><br><br>
  <form action="/post" method="post">
    <input name="content" placeholder="Votre message" required>
    <button>Poster</button>
  </form>
  <h3>Timeline</h3>
  {% for post in timeline %}
    <div><b>{{ post['author'] }}</b>: {{ post['content'] }}</div>
  {% endfor %}
  <h3>Suivre un utilisateur</h3>
  <form action="/follow" method="post">
    <input name="to_follow" placeholder="Nom d'utilisateur" required>
    <button>Suivre</button>
  </form>
{% else %}
  <form action="/login" method="post">
    <input name="username" placeholder="Nom d'utilisateur" required>
    <button>Connexion</button>
  </form>
{% endif %}
'''

# ------------------------------------------------------------
# TIMELINE — Version stable sans GQL (évite erreurs Datastore)
# ------------------------------------------------------------
def get_timeline(user: str, limit: int = 20):
    if not user:
        return []

    user_key = client.key('User', user)
    user_entity = client.get(user_key)

    if not user_entity:
        return []

    follows = list(set(user_entity.get('follows', []) + [user]))

    # Pas de GQL : trop instable avec IN + ORDER BY
    posts = []
    for author in follows:
        q = client.query(kind='Post')
        q.add_filter('author', '=', author)
        q.order = ['-created']
        posts.extend(list(q.fetch(limit=limit)))

    # Trie global (limit total)
    posts = sorted(posts, key=lambda p: p.get('created'), reverse=True)[:limit]

    return posts


# ------------------------------------------------------------
# SEED — Version solide et adaptée au benchmark
# ------------------------------------------------------------
def seed_data(users: int = 5, posts: int = 30,
              follows_min: int = 1, follows_max: int = 3,
              prefix: str = 'user'):

    user_names = [f"{prefix}{i}" for i in range(1, users + 1)]

    # Création des utilisateurs
    created_users = 0
    for name in user_names:
        key = client.key('User', name)
        entity = client.get(key)
        if entity is None:
            entity = datastore.Entity(key)
            entity['follows'] = []
            client.put(entity)
            created_users += 1

    # Relations de follow
    for name in user_names:
        key = client.key('User', name)
        entity = client.get(key)

        others = [u for u in user_names if u != name]

        if not others:
            continue

        max_follow = min(follows_max, len(others))
        min_follow = min(follows_min, len(others))

        if min_follow > max_follow:
            min_follow = max_follow

        target = random.randint(min_follow, max_follow)
        selection = random.sample(others, target)

        entity['follows'] = sorted(selection)
        client.put(entity)

    # Posts (optimisés)
    created_posts = 0
    base_time = datetime.utcnow()

    for i in range(posts):
        author = random.choice(user_names)
        p = datastore.Entity(client.key('Post'))
        p.update({
            'author': author,
            'content': f"Seed post {i+1} by {author}",
            'created': base_time - timedelta(seconds=i)
        })
        client.put(p)
        created_posts += 1

    return {
        'users_total': users,
        'users_created': created_users,
        'posts_created': created_posts,
        'prefix': prefix
    }


# ------------------------------------------------------------
# ROUTES
# ------------------------------------------------------------

@app.route('/')
def index():
    user = session.get('user')
    timeline = get_timeline(user) if user else []
    return render_template_string(TEMPLATE_INDEX, user=user, timeline=timeline)


@app.route('/api/timeline')
def api_timeline():
    user = request.args.get('user') or session.get('user')
    if not user:
        return jsonify({"error": "missing user"}), 400

    # Vérification utilisateur
    if not client.get(client.key('User', user)):
        return jsonify({"error": "unknown user"}), 404

    try:
        limit = int(request.args.get('limit', '20'))
    except ValueError:
        limit = 20

    limit = max(1, min(limit, 100))
    entities = get_timeline(user, limit=limit)

    data = [{
        'author': e.get('author'),
        'content': e.get('content'),
        'created': (e.get('created') or datetime.utcnow()).isoformat() + 'Z'
    } for e in entities]

    return jsonify({'user': user, 'count': len(data), 'items': data})


@app.route('/admin/seed', methods=['POST'])
def admin_seed():
    expected = os.environ.get('SEED_TOKEN')
    provided = request.headers.get('X-Seed-Token') \
        or request.args.get('token') \
        or request.form.get('token')

    if expected and provided != expected:
        return jsonify({'error': 'forbidden'}), 403

    def _int(name, default):
        try:
            return int(request.values.get(name, default))
        except ValueError:
            return default

    users = _int('users', 5)
    posts = _int('posts', 30)
    follows_min = _int('follows_min', 1)
    follows_max = _int('follows_max', 3)
    prefix = request.values.get('prefix', 'user')

    if users <= 0 or posts < 0:
        return jsonify({'error': 'invalid parameters'}), 400

    result = seed_data(
        users=users,
        posts=posts,
        follows_min=follows_min,
        follows_max=follows_max,
        prefix=prefix
    )

    return jsonify({'status': 'ok', **result})


@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    key = client.key('User', username)

    if not client.get(key):
        entity = datastore.Entity(key)
        entity['follows'] = []
        client.put(entity)

    session['user'] = username
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


@app.route('/post', methods=['POST'])
def post():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))

    content = request.form['content']
    entity = datastore.Entity(client.key('Post'))
    entity.update({
        'author': user,
        'content': content,
        'created': datetime.utcnow()
    })
    client.put(entity)
    return redirect(url_for('index'))


@app.route('/follow', methods=['POST'])
def follow():
    user = session.get('user')
    to_follow = request.form['to_follow']

    if not user or user == to_follow:
        return redirect(url_for('index'))

    user_key = client.key('User', user)
    user_entity = client.get(user_key)

    if to_follow not in user_entity['follows']:
        user_entity['follows'].append(to_follow)
        client.put(user_entity)

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)

@app.route('/admin/clear', methods=['POST'])
def admin_clear():
    expected = os.environ.get('SEED_TOKEN')
    provided = request.headers.get('X-Seed-Token') \
        or request.args.get('token') \
        or request.form.get('token')

    if expected and provided != expected:
        return jsonify({'error': 'forbidden'}), 403

    q_users = client.query(kind='User')
    users = list(q_users.fetch())
    for u in users:
        client.delete(u.key)

    q_posts = client.query(kind='Post')
    posts = list(q_posts.fetch())
    for p in posts:
        client.delete(p.key)

    return jsonify({
        "status": "ok",
        "users_deleted": len(users),
        "posts_deleted": len(posts)
    })


# ⚠️ Ce bloc DOIT être en tout dernier
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
