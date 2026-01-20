from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'dev-secret-change-me'


USERS = {}
ADMIN_USERS = {
    'admin@bookbazaar.com': {
        'name': 'Administrator',
        'password': generate_password_hash('admin123')
    }
}

MOCK_BOOKS = [
    {
        'id': 1,
        'title': 'The Great Gatsby',
        'author': 'F. Scott Fitzgerald',
        'price': 10.99,
        'genre': 'Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Gatsby'
    },
    {
        'id': 2,
        'title': '1984',
        'author': 'George Orwell',
        'price': 8.99,
        'genre': 'Sci-Fi',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=1984'
    },
    {
        'id': 3,
        'title': 'The Hobbit',
        'author': 'J.R.R. Tolkien',
        'price': 12.99,
        'genre': 'Sci-Fi',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Hobbit'
    },
    {
        'id': 4,
        'title': 'Clean Code',
        'author': 'Robert C. Martin',
        'price': 29.99,
        'genre': 'Non-Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Code'
    },
    {
        'id': 5,
        'title': 'Design Patterns',
        'author': 'Gang of Four',
        'price': 35.50,
        'genre': 'Non-Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Patterns'
    },
    {
        'id': 6,
        'title': 'The Alchemist',
        'author': 'Paulo Coelho',
        'price': 9.99,
        'genre': 'Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Alchemist'
    }
]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/auth')
def auth_page():
    return render_template('auth.html')


@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        flash('Email and password are required.', 'error')
        return redirect(url_for('index'))

    if email in USERS:
        flash('Account already exists. Please log in.', 'error')
        return redirect(url_for('index'))
    USERS[email] = {
        'name': name or '',
        'password': generate_password_hash(password)
    }
    flash('Account created successfully. Please sign in.', 'success')
    return redirect(url_for('auth_page'))


@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    # Check if admin
    admin = ADMIN_USERS.get(email)
    if admin and check_password_hash(admin.get('password', ''), password):
        session['user'] = {
            'email': email,
            'name': admin.get('name', ''),
            'is_admin': True
        }
        flash('Welcome Admin!', 'success')
        return redirect(url_for('admin_dashboard'))

    # Check if regular user
    user = USERS.get(email)
    if user and check_password_hash(user.get('password', ''), password):
        session['user'] = {
            'email': email,
            'name': user.get('name', ''),
            'is_admin': False
        }
        flash('Logged in successfully.', 'success')
        return redirect(url_for('dashboard'))

    flash('Invalid credentials.', 'error')
    return redirect(url_for('auth_page'))


@app.route('/dashboard')
def dashboard():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))
    if user.get('is_admin'):
        return redirect(url_for('admin_dashboard'))
    return render_template('customer_dashboard.html', user=user, books=MOCK_BOOKS)


@app.route('/admin/dashboard')
def admin_dashboard():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    # Get statistics
    stats = {
        'total_users': len(USERS),
        'total_admins': len(ADMIN_USERS),
        'total_books': 0,  # Placeholder
        'total_orders': 0  # Placeholder
    }

    return render_template('admin_dashboard.html', user=user, stats=stats)


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/profile')
def profile():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))
    return render_template('profile.html', user=user)


@app.route('/orders')
def orders():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))
    # Placeholder orders list
    sample_orders = []
    return render_template('orders.html', user=user, orders=sample_orders)


@app.context_processor
def cart_context():
    cart = session.get('cart', {})
    # cart stored as {str(book_id): qty}
    try:
        count = sum(int(q) for q in cart.values())
    except Exception:
        count = 0
    wishlist = session.get('wishlist', [])
    try:
        wishlist_ids = {int(x) for x in wishlist}
    except Exception:
        wishlist_ids = set()
    return {'cart_count': count, 'wishlist_ids': wishlist_ids}


def _find_book(book_id):
    for b in MOCK_BOOKS:
        if int(b.get('id')) == int(book_id):
            return b
    return None


@app.route('/cart/add/<int:book_id>', methods=['POST'])
def add_to_cart(book_id):
    user = session.get('user')
    if not user:
        flash('Please sign in to add items to cart.', 'error')
        return redirect(url_for('index'))

    book = _find_book(book_id)
    if not book:
        flash('Book not found.', 'error')
        return redirect(url_for('dashboard'))

    cart = session.get('cart', {})
    key = str(book_id)
    cart[key] = int(cart.get(key, 0)) + 1
    session['cart'] = cart
    flash(f"Added '{book.get('title')}' to cart.", 'success')

    # Redirect back to referring page if available
    ref = request.referrer
    if ref:
        return redirect(ref)
    return redirect(url_for('dashboard'))


@app.route('/cart')
def cart():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))

    cart = session.get('cart', {})
    items = []
    total = 0.0
    for bid, qty in cart.items():
        book = _find_book(bid)
        if not book:
            continue
        qty = int(qty)
        subtotal = qty * float(book.get('price', 0))
        total += subtotal
        items.append({
            'id': book.get('id'),
            'title': book.get('title'),
            'author': book.get('author'),
            'price': book.get('price'),
            'qty': qty,
            'subtotal': subtotal,
        })

    return render_template('cart.html', user=user, items=items, total=total, hide_header_actions=True)


@app.route('/wishlist/toggle/<int:book_id>', methods=['POST'])
def toggle_wishlist(book_id):
    user = session.get('user')
    if not user:
        return jsonify({'error': 'login_required'}), 401

    book = _find_book(book_id)
    if not book:
        return jsonify({'error': 'not_found'}), 404

    wishlist = session.get('wishlist', [])
    # store ids as strings for session serialization
    key = str(book_id)
    added = False
    if key in wishlist:
        wishlist.remove(key)
        added = False
    else:
        wishlist.append(key)
        added = True
    session['wishlist'] = wishlist

    return jsonify({'added': added, 'count': len(wishlist)})


@app.route('/wishlist')
def wishlist():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))
    wishlist_items = []
    return render_template('wishlist.html', user=user, items=wishlist_items)


if __name__ == '__main__':
    app.run(debug=True)
