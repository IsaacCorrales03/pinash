from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
from database import database
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# ─── AUTH ─────────────────────────────────────────────────────────────────────

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))
        error = 'Contraseña incorrecta'
    return render_template('login.html', error=error)


@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─── HOME ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    recent  = database.get_recent_products(limit=5)
    reviews = database.get_recent_reviews(limit=10)
    stats   = database.get_reviews_stats()
    return render_template('index.html', products=recent, reviews=reviews, stats=stats)


# ─── CATALOGUE ────────────────────────────────────────────────────────────────

@app.route('/catalogo')
def catalogue():
    products = database.get_all_products()
    return render_template('catalogo.html', products=products)


# ─── RESEÑAS ──────────────────────────────────────────────────────────────────

@app.route('/resenas', methods=['GET'])
def get_reviews():
    """Devuelve las últimas 10 reseñas como JSON."""
    reviews = database.get_recent_reviews(limit=10)
    # datetime no es serializable por defecto
    for r in reviews:
        if r.get('created_at'):
            r['created_at'] = r['created_at'].strftime('%d %b %Y')
    return jsonify(reviews)


@app.route('/resenas', methods=['POST'])
def create_review():
    """
    Acepta JSON  { author, rating, body }
    o form-data con los mismos campos.
    Devuelve JSON con la reseña creada o el error.
    """
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form

    author = str(data.get('author', '')).strip()
    body   = str(data.get('body', '')).strip()
    try:
        rating = int(data.get('rating', 0))
    except (ValueError, TypeError):
        rating = 0

    # ── validaciones básicas ──────────────────────────────────────────────────
    errors = {}
    if not author:
        errors['author'] = 'El nombre es requerido.'
    elif len(author) > 120:
        errors['author'] = 'El nombre no puede superar 120 caracteres.'
    if not body:
        errors['body'] = 'El comentario es requerido.'
    if rating not in range(1, 6):
        errors['rating'] = 'La calificación debe ser entre 1 y 5.'

    if errors:
        return jsonify({'ok': False, 'errors': errors}), 422

    database.create_review(author=author, rating=rating, body=body)
    return jsonify({'ok': True, 'message': '¡Gracias por tu reseña!'}), 201


# ─── ADMIN: LIST ──────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin():
    products = database.get_all_products_admin()
    return render_template('admin.html', products=products)


# ─── ADMIN: CREATE ────────────────────────────────────────────────────────────

@app.route('/admin/productos/nuevo', methods=['POST'])
@admin_required
def create_product():
    name        = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price       = request.form.get('price', '0')
    badge       = request.form.get('badge', '')
    stock       = request.form.get('stock', '0')
    image_path  = ''

    file = request.files.get('image')
    if file and file.filename:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename   = file.filename
        image_path = f"uploads/{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    database.create_product(name, description, float(price), badge, int(stock), image_path)
    return redirect(url_for('admin'))


# ─── ADMIN: EDIT ──────────────────────────────────────────────────────────────

@app.route('/admin/productos/<int:product_id>/editar', methods=['POST'])
@admin_required
def edit_product(product_id):
    name        = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    price       = request.form.get('price', '0')
    badge       = request.form.get('badge', '')
    stock       = request.form.get('stock', '0')

    row = database.get_product_image(product_id)
    image_path = row[0]['image'] if row else ''

    file = request.files.get('image')
    if file and file.filename:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename   = file.filename
        image_path = f"uploads/{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    database.update_product(product_id, name, description, float(price), badge, int(stock), image_path)
    return redirect(url_for('admin'))


# ─── ADMIN: DELETE PRODUCT ────────────────────────────────────────────────────

@app.route('/admin/productos/<int:product_id>/eliminar', methods=['POST'])
@admin_required
def delete_product(product_id):
    database.delete_product(product_id)
    return redirect(url_for('admin'))


# ─── ADMIN: DELETE REVIEW ─────────────────────────────────────────────────────

@app.route('/admin/resenas/<int:review_id>/eliminar', methods=['POST'])
@admin_required
def delete_review(review_id):
    database.delete_review(review_id)
    return redirect(url_for('admin'))

@app.route('/alive')
def alive():
    return "Vivo: true", 200
import requests
import time
import threading
from datetime import datetime

def ping():
    while True:
        try:
            res = requests.get('http://tu-servidor/alive')
            print(f"[{datetime.now().isoformat()}] {res.text}")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Error: {e}")
        time.sleep(30)


# tu código sigue aquí sin bloquearse
if __name__ == '__main__':
    threading.Thread(target=ping, daemon=True).start()

    app.run(debug=True, host='0.0.0.0', port=8080)