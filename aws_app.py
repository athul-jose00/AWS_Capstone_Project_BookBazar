from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import boto3
import uuid
from decimal import Decimal
import json
import requests
from huggingface_hub import InferenceClient

from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = 'bookbazaar-secret-key-2026'

# Hugging Face Configuration
HF_API_KEY = os.environ.get(
    'HF_TOKEN', 'test')
HF_MODEL = os.environ.get('HF_MODEL', 'Qwen/Qwen2.5-72B-Instruct')
HF_CLIENT = InferenceClient(api_key=HF_API_KEY) if HF_API_KEY else None

# AWS Configuration
REGION = 'us-east-1'

# Initialize AWS services
dynamodb = boto3.resource('dynamodb', region_name=REGION)
sns = boto3.client('sns', region_name=REGION)

# DynamoDB Tables
users_table = dynamodb.Table('BookBazaar_Users')
books_table = dynamodb.Table('BookBazaar_Books')
orders_table = dynamodb.Table('BookBazaar_Orders')

# SNS Topic ARN
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:537124956479:bookbazar_topic'


def send_notification(subject, message):
    try:
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=subject,
            Message=message
        )
    except ClientError as e:
        print(f"Error sending notification: {e}")

# ==================== PUBLIC ROUTES ====================


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
    role = request.form.get('role') or 'customer'

    if not email or not password:
        flash('Email and password are required.', 'error')
        return redirect(url_for('index'))

    # Check if user exists
    if role == 'admin':
        # store admins in the same users table but mark role='admin' to avoid redundant admin table
        response = users_table.get_item(Key={'email': email})
        if 'Item' in response:
            flash('Admin already exists!', 'error')
            return redirect(url_for('auth_page'))

        users_table.put_item(Item={
            'email': email,
            'name': name or '',
            'password': generate_password_hash(password),
            'role': 'admin',
            'created_at': datetime.utcnow().isoformat()
        })
        send_notification("New Admin Signup",
                          f"Admin {name} ({email}) has registered.")
    else:
        response = users_table.get_item(Key={'email': email})
        if 'Item' in response:
            flash('User already exists!', 'error')
            return redirect(url_for('auth_page'))

        users_table.put_item(Item={
            'email': email,
            'name': name or '',
            'password': generate_password_hash(password),
            'role': role,
            'created_at': datetime.utcnow().isoformat()
        })
        send_notification("New User Signup",
                          f"User {name} ({email}) signed up as {role}.")

    flash('Account created successfully. Please sign in.', 'success')
    return redirect(url_for('auth_page'))


@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    # Check user (admins are stored in users_table with role='admin')
    response = users_table.get_item(Key={'email': email})
    if 'Item' in response:
        user = response['Item']
        if check_password_hash(user.get('password', ''), password):
            role = user.get('role', 'customer')
            is_admin = True if role == 'admin' else False
            session['user'] = {
                'email': email,
                'name': user.get('name', ''),
                'is_admin': is_admin,
                'role': role
            }
            session['cart'] = {}
            session['wishlist'] = []

            if is_admin:
                send_notification("Admin Login", f"Admin {email} logged in.")
                flash('Welcome Admin!', 'success')
                return redirect(url_for('admin_dashboard'))

            send_notification("User Login", f"User {email} logged in.")
            flash('Logged in successfully.', 'success')

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
    if user.get('role') == 'seller':
        return redirect(url_for('seller_dashboard'))

    # Get all books
    response = books_table.scan()
    books = response.get('Items', [])

    return render_template('customer_dashboard.html', user=user, books=books)


@app.route('/browse')
def browse():
    user = session.get('user')
    response = books_table.scan()
    books = response.get('Items', [])
    return render_template('customer_dashboard.html', user=user, books=books)


@app.route('/logout')
def logout():
    email = session.get('user', {}).get('email', 'Unknown')
    session.clear()
    send_notification("User Logout", f"User {email} logged out.")
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

# ==================== ADMIN ROUTES ====================


@app.route('/admin/dashboard')
def admin_dashboard():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))

    users = users_table.scan().get('Items', [])
    books = books_table.scan().get('Items', [])
    orders = orders_table.scan().get('Items', [])

    total_users = len(users)
    total_customers = sum(1 for u in users if u.get('role') == 'customer')
    total_sellers = sum(1 for u in users if u.get('role') == 'seller')
    total_books = len(books)
    total_orders = len(orders)
    total_revenue = sum(float(o.get('total', 0)) for o in orders)

    stats = {
        'total_users': total_users,
        'total_customers': total_customers,
        'total_sellers': total_sellers,
        'total_books': total_books,
        'total_orders': total_orders,
        'total_revenue': round(total_revenue, 2)
    }

    recent_orders = sorted(orders, key=lambda x: x.get(
        'created_at', ''), reverse=True)[:5]

    return render_template('admin_dashboard.html', user=user, stats=stats, recent_orders=recent_orders)


@app.route('/admin/users')
def admin_users():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    raw_users = users_table.scan().get('Items', [])
    role_filter = request.args.get('role', 'all')
    search = request.args.get('search', '')

    # Apply role filter first
    if role_filter != 'all':
        raw_users = [u for u in raw_users if u.get('role') == role_filter]

    users_enriched = []
    for u in raw_users:
        email = u.get('email')

        # count orders for this user (buyer)
        try:
            resp = orders_table.scan(
                FilterExpression=Attr('buyer_email').eq(email))
            orders_count = len(resp.get('Items', []))
        except Exception:
            orders_count = 0

        # count books for this user (if seller)
        try:
            resp = books_table.scan(
                FilterExpression=Attr('seller_email').eq(email))
            books_count = len(resp.get('Items', []))
        except Exception:
            books_count = 0

        user_copy = dict(u)
        user_copy['orders'] = orders_count if orders_count > 0 else '-'
        user_copy['books'] = books_count if books_count > 0 else '-'
        users_enriched.append(user_copy)

    return render_template('admin_users.html', user=user, users=users_enriched, role_filter=role_filter, search=search)


