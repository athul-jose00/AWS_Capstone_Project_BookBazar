from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'dev-secret-change-me'


USERS = {}
ADMIN_USERS = {
    'admin@bookbazaar.com': {
        'name': 'Administrator',
        'password': generate_password_hash('admin@bookbazaar.com')
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
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Gatsby',
        'stock': 10
    },
    {
        'id': 2,
        'title': '1984',
        'author': 'George Orwell',
        'summary': 'A dystopian social science fiction novel and cautionary tale about surveillance and totalitarianism.',
        'seller': {'name': 'Dystopia Books', 'contact': 'sales@dystopiabooks.example.com'},
        'price': 8.99,
        'genre': 'Sci-Fi',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=1984',
        'stock': 10
    },
    {
        'id': 3,
        'title': 'The Hobbit',
        'author': 'J.R.R. Tolkien',
        'summary': 'Bilbo Baggins embarks on a grand adventure with a group of dwarves to reclaim their mountain home.',
        'seller': {'name': 'MiddleEarth Books', 'contact': 'hobbit@middleearth.example.com'},
        'price': 12.99,
        'genre': 'Sci-Fi',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Hobbit',
        'stock': 10
    },
    {
        'id': 4,
        'title': 'Clean Code',
        'author': 'Robert C. Martin',
        'summary': 'A handbook of agile software craftsmanship, focusing on writing readable, maintainable code.',
        'seller': {'name': 'TechReads', 'contact': 'support@techreads.example.com'},
        'price': 29.99,
        'genre': 'Non-Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Code',
        'stock': 10
    },
    {
        'id': 5,
        'title': 'Design Patterns',
        'author': 'Gang of Four',
        'summary': 'Elements of reusable object-oriented software — classic reference for software design patterns.',
        'seller': {'name': 'Patterns Shop', 'contact': 'info@patternsshop.example.com'},
        'price': 35.50,
        'genre': 'Non-Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Patterns',
        'stock': 10
    },
    {
        'id': 6,
        'title': 'The Alchemist',
        'author': 'Paulo Coelho',
        'summary': 'A philosophical tale about following your dreams and listening to your heart on the journey of life.',
        'seller': {'name': 'Inspirations Ltd', 'contact': 'hello@inspirations.example.com'},
        'price': 9.99,
        'genre': 'Fiction',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Alchemist',
        'stock': 10
    }
]

# --- Demo/test data: a sample seller, buyer, two books and one order (for local testing) ---
demo_seller_email = 'seller_demo@example.com'
demo_buyer_email = 'buyer_demo@example.com'

# create demo seller account if not present
if demo_seller_email not in USERS:
    USERS[demo_seller_email] = {
        'name': 'Demo Seller',
        'password': generate_password_hash('seller_demo@example.com'),
        'role': 'seller',
        'books': [],
        'received_orders': [],
        'wishlist': []
    }

# create demo buyer account if not present
if demo_buyer_email not in USERS:
    USERS[demo_buyer_email] = {
        'name': 'Demo Buyer',
        'password': generate_password_hash('buyer_demo@example.com'),
        'role': 'customer',
        'cart': {},
        'orders': [],
        'addresses': [],
        'wishlist': []
    }

# Add two demo books (ids chosen after existing ones)
_next_id = max((b.get('id', 0) for b in MOCK_BOOKS), default=0) + 1
demo_book_a = {
    'id': _next_id,
    'title': "Demo: Learning Flask",
    'author': 'Demo Author',
    'summary': 'A short demo book about building apps with Flask.',
    'seller': {'name': 'Demo Seller', 'contact': demo_seller_email},
    'price': 7.00,
    'genre': 'Programming',
    'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Flask',
    'stock': 5
}
_next_id += 1
demo_book_b = {
    'id': _next_id,
    'title': "Demo: Web UI Design",
    'author': 'Design Demo',
    'summary': 'A demo book about designing simple web UIs.',
    'seller': {'name': 'Demo Seller', 'contact': demo_seller_email},
    'price': 15.00,
    'genre': 'Design',
    'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Design',
    'stock': 5
}

