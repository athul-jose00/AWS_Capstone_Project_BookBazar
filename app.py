from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

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
        'summary': 'A classic novel of the Jazz Age that tells the story of the mysteriously wealthy Jay Gatsby and his love for Daisy Buchanan.',
        'seller': {'name': 'ClassicBooks Co.', 'contact': 'classic@bookseller.example.com'},
        'price': 10.99,
        'genre': 'Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Gatsby'
    },
    {
        'id': 2,
        'title': '1984',
        'author': 'George Orwell',
        'summary': 'A dystopian social science fiction novel and cautionary tale about surveillance and totalitarianism.',
        'seller': {'name': 'Dystopia Books', 'contact': 'sales@dystopiabooks.example.com'},
        'price': 8.99,
        'genre': 'Sci-Fi',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=1984'
    },
    {
        'id': 3,
        'title': 'The Hobbit',
        'author': 'J.R.R. Tolkien',
        'summary': 'Bilbo Baggins embarks on a grand adventure with a group of dwarves to reclaim their mountain home.',
        'seller': {'name': 'MiddleEarth Books', 'contact': 'hobbit@middleearth.example.com'},
        'price': 12.99,
        'genre': 'Sci-Fi',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Hobbit'
    },
    {
        'id': 4,
        'title': 'Clean Code',
        'author': 'Robert C. Martin',
        'summary': 'A handbook of agile software craftsmanship, focusing on writing readable, maintainable code.',
        'seller': {'name': 'TechReads', 'contact': 'support@techreads.example.com'},
        'price': 29.99,
        'genre': 'Non-Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Code'
    },
    {
        'id': 5,
        'title': 'Design Patterns',
        'author': 'Gang of Four',
        'summary': 'Elements of reusable object-oriented software — classic reference for software design patterns.',
        'seller': {'name': 'Patterns Shop', 'contact': 'info@patternsshop.example.com'},
        'price': 35.50,
        'genre': 'Non-Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Patterns'
    },
    {
        'id': 6,
        'title': 'The Alchemist',
        'author': 'Paulo Coelho',
        'summary': 'A philosophical tale about following your dreams and listening to your heart on the journey of life.',
        'seller': {'name': 'Inspirations Ltd', 'contact': 'hello@inspirations.example.com'},
        'price': 9.99,
        'genre': 'Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Alchemist'
    }
]


@app.route('/')
def index():
    # Show header actions (Get Started) on the public landing page
    return render_template('index.html')


@app.route('/auth')
def auth_page():
    return render_template('auth.html')


@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role') or 'customer'

    if not email or not password:
        flash('Email and password are required.', 'error')
        return redirect(url_for('index'))

    if email in USERS:
        flash('Account already exists. Please log in.', 'error')
        return redirect(url_for('index'))
    USERS[email] = {
        'name': name or '',
        'password': generate_password_hash(password),
        'role': role
    }
    # Initialize seller-specific containers
    if role == 'seller':
        USERS[email]['books'] = []
        USERS[email]['received_orders'] = []
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

    # Check if regular user (customer or seller)
    user = USERS.get(email)
    if user and check_password_hash(user.get('password', ''), password):
        role = user.get('role', 'customer')
        session['user'] = {
            'email': email,
            'name': user.get('name', ''),
            'is_admin': False,
            'role': role
        }
        # restore user's persisted cart into session if present
        stored_cart = USERS.get(email, {}).get('cart', {})
        session['cart'] = stored_cart or {}
        flash('Logged in successfully.', 'success')
        # Redirect sellers to seller dashboard
        if role == 'seller':
            return redirect(url_for('seller_dashboard'))
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
    # if seller, go to seller dashboard
    if user.get('role') == 'seller':
        return redirect(url_for('seller_dashboard'))
    return render_template('customer_dashboard.html', user=user, books=MOCK_BOOKS)


@app.route('/browse')
def browse():
    # Public browse page that renders the customer dashboard view but
    # does not redirect sellers. Useful so sellers can access the browse UI.
    user = session.get('user')
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


@app.route('/seller/dashboard')
def seller_dashboard():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))
    if user.get('role') != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('dashboard'))

    email = user.get('email')
    # Load seller-specific books and orders from USERS store (only books this seller added)
    seller_obj = USERS.get(email, {})
    seller_books = seller_obj.get('books', [])
    seller_orders = list(reversed(seller_obj.get('received_orders', [])))
    return render_template('seller_dashboard.html', user=user, books=seller_books, orders=seller_orders)