@app.route('/admin/user/<email>')
def admin_user_details(email):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    response = users_table.get_item(Key={'email': email})
    if 'Item' not in response:
        flash('User not found.', 'error')
        return redirect(url_for('admin_users'))

    target_user = response['Item']

    # Get user orders
    response = orders_table.scan(
        FilterExpression=Attr('buyer_email').eq(email)
    )
    user_orders = response.get('Items', [])

    # Attach orders and safe defaults onto the target_user so the template
    # can reference `user_info.*` fields without raising UndefinedError
    try:
        target_user['orders'] = user_orders
    except Exception:
        target_user['orders'] = []
    # ensure other optional collections exist to avoid template errors
    target_user.setdefault('wishlist', [])
    target_user.setdefault('cart', {})
    target_user.setdefault('books', [])
    target_user.setdefault('received_orders', [])

    return render_template('admin_user_details.html', user=user, user_info=target_user, user_email=email)


@app.route('/admin/user/<email>/delete', methods=['POST'])
def admin_delete_user(email):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    users_table.delete_item(Key={'email': email})
    send_notification("User Deleted", f"Admin deleted user: {email}")
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))


@app.route('/admin/books')
def admin_books():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    all_books = books_table.scan().get('Items', [])
    # derive genre list for filter dropdown
    genres = sorted(list({b.get('genre', 'Unknown') for b in all_books}))

    genre_filter = request.args.get('genre', 'all')
    search = request.args.get('search', '')

    # start with all books then apply filters
    books = all_books
    if genre_filter != 'all':
        books = [b for b in books if b.get('genre') == genre_filter]

    if search:
        q = search.lower()
        books = [b for b in books if q in (
            b.get('title', '').lower() + ' ' + b.get('author', '').lower())]

    return render_template('admin_books.html', user=user, books=books, genre_filter=genre_filter, genres=genres, search=search)


@app.route('/admin/book/<book_id>', methods=['GET', 'POST'])
def admin_book_details(book_id):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    response = books_table.get_item(Key={'id': book_id})
    if 'Item' not in response:
        flash('Book not found.', 'error')
        return redirect(url_for('admin_books'))

    book = response['Item']

    if request.method == 'POST':
        books_table.update_item(
            Key={'id': book_id},
            UpdateExpression='SET title = :title, author = :author, price = :price, stock = :stock, genre = :genre, summary = :summary',
            ExpressionAttributeValues={
                ':title': request.form.get('title'),
                ':author': request.form.get('author'),
                ':price': Decimal(str(request.form.get('price'))),
                ':stock': int(request.form.get('stock')),
                ':genre': request.form.get('genre'),
                ':summary': request.form.get('summary', '')
            }
        )
        send_notification(
            "Book Updated", f"Admin updated book: {request.form.get('title')}")
        flash('Book updated successfully.', 'success')
        return redirect(url_for('admin_book_details', book_id=book_id))

    return render_template('admin_book_details.html', user=user, book=book)


@app.route('/admin/book/<book_id>/delete', methods=['POST'])
def admin_delete_book(book_id):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    books_table.delete_item(Key={'id': book_id})
    send_notification("Book Deleted", f"Admin deleted book ID: {book_id}")
    flash('Book deleted successfully.', 'success')
    return redirect(url_for('admin_books'))


@app.route('/admin/sellers')
def admin_sellers():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    all_users = users_table.scan().get('Items', [])
    raw_sellers = [u for u in all_users if u.get('role') == 'seller']

    sellers = []
    for s in raw_sellers:
        email = s.get('email')
        # count seller books
        try:
            resp = books_table.scan(
                FilterExpression=Attr('seller_email').eq(email))
            books_count = len(resp.get('Items', []))
        except Exception:
            books_count = 0

        # count received orders for seller
        try:
            resp = orders_table.scan(
                FilterExpression=Attr('seller_email').eq(email))
            orders_count = len(resp.get('Items', []))
        except Exception:
            orders_count = 0

        s_copy = dict(s)
        s_copy['books'] = books_count if books_count > 0 else '-'
        s_copy['orders'] = orders_count if orders_count > 0 else '-'
        sellers.append(s_copy)

    return render_template('admin_sellers.html', user=user, sellers=sellers)


@app.route('/admin/seller/<email>/details')
def admin_seller_details(email):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    response = users_table.get_item(Key={'email': email})
    if 'Item' not in response or response['Item'].get('role') != 'seller':
        flash('Seller not found.', 'error')
        return redirect(url_for('admin_sellers'))

    seller = response['Item']

    # Get seller books
    response = books_table.scan(
        FilterExpression=Attr('seller_email').eq(email))
    seller_books = response.get('Items', [])

    # Get seller orders
    response = orders_table.scan(
        FilterExpression=Attr('seller_email').eq(email)
    )
    seller_orders = response.get('Items', [])

    # Normalize totals and compute total revenue for the seller
    total_revenue = 0.0
    for o in seller_orders:
        try:
            if isinstance(o.get('total'), Decimal):
                o['total'] = float(o['total'])
            else:
                o['total'] = float(o.get('total', 0) or 0)
        except Exception:
            o['total'] = 0.0
        try:
            total_revenue += float(o.get('total', 0) or 0)
        except Exception:
            continue

    # Attach books and computed stats onto seller dict for template convenience
    seller['books'] = seller_books
    seller['received_orders'] = seller_orders
    seller['total_revenue'] = round(total_revenue, 2)

    return render_template('admin_seller_details.html', user=user, seller=seller)