# Append to global catalog and to seller's list
MOCK_BOOKS.append(demo_book_a)
MOCK_BOOKS.append(demo_book_b)
USERS[demo_seller_email].setdefault(
    'books', []).extend([demo_book_a, demo_book_b])

# Create a demo order from demo buyer purchasing both books
order_id = 'ORD-DEMO-1'
order_created = datetime.utcnow().isoformat()
items = []
items.append({'id': demo_book_a['id'], 'title': demo_book_a['title'], 'qty': 1,
             'price': demo_book_a['price'], 'subtotal': demo_book_a['price']})
items.append({'id': demo_book_b['id'], 'title': demo_book_b['title'], 'qty': 2,
             'price': demo_book_b['price'], 'subtotal': demo_book_b['price'] * 2})
total = sum(it['subtotal'] for it in items)

demo_order = {
    'id': order_id,
    'created_at': order_created,
    'status': 'Placed',
    'items': items,
    'total': total,
    'shipping_address': {
        'name': 'Demo Buyer',
        'line1': '123 Demo Lane',
        'city': 'Demo City',
        'state': 'DM',
        'zip': '00000',
        'country': 'Demo'
    }
}

# Attach order to buyer's orders
USERS[demo_buyer_email].setdefault('orders', []).append(demo_order)

# Distribute order entries to the seller's received_orders (grouped per seller)
seller_payload = {
    'id': order_id,
    'original_order_id': order_id,
    'created_at': order_created,
    'status': 'Placed',
    'items': items,
    'total': total,
    'buyer': {'email': demo_buyer_email, 'name': 'Demo Buyer'},
    'shipping_address': demo_order['shipping_address']
}
USERS[demo_seller_email].setdefault(
    'received_orders', []).append(seller_payload)


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
        'role': role,
        'cart': {},
        'wishlist': [],
        'orders': [],
        'addresses': []
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
        # restore and merge user's persisted wishlist (preserve any items added while anonymous)
        stored_wishlist = USERS.get(email, {}).get('wishlist', []) or []
        session_wishlist = session.get('wishlist', []) or []
        # merge, preserving order and uniqueness
        merged = []
        for k in (session_wishlist + stored_wishlist):
            if k not in merged:
                merged.append(k)
        session['wishlist'] = merged
        # persist merged back to user store
        user_obj = USERS.get(email, {})
        user_obj['wishlist'] = merged
        USERS[email] = user_obj
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

    # Calculate statistics
    total_books = len(MOCK_BOOKS)
    total_orders = 0
    for user_data in USERS.values():
        total_orders += len(user_data.get('orders', []))
    
    stats = {
        'total_users': len(USERS),
        'total_admins': len(ADMIN_USERS),
        'total_books': total_books,
        'total_orders': total_orders
    }

    return render_template('admin_dashboard.html', user=user, stats=stats)


@app.route('/admin/users')
def admin_users():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    search = request.args.get('search', '').lower()
    role_filter = request.args.get('role', '')

    users_list = []
    for email, user_data in USERS.items():
        if search and search not in email.lower() and search not in user_data.get('name', '').lower():
            continue
        if role_filter and user_data.get('role', 'customer') != role_filter:
            continue
        
        user_info = {
            'email': email,
            'name': user_data.get('name', 'Unknown'),
            'role': user_data.get('role', 'customer'),
            'created_at': 'N/A',
            'orders': len(user_data.get('orders', [])),
            'books': len(user_data.get('books', []))
        }
        users_list.append(user_info)

    users_list.sort(key=lambda x: x['email'])
    return render_template('admin_users.html', user=user, users=users_list, search=search, role_filter=role_filter)


@app.route('/admin/user/<email>/delete', methods=['POST'])
def admin_delete_user(email):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    if email not in USERS:
        flash('User not found.', 'error')
        return redirect(url_for('admin_users'))

    user_data = USERS[email]
    
    # Remove user's books from MOCK_BOOKS
    user_books = user_data.get('books', [])
    for book in user_books:
        MOCK_BOOKS[:] = [b for b in MOCK_BOOKS if b['id'] != book['id']]
    
    # Delete user
    del USERS[email]
    flash(f'User {email} has been deleted successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/user/<email>')