@app.route('/seller/add-book', methods=['GET', 'POST'])
def seller_add_book():
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        price = float(request.form.get('price') or 0)
        summary = request.form.get('summary') or ''
        genre = request.form.get('genre') or ''
        cover = request.form.get('cover_url') or ''
        # id assignment
        next_id = max((b.get('id', 0) for b in MOCK_BOOKS), default=0) + 1
        email = user.get('email')
        book = {
            'id': next_id,
            'title': title,
            'author': author,
            'summary': summary,
            'seller': {'name': user.get('name') or email, 'contact': email},
            'price': price,
            'genre': genre,
            'cover_url': cover or f'https://placehold.co/150x220/e0e0e0/333333?text={title[:8]}'
        }
        MOCK_BOOKS.append(book)
        # also track under seller user object
        email = user.get('email')
        seller_obj = USERS.get(email, {})
        seller_books = seller_obj.get('books', [])
        seller_books.append(book)
        seller_obj['books'] = seller_books
        USERS[email] = seller_obj
        flash('Book added to store.', 'success')
        return redirect(url_for('seller_dashboard'))

    return render_template('seller_add_book.html', user=user)


@app.route('/seller/book/<int:book_id>/edit', methods=['GET', 'POST'])
def seller_edit_book(book_id):
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('index'))

    book = _find_book(book_id)
    if not book:
        flash('Book not found.', 'error')
        return redirect(url_for('seller_dashboard'))

    # ensure seller owns this book
    seller_contact = book.get('seller', {}).get('contact')
    if seller_contact != user.get('email'):
        flash('You are not authorized to edit this book.', 'error')
        return redirect(url_for('seller_dashboard'))

    if request.method == 'POST':
        # update fields
        book['title'] = request.form.get('title') or book.get('title')
        book['author'] = request.form.get('author') or book.get('author')
        try:
            book['price'] = float(request.form.get(
                'price') or book.get('price', 0))
        except Exception:
            pass
        book['summary'] = request.form.get('summary') or book.get('summary')
        book['genre'] = request.form.get('genre') or book.get('genre')
        cover = request.form.get('cover_url')
        if cover:
            book['cover_url'] = cover

        # update seller's book list copy
        email = user.get('email')
        seller_obj = USERS.get(email, {})
        seller_books = seller_obj.get('books', [])
        for i, b in enumerate(seller_books):
            if int(b.get('id')) == int(book_id):
                seller_books[i] = book
                break
        seller_obj['books'] = seller_books
        USERS[email] = seller_obj

        flash('Book updated.', 'success')
        return redirect(url_for('seller_dashboard'))

    return render_template('seller_add_book.html', user=user, book=book)


@app.route('/seller/book/<int:book_id>/delete', methods=['POST'])
def seller_delete_book(book_id):
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('index'))

    book = _find_book(book_id)
    if not book:
        flash('Book not found.', 'error')
        return redirect(url_for('seller_dashboard'))

    # only seller who added the book can delete
    seller_contact = book.get('seller', {}).get('contact')
    if seller_contact != user.get('email'):
        flash('You are not authorized to delete this book.', 'error')
        return redirect(url_for('seller_dashboard'))

    # remove from global list
    global MOCK_BOOKS
    MOCK_BOOKS = [b for b in MOCK_BOOKS if int(b.get('id')) != int(book_id)]

    # remove from seller's list
    email = user.get('email')
    seller_obj = USERS.get(email, {})
    seller_books = [b for b in seller_obj.get(
        'books', []) if int(b.get('id')) != int(book_id)]
    seller_obj['books'] = seller_books
    USERS[email] = seller_obj

    flash('Book deleted.', 'success')
    return redirect(url_for('seller_dashboard'))


@app.route('/seller/orders')
def seller_orders():
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('index'))
    email = user.get('email')
    seller_obj = USERS.get(email, {})
    orders = list(reversed(seller_obj.get('received_orders', [])))
    return render_template('seller_orders.html', user=user, orders=orders)