@app.route('/admin/orders')
def admin_orders():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    raw_orders = orders_table.scan().get('Items', [])

    # Normalize orders for template: ensure customer name/email, totals, items_count
    normalized = []
    for o in raw_orders:
        cust_email = o.get('buyer_email') or (
            o.get('buyer') or {}).get('email')
        cust_name = o.get('buyer_name') or (
            o.get('buyer') or {}).get('name') or cust_email

        # normalize total
        total_val = o.get('total', 0) or 0
        try:
            if isinstance(total_val, Decimal):
                total_val = float(total_val)
            else:
                total_val = float(total_val)
        except Exception:
            total_val = 0.0

        items = o.get('items', []) or []
        items_count = len(items)

        order_info = {
            'id': o.get('id') or o.get('order_id') or '',
            'customer': cust_name,
            'customer_email': cust_email,
            'status': o.get('status', 'Unknown'),
            'total': total_val,
            'created_at': o.get('created_at', ''),
            'items_count': items_count
        }
        normalized.append(order_info)

    # sort
    normalized = sorted(normalized, key=lambda x: x.get(
        'created_at', ''), reverse=True)

    status_filter = request.args.get('status', 'all')
    if status_filter != 'all':
        normalized = [o for o in normalized if o.get(
            'status') == status_filter]

    return render_template('admin_orders.html', user=user, orders=normalized, statuses=sorted(set(o.get('status') for o in normalized)), status_filter=status_filter)


@app.route('/admin/order/<order_id>')
def admin_order_details(order_id):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    response = orders_table.get_item(Key={'id': order_id})
    if 'Item' not in response:
        flash('Order not found.', 'error')
        return redirect(url_for('admin_orders'))

    order = response['Item']
    # Normalize DynamoDB Decimal values and adapt item keys for the template
    try:
        # customer info
        customer_email = order.get('buyer_email') or order.get(
            'buyer', {}).get('email')
        customer_name = order.get('buyer_name') or order.get(
            'buyer', {}).get('name') or ''

        # total
        if isinstance(order.get('total'), Decimal):
            order['total'] = float(order['total'])

        # items: ensure each item has 'id', numeric types are native
        items = order.get('items', []) or []
        new_items = []
        for it in items:
            # copy to avoid mutating unexpected types
            try:
                it_id = it.get('book_id') or it.get('id')
            except Exception:
                it_id = None
            # coerce numeric fields
            try:
                price = float(it.get('price')) if it.get(
                    'price') is not None else 0.0
            except Exception:
                price = 0.0
            try:
                subtotal = float(it.get('subtotal')) if it.get(
                    'subtotal') is not None else 0.0
            except Exception:
                subtotal = 0.0
            try:
                qty = int(it.get('qty') or 0)
            except Exception:
                qty = 0

            new_item = dict(it)
            new_item['id'] = it_id
            new_item['price'] = price
            new_item['subtotal'] = subtotal
            new_item['qty'] = qty
            new_items.append(new_item)

        order['items'] = new_items
    except Exception as e:
        print(f"admin_order_details normalization error: {e}")
        customer_email = order.get('buyer_email')
        customer_name = order.get('buyer_name', '')

    return render_template('admin_order_details.html', user=user, order=order, customer_email=customer_email, customer_name=customer_name)


@app.route('/admin/order/<order_id>/item/<item_id>/remove', methods=['POST'])
def admin_remove_order_item(order_id, item_id):
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    # fetch order
    resp = orders_table.get_item(Key={'id': order_id})
    if 'Item' not in resp:
        flash('Order not found.', 'error')
        return redirect(url_for('admin_orders'))

    order = resp['Item']
    items = order.get('items', []) or []

    # find and remove item (match book_id or id)
    new_items = []
    removed = False
    for it in items:
        it_id = it.get('book_id') or it.get('id') or str(it.get('id'))
        if str(it_id) == str(item_id) and not removed:
            removed = True
            continue
        new_items.append(it)

    if not removed:
        flash('Item not found in order.', 'error')
        return redirect(url_for('admin_order_details', order_id=order_id))

    # recompute total
    new_total = 0.0
    for it in new_items:
        try:
            subtotal = it.get('subtotal', 0) or 0
            if isinstance(subtotal, Decimal):
                subtotal = float(subtotal)
            else:
                subtotal = float(subtotal)
        except Exception:
            subtotal = 0.0
        new_total += subtotal

    # update DynamoDB order
    try:
        orders_table.update_item(
            Key={'id': order_id},
            UpdateExpression='SET items = :items, total = :total',
            ExpressionAttributeValues={
                ':items': new_items,
                ':total': Decimal(str(new_total))
            }
        )
        flash('Item removed from order.', 'success')
    except Exception as e:
        print(f"Error updating order: {e}")
        flash('Failed to update order.', 'error')

    return redirect(url_for('admin_order_details', order_id=order_id))