def admin_user_details(email):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    if email not in USERS:
        flash('User not found.', 'error')
        return redirect(url_for('admin_users'))

    user_data = USERS[email]
    user_info = {
        'email': email,
        'name': user_data.get('name', 'Unknown'),
        'role': user_data.get('role', 'customer'),
        'orders': user_data.get('orders', []),
        'received_orders': user_data.get('received_orders', []),
        'books': user_data.get('books', []),
        'wishlist': user_data.get('wishlist', []),
        'cart': user_data.get('cart', {})
    }
    
    return render_template('admin_user_details.html', user=user, user_info=user_info, user_email=email)


@app.route('/admin/books')
def admin_books():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    search = request.args.get('search', '').lower()
    genre_filter = request.args.get('genre', '')

    books_list = []
    for book in MOCK_BOOKS:
        if search and search not in book.get('title', '').lower() and search not in book.get('author', '').lower():
            continue
        if genre_filter and book.get('genre', '') != genre_filter:
            continue
        books_list.append(book)

    # Get unique genres
    genres = sorted(set(b.get('genre', '') for b in MOCK_BOOKS if b.get('genre', '')))
    
    return render_template('admin_books.html', user=user, books=books_list, genres=genres, search=search, genre_filter=genre_filter)


@app.route('/admin/book/<int:book_id>', methods=['GET', 'POST'])
def admin_book_details(book_id):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    book = _find_book(book_id)
    if not book:
        flash('Book not found.', 'error')
        return redirect(url_for('admin_books'))

    if request.method == 'POST':
        book['title'] = request.form.get('title', book['title'])
        book['author'] = request.form.get('author', book['author'])
        book['price'] = float(request.form.get('price', book['price']))
        book['summary'] = request.form.get('summary', book['summary'])
        book['genre'] = request.form.get('genre', book['genre'])
        book['stock'] = int(request.form.get('stock', book.get('stock', 0)))
        book['cover_url'] = request.form.get('cover_url', book['cover_url'])
        flash('Book updated successfully.', 'success')
        return redirect(url_for('admin_books'))

    return render_template('admin_book_details.html', user=user, book=book)


@app.route('/admin/book/<int:book_id>/delete', methods=['POST'])
def admin_delete_book(book_id):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    book = _find_book(book_id)
    if not book:
        flash('Book not found.', 'error')
        return redirect(url_for('admin_books'))

    title = book['title']
    MOCK_BOOKS[:] = [b for b in MOCK_BOOKS if b['id'] != book_id]
    
    # Remove from sellers' books list
    for user_data in USERS.values():
        user_data['books'] = [b for b in user_data.get('books', []) if b['id'] != book_id]
    
    flash(f'Book "{title}" has been deleted successfully.', 'success')
    return redirect(url_for('admin_books'))


@app.route('/admin/sellers')
def admin_sellers():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    sellers = []
    for email, user_data in USERS.items():
        if user_data.get('role') == 'seller':
            seller_info = {
                'email': email,
                'name': user_data.get('name', 'Unknown'),
                'books': len(user_data.get('books', [])),
                'orders': len(user_data.get('received_orders', [])),
                'status': 'Active'
            }
            sellers.append(seller_info)

    sellers.sort(key=lambda x: x['email'])
    return render_template('admin_sellers.html', user=user, sellers=sellers)


@app.route('/admin/seller/<email>/details')
def admin_seller_details(email):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    if email not in USERS or USERS[email].get('role') != 'seller':
        flash('Seller not found.', 'error')
        return redirect(url_for('admin_sellers'))

    seller_data = USERS[email]
    seller_info = {
        'email': email,
        'name': seller_data.get('name', 'Unknown'),
        'books': seller_data.get('books', []),
        'received_orders': seller_data.get('received_orders', []),
        'total_revenue': sum(float(o.get('total', 0) or 0) for o in seller_data.get('received_orders', []))
    }

    return render_template('admin_seller_details.html', user=user, seller=seller_info)