@app.route('/seller/order/<order_id>/status', methods=['POST'])
def seller_update_order_status(order_id):
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        return jsonify({'error': 'access_denied'}), 403
    email = user.get('email')
    seller_obj = USERS.get(email, {})
    orders = seller_obj.get('received_orders', [])
    new_status = request.form.get('status')
    updated = False
    for o in orders:
        if o.get('id') == order_id:
            o['status'] = new_status
            updated = True
            break
    seller_obj['received_orders'] = orders
    USERS[email] = seller_obj
    if updated:
        flash('Order status updated.', 'success')
        return redirect(url_for('seller_orders'))
    return jsonify({'error': 'not_found'}), 404


@app.route('/logout')
def logout():
    # persist cart to user's store before logout (if logged in)
    user = session.get('user')
    if user:
        email = user.get('email')
        if email:
            user_obj = USERS.get(email, {})
            user_obj['cart'] = session.get('cart', {})
            USERS[email] = user_obj
    session.pop('user', None)
    flash('Logged out.', 'success')
    return redirect(url_for('index'))


@app.route('/profile')
def profile():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))
    # ensure user addresses exist in USERS store
    email = user.get('email')
    stored = USERS.get(email, {})
    addresses = stored.get('addresses', [])
    return render_template('profile.html', user=user, addresses=addresses)


@app.route('/profile/address', methods=['POST'])
def add_address_profile():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))
    email = user.get('email')
    addr = {
        'name': request.form.get('name') or user.get('name') or '',
        'line1': request.form.get('line1', ''),
        'line2': request.form.get('line2', ''),
        'city': request.form.get('city', ''),
        'state': request.form.get('state', ''),
        'zip': request.form.get('zip', ''),
        'country': request.form.get('country', ''),
        'phone': request.form.get('phone', ''),
    }
    user_obj = USERS.get(email)
    if user_obj is None:
        flash('User not found.', 'error')
        return redirect(url_for('profile'))
    addrs = user_obj.get('addresses', [])
    addrs.append(addr)
    user_obj['addresses'] = addrs
    USERS[email] = user_obj
    flash('Address added to your profile.', 'success')
    return redirect(url_for('profile'))


@app.route('/payment', methods=['GET', 'POST'])
def payment():
    user = session.get('user')
    if not user:
        flash('Please sign in to checkout.', 'error')
        return redirect(url_for('auth_page'))

    email = user.get('email')
    user_obj = USERS.get(email, {})
    addresses = user_obj.get('addresses', [])

    if request.method == 'POST':
        # collect address from form
        addr_id = request.form.get('existing_address')
        if addr_id:
            try:
                addr = addresses[int(addr_id)]
            except Exception:
                addr = None
        else:
            addr = {
                'name': request.form.get('name') or user.get('name') or '',
                'line1': request.form.get('line1', ''),
                'line2': request.form.get('line2', ''),
                'city': request.form.get('city', ''),
                'state': request.form.get('state', ''),
                'zip': request.form.get('zip', ''),
                'country': request.form.get('country', ''),
                'phone': request.form.get('phone', ''),
            }
            if request.form.get('save_address'):
                addrs = user_obj.get('addresses', [])
                addrs.append(addr)
                user_obj['addresses'] = addrs
                USERS[email] = user_obj

        # build order from cart
        cart = session.get('cart', {})
        if not cart:
            flash('Your cart is empty.', 'error')
            return redirect(url_for('cart'))

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
                'qty': qty,
                'price': book.get('price'),
                'subtotal': subtotal,
            })

        order_id = f"ORD-{int(datetime.utcnow().timestamp()*1000)}"
        order = {
            'id': order_id,
            'created_at': datetime.utcnow().isoformat(),
            'status': 'Placed',
            'items': items,
            'total': total,
            'shipping_address': addr,
        }

        user_orders = user_obj.get('orders', [])
        user_orders.append(order)
        user_obj['orders'] = user_orders
        USERS[email] = user_obj

        # Also distribute order copies to each seller involved so sellers can manage their orders
        # Group items by seller contact
        sellers = {}
        for it in items:
            book = _find_book(it.get('id'))
            if not book:
                continue
            seller_info = book.get('seller', {}) or {}
            seller_email = seller_info.get('contact')
            if not seller_email:
                continue
            sellers.setdefault(seller_email, {'items': [], 'total': 0.0})
            sellers[seller_email]['items'].append(it)
            sellers[seller_email]['total'] += it.get('subtotal', 0.0)

        for seller_email, payload in sellers.items():
            seller_user = USERS.get(seller_email)
            if not seller_user:
                # no seller account registered with that contact email; skip
                continue
            seller_orders = seller_user.get('received_orders', [])
            seller_order = {
                'id': order_id,
                'original_order_id': order_id,
                'created_at': order.get('created_at'),
                'status': 'Placed',
                'items': payload['items'],
                'total': payload['total'],
                'buyer': {'email': email, 'name': user.get('name')},
                'shipping_address': addr,
            }
            seller_orders.append(seller_order)
            seller_user['received_orders'] = seller_orders
            USERS[seller_email] = seller_user

        flash('Order placed (Cash on Delivery).', 'success')
        session['cart'] = {}
        return redirect(url_for('orders'))

    return render_template('payment.html', user=user, addresses=addresses)