@app.route('/admin/analytics')
def admin_analytics():
    user = session.get('user')
    if not user or not user.get('is_admin'):
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    all_users = users_table.scan().get('Items', [])
    all_books = books_table.scan().get('Items', [])
    all_orders = orders_table.scan().get('Items', [])

    total_users = len(all_users)
    total_customers = sum(1 for u in all_users if u.get('role') == 'customer')
    total_sellers = sum(1 for u in all_users if u.get('role') == 'seller')
    total_books = len(all_books)
    total_orders = len(all_orders)

    total_revenue = sum(float(o.get('total', 0)) for o in all_orders)
    completed_orders = sum(
        1 for o in all_orders if o.get('status') == 'Delivered')

    # Genre stats
    genre_stats = {}
    for book in all_books:
        genre = book.get('genre', 'Unknown')
        genre_stats[genre] = genre_stats.get(genre, 0) + 1

    # Status stats
    status_stats = {}
    for order in all_orders:
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

# ==================== SELLER ROUTES ====================


@app.route('/seller/dashboard')
def seller_dashboard():
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('index'))

    email = user.get('email')

    # Get seller books
    response = books_table.scan(
        FilterExpression=Attr('seller_email').eq(email))
    seller_books = response.get('Items', [])

    # Get seller orders
    response = orders_table.scan(
        FilterExpression=Attr('seller_email').eq(email)
    )
    seller_orders = sorted(response.get('Items', []),
                           key=lambda x: x.get('created_at', ''), reverse=True)

    total_books = len(seller_books)
    total_orders = len(seller_orders)
    revenue = sum(float(o.get('total', 0)) for o in seller_orders)

    stats = {
        'total_books': total_books,
        'total_orders': total_orders,
        'revenue': round(revenue, 2)
    }

    return render_template('seller_dashboard.html', user=user, books=seller_books, orders=seller_orders, stats=stats)


@app.route('/seller/books')
def seller_books():
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    email = user.get('email')
    response = books_table.scan(
        FilterExpression=Attr('seller_email').eq(email))
    seller_books_list = response.get('Items', [])

    return render_template('seller_books.html', user=user, books=seller_books_list)


@app.route('/seller/add-book', methods=['GET', 'POST'])
def seller_add_book():
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        book_id = str(uuid.uuid4())
        email = user.get('email')

        books_table.put_item(Item={
            'id': book_id,
            'title': request.form.get('title'),
            'author': request.form.get('author'),
            'summary': request.form.get('summary', ''),
            'seller_name': user.get('name', ''),
            'seller_email': email,
            'price': Decimal(str(request.form.get('price'))),
            'genre': request.form.get('genre'),
            'cover_url': request.form.get('cover_url', 'https://placehold.co/150x220/e0e0e0/333333?text=Book'),
            'stock': int(request.form.get('stock')),
            'created_at': datetime.utcnow().isoformat()
        })

        send_notification("New Book Added",
                          f"Seller {email} added: {request.form.get('title')}")
        flash('Book added successfully!', 'success')
        return redirect(url_for('seller_books'))

    return render_template('seller_add_book.html', user=user)


@app.route('/seller/book/<book_id>/edit', methods=['GET', 'POST'])
def seller_edit_book(book_id):
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('index'))

    # fetch book from DynamoDB
    response = books_table.get_item(Key={'id': book_id})
    if 'Item' not in response:
        flash('Book not found.', 'error')
        return redirect(url_for('seller_books'))

    book = response['Item']

    # ensure seller owns the book
    if book.get('seller_email') != user.get('email'):
        flash('You are not authorized to edit this book.', 'error')
        return redirect(url_for('seller_books'))

    if request.method == 'POST':
        updates = {}
        # collect fields if provided
        if request.form.get('title') is not None:
            updates['title'] = request.form.get('title')
        if request.form.get('author') is not None:
            updates['author'] = request.form.get('author')
        if request.form.get('summary') is not None:
            updates['summary'] = request.form.get('summary')
        if request.form.get('genre') is not None:
            updates['genre'] = request.form.get('genre')
        if request.form.get('cover_url'):
            updates['cover_url'] = request.form.get('cover_url')
        # numeric conversions
        price_val = request.form.get('price')
        if price_val:
            try:
                updates['price'] = Decimal(str(price_val))
            except Exception:
                pass
        stock_val = request.form.get('stock')
        if stock_val:
            try:
                updates['stock'] = int(stock_val)
            except Exception:
                pass

        if updates:
            expr_parts = []
            expr_values = {}
            for k, v in updates.items():
                expr_parts.append(f"{k} = :{k}")
                expr_values[f":{k}"] = v

            update_expr = 'SET ' + ', '.join(expr_parts)
            try:
                books_table.update_item(
                    Key={'id': book_id},
                    UpdateExpression=update_expr,
                    ExpressionAttributeValues=expr_values
                )
                send_notification(
                    "Book Updated", f"Seller {user.get('email')} updated book: {updates.get('title', book.get('title'))}")
                flash('Book updated successfully.', 'success')
            except Exception as e:
                print(f"Error updating book: {e}")
                flash('Failed to update book.', 'error')

        return redirect(url_for('seller_books'))

    return render_template('seller_add_book.html', user=user, book=book)


@app.route('/seller/book/<book_id>/delete', methods=['POST'])
def seller_delete_book(book_id):
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('index'))

    response = books_table.get_item(Key={'id': book_id})
    if 'Item' not in response:
        flash('Book not found.', 'error')
        return redirect(url_for('seller_books'))

    book = response['Item']
    if book.get('seller_email') != user.get('email'):
        flash('You are not authorized to delete this book.', 'error')
        return redirect(url_for('seller_books'))

    try:
        books_table.delete_item(Key={'id': book_id})
        send_notification(
            'Book Deleted', f"Seller {user.get('email')} deleted book: {book.get('title')}")
        flash('Book deleted successfully.', 'success')
    except Exception as e:
        print(f"Error deleting book: {e}")
        flash('Failed to delete book.', 'error')

    return redirect(url_for('seller_books'))