@app.route('/admin/orders')
def admin_orders():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    status_filter = request.args.get('status', '')
    
    all_orders = []
    for email, user_data in USERS.items():
        for order in user_data.get('orders', []):
            order_info = {
                'id': order.get('id', ''),
                'customer': user_data.get('name', email),
                'customer_email': email,
                'status': order.get('status', 'Unknown'),
                'total': order.get('total', 0),
                'created_at': order.get('created_at', 'N/A'),
                'items_count': len(order.get('items', []))
            }
            all_orders.append(order_info)

    if status_filter:
        all_orders = [o for o in all_orders if o['status'] == status_filter]

    all_orders.sort(key=lambda x: x['created_at'], reverse=True)
    statuses = sorted(set(o['status'] for o in all_orders))
    
    return render_template('admin_orders.html', user=user, orders=all_orders, statuses=statuses, status_filter=status_filter)


@app.route('/admin/order/<order_id>')
def admin_order_details(order_id):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    order_info = None
    customer_email = None
    customer_name = None

    for email, user_data in USERS.items():
        for order in user_data.get('orders', []):
            if order.get('id') == order_id:
                order_info = order
                customer_email = email
                customer_name = user_data.get('name', email)
                break
        if order_info:
            break

    if not order_info:
        flash('Order not found.', 'error')
        return redirect(url_for('admin_orders'))

    return render_template('admin_order_details.html', user=user, order=order_info, customer_email=customer_email, customer_name=customer_name)


@app.route('/admin/analytics')
def admin_analytics():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    # Calculate analytics data
    total_users = len(USERS)
    total_customers = sum(1 for u in USERS.values() if u.get('role', 'customer') == 'customer')
    total_sellers = sum(1 for u in USERS.values() if u.get('role') == 'seller')
    total_books = len(MOCK_BOOKS)
    
    total_revenue = 0.0
    total_orders = 0
    completed_orders = 0
    
    for user_data in USERS.values():
        for order in user_data.get('orders', []):
            total_orders += 1
            total_revenue += float(order.get('total', 0) or 0)
            if order.get('status') == 'Delivered':
                completed_orders += 1

    # Genre breakdown
    genre_stats = {}
    for book in MOCK_BOOKS:
        genre = book.get('genre', 'Unknown')
        genre_stats[genre] = genre_stats.get(genre, 0) + 1

    # Status breakdown
    status_stats = {}
    for user_data in USERS.values():
        for order in user_data.get('orders', []):
            status = order.get('status', 'Unknown')
            status_stats[status] = status_stats.get(status, 0) + 1

    analytics = {
        'total_users': total_users,
        'total_customers': total_customers,
        'total_sellers': total_sellers,
        'total_books': total_books,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'total_revenue': round(total_revenue, 2),
        'average_order_value': round(total_revenue / max(total_orders, 1), 2),
        'genre_stats': genre_stats,
        'status_stats': status_stats
    }

    return render_template('admin_analytics.html', user=user, analytics=analytics)


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

    # compute overview stats for seller landing dashboard
    total_books = len(seller_books)
    total_orders = len(seller_orders)
    try:
        revenue = sum(float(o.get('total', 0) or 0) for o in seller_orders)
    except Exception:
        revenue = 0.0
    revenue = round(revenue, 2)

    stats = {
        'total_books': total_books,
        'total_orders': total_orders,
        'revenue': revenue,
    }

    return render_template('seller_dashboard.html', user=user, books=seller_books, orders=seller_orders, stats=stats)