@app.route('/orders')
def orders():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))
    email = user.get('email')
    user_obj = USERS.get(email, {})
    orders_list = user_obj.get('orders', [])
    # show most recent first
    orders_list = list(reversed(orders_list))
    return render_template('orders.html', user=user, orders=orders_list)


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
    # also expose the current user (if any) to all templates
    return {'cart_count': count, 'wishlist_ids': wishlist_ids, 'user': session.get('user')}


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
    # persist cart for logged in user
    user = session.get('user')
    if user:
        email = user.get('email')
        user_obj = USERS.get(email)
        if user_obj is not None:
            user_obj['cart'] = cart
            USERS[email] = user_obj
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


@app.route('/cart/update/<int:book_id>', methods=['POST'])
def update_cart(book_id):
    user = session.get('user')
    if not user:
        return jsonify({'error': 'login_required'}), 401

    op = request.form.get('op') or request.json.get(
        'op') if request.is_json else request.form.get('op')
    cart = session.get('cart', {})
    key = str(book_id)
    qty = int(cart.get(key, 0))
    if op == 'inc':
        qty += 1
    elif op == 'dec':
        qty = max(0, qty - 1)
    else:
        try:
            q = int(request.form.get('qty', request.json.get(
                'qty') if request.is_json else 0))
            qty = max(0, q)
        except Exception:
            pass

    if qty <= 0:
        cart.pop(key, None)
    else:
        cart[key] = qty
    session['cart'] = cart
    # persist cart for logged-in user
    user = session.get('user')
    if user:
        email = user.get('email')
        user_obj = USERS.get(email, {})
        user_obj['cart'] = cart
        USERS[email] = user_obj

    # Recalculate totals
    total = 0.0
    items_count = 0
    for bid, q in cart.items():
        book = _find_book(bid)
        if not book:
            continue
        subtotal = int(q) * float(book.get('price', 0))
        total += subtotal
        items_count += int(q)

    # item subtotal for this book
    book = _find_book(book_id)
    line_subtotal = 0.0
    if book and str(book_id) in cart:
        line_subtotal = int(cart.get(str(book_id), 0)) * \
            float(book.get('price', 0))

    return jsonify({
        'qty': int(cart.get(key, 0)),
        'line_subtotal': round(line_subtotal, 2),
        'total': round(total, 2),
        'cart_count': items_count,
    })


@app.route('/cart/remove/<int:book_id>', methods=['POST'])
def remove_from_cart(book_id):
    user = session.get('user')
    if not user:
        return jsonify({'error': 'login_required'}), 401

    cart = session.get('cart', {})
    key = str(book_id)
    if key in cart:
        cart.pop(key, None)
        session['cart'] = cart
        # persist
        email = user.get('email')
        if email:
            user_obj = USERS.get(email, {})
            user_obj['cart'] = cart
            USERS[email] = user_obj

    # recalc
    total = 0.0
    items_count = 0
    for bid, q in cart.items():
        book = _find_book(bid)
        if not book:
            continue
        subtotal = int(q) * float(book.get('price', 0))
        total += subtotal
        items_count += int(q)

    return jsonify({'total': round(total, 2), 'cart_count': items_count})


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
    wishlist = session.get('wishlist', [])
    # wishlist stored as list of string ids in session
    for bid in wishlist:
        try:
            book = _find_book(int(bid))
        except Exception:
            book = None
        if book:
            wishlist_items.append(book)

    return render_template('wishlist.html', user=user, items=wishlist_items)


if __name__ == '__main__':
    app.run(debug=True)