@app.route('/seller/orders')
def seller_orders():
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    email = user.get('email')
    response = orders_table.scan(
        FilterExpression=Attr('seller_email').eq(email)
    )
    orders = response.get('Items', [])

    # Normalize orders so templates can access `o.buyer.name` and `o.buyer.email`
    normalized = []
    for o in orders:
        # buyer info may be stored as top-level fields
        buyer_name = o.get('buyer_name') or (
            o.get('buyer') or {}).get('name', '')
        buyer_email = o.get('buyer_email') or (
            o.get('buyer') or {}).get('email', '')
        buyer = {'name': buyer_name, 'email': buyer_email}

        # normalize total and item numeric types for template formatting
        total_val = o.get('total', 0) or 0
        try:
            if isinstance(total_val, Decimal):
                total_val = float(total_val)
            else:
                total_val = float(total_val)
        except Exception:
            total_val = 0.0

        items = o.get('items', []) or []
        nice_items = []
        for it in items:
            try:
                subtotal = it.get('subtotal', 0) or 0
                if isinstance(subtotal, Decimal):
                    subtotal = float(subtotal)
                else:
                    subtotal = float(subtotal)
            except Exception:
                subtotal = 0.0
            try:
                qty = int(it.get('qty', 0) or 0)
            except Exception:
                qty = 0

            nice_items.append({
                'qty': qty,
                'title': it.get('title', ''),
                'subtotal': subtotal
            })

        no = dict(o)
        no['buyer'] = buyer
        no['total'] = total_val
        no['items'] = nice_items
        normalized.append(no)

    return render_template('seller_orders.html', user=user, orders=normalized)


@app.route('/seller/order/<order_id>/status', methods=['POST'])
def seller_update_order_status(order_id):
    user = session.get('user')
    if not user or user.get('role') != 'seller':
        flash('Access denied. Seller account required.', 'error')
        return redirect(url_for('index'))

    # Fetch the order item from DynamoDB
    try:
        resp = orders_table.get_item(Key={'id': order_id})
    except Exception as e:
        print(f"Error fetching order {order_id}: {e}")
        flash('Failed to update order.', 'error')
        return redirect(url_for('seller_orders'))

    if 'Item' not in resp:
        flash('Order not found.', 'error')
        return redirect(url_for('seller_orders'))

    order = resp['Item']
    seller_email = order.get('seller_email')
    if seller_email != user.get('email'):
        flash('You are not authorized to update this order.', 'error')
        return redirect(url_for('seller_orders'))

    new_status = request.form.get('status') or order.get('status')

    try:
        orders_table.update_item(
            Key={'id': order_id},
            UpdateExpression='SET #s = :s',
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': new_status}
        )
        flash('Order status updated.', 'success')
    except Exception as e:
        print(f"Error updating order status: {e}")
        flash('Failed to update order status.', 'error')

    return redirect(url_for('seller_orders'))

# ==================== CUSTOMER ROUTES ====================


@app.route('/cart')
def cart():
    user = session.get('user')
    if not user:
        flash('Please sign in.', 'error')
        return redirect(url_for('auth_page'))

    cart_data = session.get('cart', {})
    cart_items = []
    total = 0.0

    # Fetch all books once and index by id to avoid per-item get_item mismatches
    try:
        response = books_table.scan()
        all_books = response.get('Items', [])
        books_index = {str(b.get('id')): b for b in all_books}
    except Exception:
        books_index = {}

    # Build cart items from session, using indexed books
    for book_id, qty in cart_data.items():
        # try indexed lookup first
        book = books_index.get(str(book_id))
        # fallback to direct get_item if scan didn't include it (safer for inconsistent id types)
        if not book:
            try:
                resp = books_table.get_item(Key={'id': book_id})
                if 'Item' in resp:
                    book = resp['Item']
            except Exception:
                book = None

        if book:
            try:
                qty_int = int(qty)
            except Exception:
                qty_int = 0
            try:
                price = float(book.get('price', 0))
            except Exception:
                price = 0.0
            subtotal = qty_int * price
            total += subtotal
            # Build flat item dict expected by cart.html template
            item = {
                'id': str(book.get('id')) if book.get('id') is not None else None,
                'title': book.get('title', ''),
                'author': book.get('author', ''),
                'price': price,
                'qty': qty_int,
                'subtotal': subtotal,
            }
            cart_items.append(item)
        else:
            # show user-friendly message for missing items
            flash(
                f"Item with id {book_id} is no longer available and will be removed at checkout.", 'info')

    return render_template('cart.html', user=user, items=cart_items, total=round(total, 2))


@app.route('/cart/add/<book_id>', methods=['POST'])
def add_to_cart(book_id):
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Please sign in'}), 401

    cart = session.get('cart', {})
    cart[book_id] = cart.get(book_id, 0) + 1
    session['cart'] = cart

    cart_count = sum(int(q) for q in cart.values())
    return jsonify({'success': True, 'count': cart_count})


@app.route('/cart/update/<book_id>', methods=['POST'])
def update_cart(book_id):
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Please sign in'}), 401

    qty = request.json.get('qty', 0)
    cart = session.get('cart', {})

    if qty <= 0:
        cart.pop(book_id, None)
    else:
        cart[book_id] = qty

    session['cart'] = cart
    return jsonify({'success': True})


@app.route('/cart/remove/<book_id>', methods=['POST'])
def remove_from_cart(book_id):
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Please sign in'}), 401

    cart = session.get('cart', {})
    cart.pop(book_id, None)
    session['cart'] = cart

    return jsonify({'success': True})