@app.route('/seller/books')
def seller_books():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))
    if user.get('role') != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('dashboard'))

    email = user.get('email')
    seller_obj = USERS.get(email, {})
    seller_books = seller_obj.get('books', [])
    return render_template('seller_books.html', user=user, books=seller_books)


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
        try:
            stock = int(request.form.get('stock') or 0)
        except Exception:
            stock = 0
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
            'cover_url': cover or f'https://placehold.co/150x220/e0e0e0/333333?text={title[:8]}',
            'stock': stock
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
        return redirect(url_for('seller_books'))

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
        return redirect(url_for('seller_books'))

    # ensure seller owns this book
    seller_contact = book.get('seller', {}).get('contact')
    if seller_contact != user.get('email'):
        flash('You are not authorized to edit this book.', 'error')
        return redirect(url_for('seller_books'))

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
        try:
            book['stock'] = int(request.form.get(
                'stock') or book.get('stock', 0))
        except Exception:
            pass
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
        return redirect(url_for('seller_books'))

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
        return redirect(url_for('seller_books'))

    # only seller who added the book can delete
    seller_contact = book.get('seller', {}).get('contact')
    if seller_contact != user.get('email'):
        flash('You are not authorized to delete this book.', 'error')
        return redirect(url_for('seller_books'))

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
    return redirect(url_for('seller_books'))


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
            # Also update the buyer's copy of this order so the buyer sees the new status
            buyer_email = o.get('buyer', {}).get('email')
            if buyer_email:
                buyer_obj = USERS.get(buyer_email, {})
                buyer_orders = buyer_obj.get('orders', [])
                for bo in buyer_orders:
                    if bo.get('id') == order_id:
                        bo['status'] = new_status
                buyer_obj['orders'] = buyer_orders
                USERS[buyer_email] = buyer_obj
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
            # persist wishlist as well
            user_obj['wishlist'] = session.get('wishlist', [])
            USERS[email] = user_obj
    # clear session-scoped cart and wishlist to avoid leaking between accounts
    session.pop('cart', None)
    session.pop('wishlist', None)
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
            # check stock availability
            available = int(book.get('stock', 0)) if book.get(
                'stock') is not None else None
            if available is not None and qty > available:
                flash(
                    f"Not enough stock for '{book.get('title')}'. Please adjust your cart.", 'error')
                return redirect(url_for('cart'))
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

        # decrement stock for ordered items and update seller copies
        for it in items:
            book = _find_book(it.get('id'))
            if not book:
                continue
            try:
                new_stock = max(0, int(book.get('stock', 0)) -
                                int(it.get('qty', 0)))
            except Exception:
                new_stock = book.get('stock', 0)
            book['stock'] = new_stock
            # update seller's copy of this book as well
            seller_contact = book.get('seller', {}).get('contact')
            if seller_contact:
                s_user = USERS.get(seller_contact, {})
                s_books = s_user.get('books', [])
                for i, sb in enumerate(s_books):
                    if int(sb.get('id')) == int(book.get('id')):
                        s_books[i]['stock'] = new_stock
                s_user['books'] = s_books
                USERS[seller_contact] = s_user

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

    # enforce stock limits
    available = int(book.get('stock', 0)) if book.get(
        'stock') is not None else None
    cart = session.get('cart', {})
    key = str(book_id)
    current = int(cart.get(key, 0))
    if available is not None and current + 1 > available:
        flash(f"Not enough stock for '{book.get('title')}'.", 'error')
        ref = request.referrer
        if ref:
            return redirect(ref)
        return redirect(url_for('cart'))

    cart[key] = current + 1
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
    # enforce stock limits on increment or direct set
    book = _find_book(book_id)
    try:
        available = int(book.get('stock', 0)) if book and book.get(
            'stock') is not None else None
    except Exception:
        available = None
    if op == 'inc':
        qty += 1
        if available is not None and qty > available:
            qty = available
    elif op == 'dec':
        qty = max(0, qty - 1)
    else:
        try:
            q = int(request.form.get('qty', request.json.get(
                'qty') if request.is_json else 0))
            qty = max(0, q)
            if available is not None and qty > available:
                qty = available
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
    """Toggle wishlist membership for a book.

    Behavior:
    - If the user is anonymous, modify `session['wishlist']` only.
    - If the user is logged in, persist the wishlist into `USERS[email]['wishlist']` as well.
    """
    user = session.get('user')

    book = _find_book(book_id)
    if not book:
        return jsonify({'error': 'not_found'}), 404

    wishlist = session.get('wishlist', []) or []
    # store ids as strings for session serialization
    key = str(book_id)
    added = False
    if key in wishlist:
        wishlist.remove(key)
        added = False
    else:
        wishlist.append(key)
        added = True

    # save back to session
    session['wishlist'] = wishlist

    # if logged-in, persist to user store as well
    if user:
        email = user.get('email')
        if email:
            user_obj = USERS.get(email, {})
            user_obj['wishlist'] = wishlist
            USERS[email] = user_obj

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
