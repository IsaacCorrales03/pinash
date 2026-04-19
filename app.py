from flask import Flask, render_template, request, redirect, url_for, session
import os
from database import database
from dotenv import load_dotenv
load_dotenv()  # ← primero que todo

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
print(ADMIN_PASSWORD)
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
    recent = database.query(
        "SELECT id, name, description, price, image, badge FROM products ORDER BY id DESC LIMIT 5"
    )
    return render_template('index.html', products=recent)


# ─── CATALOGUE ────────────────────────────────────────────────────────────────

@app.route('/catalogo')
def catalogue():
    products = database.query(
        "SELECT id, name, description, price, image, badge FROM products ORDER BY id DESC"
    )
    return render_template('catalogo.html', products=products)


# ─── ADMIN: LIST ──────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin():
    products = database.query(
        "SELECT id, name, description, price, image, badge, stock FROM products ORDER BY id DESC"
    )
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

    database.query(
        "INSERT INTO products (name, description, price, badge, stock, image) VALUES (?, ?, ?, ?, ?, ?)",
        (name, description, float(price), badge, int(stock), image_path)
    )
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

    row = database.query("SELECT image FROM products WHERE id = ?", (product_id,))
    image_path = row[0]['image'] if row else ''

    file = request.files.get('image')
    if file and file.filename:
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filename   = file.filename
        image_path = f"uploads/{filename}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    database.query(
        "UPDATE products SET name=?, description=?, price=?, badge=?, stock=?, image=? WHERE id=?",
        (name, description, float(price), badge, int(stock), image_path, product_id)
    )
    return redirect(url_for('admin'))


# ─── ADMIN: DELETE ────────────────────────────────────────────────────────────

@app.route('/admin/productos/<int:product_id>/eliminar', methods=['POST'])
@admin_required
def delete_product(product_id):
    database.query("DELETE FROM products WHERE id = ?", (product_id,))
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)