@app.route('/wishlist/toggle/<book_id>', methods=['POST'])
def toggle_wishlist(book_id):
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Please sign in'}), 401

    wishlist = session.get('wishlist', [])

    if book_id in wishlist:
        wishlist.remove(book_id)
        added = False
    else:
        wishlist.append(book_id)
        added = True

    session['wishlist'] = wishlist
    return jsonify({'added': added, 'count': len(wishlist)})


@app.route('/wishlist')
def wishlist():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))

    wishlist_ids = session.get('wishlist', [])
    wishlist_items = []

    for book_id in wishlist_ids:
        response = books_table.get_item(Key={'id': book_id})
        if 'Item' in response:
            wishlist_items.append(response['Item'])

    return render_template('wishlist.html', user=user, items=wishlist_items)


@app.route('/profile')
def profile():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))

    email = user.get('email')
    response = users_table.get_item(Key={'email': email})
    user_data = response.get('Item', {})
    addresses = user_data.get('addresses', [])

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

    response = users_table.get_item(Key={'email': email})
    user_data = response.get('Item', {})
    addresses = user_data.get('addresses', [])
    addresses.append(addr)

    users_table.update_item(
        Key={'email': email},
        UpdateExpression='SET addresses = :addresses',
        ExpressionAttributeValues={':addresses': addresses}
    )

    flash('Address added.', 'success')
    return redirect(url_for('profile'))


@app.route('/payment', methods=['GET', 'POST'])
def payment():
    user = session.get('user')
    if not user:
        flash('Please sign in.', 'error')
        return redirect(url_for('auth_page'))

    email = user.get('email')
    response = users_table.get_item(Key={'email': email})
    user_data = response.get('Item', {})
    addresses = user_data.get('addresses', [])

    if request.method == 'POST':
        addr_id = request.form.get('existing_address')
        if addr_id:
            addr = addresses[int(addr_id)]
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
                addresses.append(addr)
                users_table.update_item(
                    Key={'email': email},
                    UpdateExpression='SET addresses = :addresses',
                    ExpressionAttributeValues={':addresses': addresses}
                )

        cart = session.get('cart', {})
        if not cart:
            flash('Your cart is empty.', 'error')
            return redirect(url_for('cart'))

        items = []
        total = 0.0
        sellers_involved = {}

        for book_id, qty in cart.items():
            response = books_table.get_item(Key={'id': book_id})
            if 'Item' not in response:
                continue

            book = response['Item']
            qty = int(qty)
            available = int(book.get('stock', 0))

            if qty > available:
                flash(f"Not enough stock for '{book.get('title')}'", 'error')
                return redirect(url_for('cart'))

            subtotal = qty * float(book.get('price', 0))
            total += subtotal

            item = {
                'book_id': book_id,
                'title': book.get('title'),
                'author': book.get('author'),
                'qty': qty,
                'price': float(book.get('price')),
                'subtotal': subtotal
            }
            items.append(item)

            seller_email = book.get('seller_email')
            if seller_email:
                if seller_email not in sellers_involved:
                    sellers_involved[seller_email] = []
                sellers_involved[seller_email].append(item)

        order_id = f"ORD-{int(datetime.utcnow().timestamp()*1000)}"

        # Create order for each seller
        for seller_email, seller_items in sellers_involved.items():
            # seller_items may contain Python floats which DynamoDB rejects;
            # convert numeric fields to Decimal before persisting.
            seller_total = sum(float(it.get('subtotal', 0) or 0)
                               for it in seller_items)

            safe_items = []
            for it in seller_items:
                try:
                    price_val = Decimal(str(float(it.get('price', 0) or 0)))
                except Exception:
                    price_val = Decimal('0')
                try:
                    subtotal_val = Decimal(
                        str(float(it.get('subtotal', 0) or 0)))
                except Exception:
                    subtotal_val = Decimal('0')
                try:
                    qty_val = int(it.get('qty', 0) or 0)
                except Exception:
                    qty_val = 0

                safe_item = {
                    'book_id': it.get('book_id'),
                    'title': it.get('title'),
                    'author': it.get('author'),
                    'qty': qty_val,
                    'price': price_val,
                    'subtotal': subtotal_val
                }
                safe_items.append(safe_item)

            orders_table.put_item(Item={
                'id': f"{order_id}-{seller_email}",
                'original_order_id': order_id,
                'buyer_email': email,
                'buyer_name': user.get('name', ''),
                'seller_email': seller_email,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'Placed',
                'items': safe_items,
                'total': Decimal(str(seller_total)),
                'shipping_address': addr
            })

        # Update stock
        for item in items:
            response = books_table.get_item(Key={'id': item['book_id']})
            if 'Item' in response:
                book = response['Item']
                new_stock = max(0, int(book.get('stock', 0)) - item['qty'])
                books_table.update_item(
                    Key={'id': item['book_id']},
                    UpdateExpression='SET stock = :stock',
                    ExpressionAttributeValues={':stock': new_stock}
                )

        send_notification(
            "New Order", f"Order {order_id} placed by {email} for ${total:.2f}")

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
    response = orders_table.scan(
        FilterExpression=Attr('buyer_email').eq(email)
    )
    orders_list = sorted(response.get('Items', []),
                         key=lambda x: x.get('created_at', ''), reverse=True)

    return render_template('orders.html', user=user, orders=orders_list)


@app.route('/api/chatbot', methods=['POST'])
def chatbot_api():
    """Chatbot API endpoint with LLM integration and DynamoDB context"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()

        if not message:
            return jsonify({'error': 'Message is required'}), 400

        # Get available books from DynamoDB
        response = books_table.scan()
        all_books = response.get('Items', [])
        available_books = [b for b in all_books if int(b.get('stock', 0)) > 0]

        # Get user's orders if logged in
        user = session.get('user')
        user_orders = []
        user_wishlist = []
        if user:
            email = user.get('email')
            try:
                resp = orders_table.scan(
                    FilterExpression=Attr('buyer_email').eq(email)
                )
                user_orders = resp.get('Items', [])
            except Exception:
                user_orders = []
            user_wishlist = session.get('wishlist', [])

        # Build a minimal book context for the LLM
        books_context = []
        for b in available_books:
            books_context.append({
                'id': str(b.get('id')),
                'title': b.get('title', ''),
                'author': b.get('author', ''),
                'genre': b.get('genre', 'Unknown'),
                'price': float(b.get('price', 0) or 0),
                'stock': int(b.get('stock', 0) or 0),
                'summary': b.get('summary', '')
            })

        genres = sorted({b.get('genre', 'Unknown') for b in available_books})
        context = {
            'total_books': len(available_books),
            'genres': genres,
            'all_books': books_context,
            'user_orders_count': len(user_orders),
            'user_wishlist_count': len(user_wishlist)
        }

        # Try to use Hugging Face LLM with InferenceClient
        response_text = None
        recommended_books = []
        actions = []
        used_ai = False

        if HF_CLIENT:
            try:
                print(f"[DEBUG] Calling HuggingFace API via InferenceClient")

                system_prompt = f"""You are BookBazaar Assistant, a helpful chatbot for an online bookstore.

DATABASE CONTEXT:
- Total books in stock: {context['total_books']}
- Available genres: {', '.join(context['genres'])}
- Books database: {json.dumps(books_context, indent=2)}

USER CONTEXT:
- Orders placed: {context['user_orders_count']}
- Wishlist items: {context['user_wishlist_count']}

CAPABILITIES:
When recommending books, you MUST respond in this JSON format:
{{
  "message": "your helpful response text",
  "recommended_books": [book_id1, book_id2],
  "action": "none|add_to_wishlist"
}}

IMPORTANT RULES:
1. When user asks about books or recommendations, include book IDs in "recommended_books" array
2. When user says "add to wishlist" or similar, set "action": "add_to_wishlist" and include the book ID
3. Always provide helpful, concise responses (2-3 sentences)
4. Use actual book data from the database
5. When recommending books, mention their titles and why they're good matches

Example:
User: "recommend a fiction book"
Response: {{"message": "I recommend 'The Great Gatsby' by F. Scott Fitzgerald - a timeless classic about the Jazz Age and the American Dream!",
    "recommended_books": [1], "action": "none"}}

User: "add it to wishlist"
Response: {{"message": "I've added 'The Great Gatsby' to your wishlist!",
    "recommended_books": [1], "action": "add_to_wishlist"}}
"""

                completion = HF_CLIENT.chat.completions.create(
                    model=HF_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )

                ai_response = completion.choices[0].message.content.strip()
                used_ai = True
                print(f"[DEBUG] AI Response: {ai_response}")

                try:
                    parsed_response = json.loads(ai_response)
                    response_text = parsed_response.get('message', ai_response)
                    # normalize recommended book ids to strings
                    recommended_books = [
                        str(b) for b in parsed_response.get('recommended_books', [])]
                    action = parsed_response.get('action', 'none')
                    if action == 'add_to_wishlist' and recommended_books:
                        actions.append(
                            {'type': 'add_to_wishlist', 'book_ids': recommended_books})
                except json.JSONDecodeError:
                    response_text = ai_response
                    for book in available_books:
                        if book.get('title') and book['title'].lower() in message.lower():
                            bid = book.get('id')
                            if bid is not None:
                                bid = str(bid)
                                if bid not in recommended_books:
                                    recommended_books.append(bid)

            except Exception as e:
                print(f"[ERROR] HuggingFace API Error: {e}")
                response_text = None

        # Fallback to pattern matching if LLM fails
        if not response_text:
            print(f"[DEBUG] Using fallback pattern matching")
            fallback_result = generate_smart_fallback(
                message.lower(), context, available_books, user_wishlist)
            response_text = fallback_result['message']
            recommended_books = fallback_result.get('recommended_books', [])
            if fallback_result.get('action') == 'add_to_wishlist':
                actions.append({'type': 'add_to_wishlist',
                               'book_ids': recommended_books})

        # Get full book details for recommended books
        books_to_display = []
        for book_id in recommended_books[:3]:
            # treat ids as strings
            bid = str(book_id)
            # find in all_books
            book = next((b for b in all_books if str(
                b.get('id', '')) == bid), None)
            if book:
                books_to_display.append({
                    'id': str(book.get('id')),
                    'title': book.get('title'),
                    'author': book.get('author'),
                    'price': float(book.get('price', 0)),
                    'genre': book.get('genre', 'Unknown'),
                    'cover_url': book.get('cover_url', ''),
                    'summary': book.get('summary', '')
                })

        source = 'ai' if used_ai else 'system'

        return jsonify({'response': response_text, 'books': books_to_display, 'actions': actions, 'source': source})

    except Exception as e:
        print(f"Chatbot API Error: {e}")
        return jsonify({'error': 'Failed to process request'}), 500


def generate_smart_fallback(message, context, available_books, user_wishlist=None):
    """Generate a deterministic fallback response when LLM is unavailable.

    Returns a dict: {message: str, recommended_books: [ids], action: optional}
    """
    user_wishlist = user_wishlist or []
    msg = "I'm sorry, I couldn't reach the recommendation engine right now."
    recommended = []
    action = 'none'

    # Simple keyword-based recommendations
    if 'recommend' in message or 'suggest' in message or 'something to read' in message:
        # recommend top 3 by stock
        sorted_books = sorted(available_books, key=lambda b: int(
            b.get('stock', 0)), reverse=True)
        for b in sorted_books[:3]:
            try:
                bid = b.get('id')
                if bid is not None:
                    recommended.append(str(bid))
            except Exception:
                continue
        if recommended:
            titles = [b.get('title') for b in sorted_books[:3]]
            msg = f"I recommend: {', '.join(titles)}. Want me to add any to your wishlist?"
    elif 'add to wishlist' in message or 'add to my wishlist' in message or 'wishlist' in message:
        # try to find a book title in message
        for b in available_books:
            if b.get('title') and b['title'].lower() in message:
                try:
                    bid = b.get('id')
                    if bid is not None:
                        recommended.append(str(bid))
                except Exception:
                    pass
        if recommended:
            action = 'add_to_wishlist'
            msg = f"Added {len(recommended)} book(s) to your wishlist (local simulation)."
        else:
            msg = "Which book would you like me to add to your wishlist?"
    else:
        # fallback quick answer
        msg = "I can help recommend books, find details, or add items to your wishlist. What would you like?"

    return {'message': msg, 'recommended_books': recommended, 'action': action}


@app.route('/api/chatbot/add-to-wishlist', methods=['POST'])
def chatbot_add_to_wishlist():
    try:
        data = request.get_json()
        book_ids = data.get('book_ids', [])
        suppress_confirmation = data.get('suppressConfirmation', False)

        if not isinstance(book_ids, list):
            return jsonify({'error': 'book_ids must be a list'}), 400

        wishlist = session.get('wishlist', [])
        added = []
        for bid in book_ids:
            # store ids as strings
            bid = str(bid)
            if bid not in wishlist:
                wishlist.append(bid)
                added.append(bid)

        session['wishlist'] = wishlist

        response_msg = None
        if not suppress_confirmation:
            response_msg = f"Added {len(added)} book(s) to your wishlist."

        return jsonify({'added': added, 'message': response_msg})
    except Exception as e:
        print(f"Add to wishlist error: {e}")
        return jsonify({'error': 'Failed to add to wishlist'}), 500


@app.route('/api/book/<book_id>', methods=['GET'])
def get_book_details(book_id):
    try:
        response = books_table.scan()
        all_books = response.get('Items', [])
        # compare ids as strings
        book = next((b for b in all_books if str(
            b.get('id', '')) == str(book_id)), None)
        if not book:
            return jsonify({'error': 'Book not found'}), 404

        return jsonify({
            'id': str(book.get('id')),
            'title': book.get('title'),
            'author': book.get('author'),
            'price': float(book.get('price', 0)),
            'genre': book.get('genre', 'Unknown'),
            'summary': book.get('summary', ''),
            'cover_url': book.get('cover_url', '')
        })
    except Exception as e:
        print(f"Get book details error: {e}")
        return jsonify({'error': 'Failed to retrieve book'}), 500


def generate_fallback_response(message, context, available_books, user_orders):
    """Generate response using simple pattern matching"""
    # Use the passed `available_books` and safe context lookups
    genres = context.get('genres', [])
    total = len(available_books)

    # Greetings
    if any(word in message for word in ['hello', 'hi', 'hey']):
        return f"Hello! 👋 Welcome to BookBazaar! We have {total} books available. How can I help you find your next great read?"

    # Book availability
    if 'how many' in message or 'available' in message:
        return f"We currently have {total} books in stock across {len(genres)} genres: {', '.join(genres)}. Would you like to browse by genre?"

    # Genre queries
    for genre in genres:
        if genre.lower() in message:
            genre_books = [
                b for b in available_books if b.get('genre') == genre]
            if genre_books:
                sample = genre_books[:2]
                books_list = ', '.join([
                    f"{b.get('title')} by {b.get('author')} (${float(b.get('price', 0))})" for b in sample])
                return f"We have {len(genre_books)} {genre} books! Check out: {books_list}. Browse more on our catalog!"

    # Search
    if 'search' in message or 'find' in message:
        return f"You can browse our {total} books by using the search bar or genre filter on the Browse Books page. What type of book are you looking for?"

    # Orders
    if 'order' in message:
        if user_orders:
            return f"You have {len(user_orders)} order(s). Check the 'Your Orders' page to view details and track your deliveries."
        return "You haven't placed any orders yet. Browse our books and add items to your cart to get started!"

    # Cart
    if 'cart' in message:
        return "Click the cart icon in the header to view your cart. You can add books by clicking 'Add to Cart' on any book card."

    # Wishlist
    if 'wishlist' in message or 'wish list' in message:
        return "Save books for later by clicking the heart icon! View your wishlist from the sidebar to see all your saved books."

    # Thanks
    if 'thank' in message:
        return "You're welcome! Happy reading! 📚 Let me know if you need anything else."

    # Default
    return f"I can help you with:\n• Browse our {total} available books\n• Search by genre: {', '.join(genres[:3])}\n• Track your orders\n• Manage cart and wishlist\n\nWhat would you like to know?"


@app.context_processor
def cart_context():
    cart = session.get('cart', {})
    count = sum(int(q) for q in cart.values())
    wishlist = session.get('wishlist', [])
    wishlist_ids = set(wishlist)

    return {
        'cart_count': count,
        'wishlist_ids': wishlist_ids
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
