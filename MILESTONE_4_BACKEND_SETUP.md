# Milestone 4: Backend Development and Application Setup (BookBazaar)

## Description of the code

This milestone documents the backend implementation and setup for BookBazaar. The backend is built with Flask, stores data in DynamoDB, sends notifications using SNS, and integrates an AI chatbot with a safe fallback. Below, each section includes a short description followed by the relevant code snippet.

---

## 1) Flask App Initialization

**Description:**
We import Flask, security helpers, AWS SDK (boto3), and other utilities. The Flask app is created and a secret key is set for secure session handling.

```python
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
```

---

## 2) Hugging Face Chatbot Configuration

**Description:**
We configure the Hugging Face API token and model name. The `InferenceClient` is created if a token is present.

```python
# Hugging Face Configuration
HF_API_KEY = os.environ.get('HF_TOKEN', 'test')
HF_MODEL = os.environ.get('HF_MODEL', 'Qwen/Qwen2.5-72B-Instruct')
HF_CLIENT = InferenceClient(api_key=HF_API_KEY) if HF_API_KEY else None
```

---

## 3) AWS DynamoDB and SNS Setup

**Description:**
We connect to DynamoDB and SNS in the configured AWS region, then create table references for users, books, and orders. The SNS topic ARN is used to publish notifications.

```python
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
```

---

## 4) SNS Notification Helper

**Description:**
This helper publishes system events such as signup, login, book updates, and order creation to the SNS topic.

```python
def send_notification(subject, message):
  try:
    sns.publish(
      TopicArn=SNS_TOPIC_ARN,
      Subject=subject,
      Message=message
    )
  except ClientError as e:
    print(f"Error sending notification: {e}")
```

---

## 5) Authentication (Signup + Login)

**Description:**
Users register and log in through DynamoDB. Passwords are hashed using `werkzeug.security`. The session stores role-based access for admin, seller, and customer.

```python
@app.route('/signup', methods=['POST'])
def signup():
  name = request.form.get('name')
  email = request.form.get('email')
  password = request.form.get('password')
  role = request.form.get('role') or 'customer'

  if not email or not password:
    flash('Email and password are required.', 'error')
    return redirect(url_for('index'))

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

  send_notification("New User Signup", f"User {name} ({email}) signed up as {role}.")
  flash('Account created successfully. Please sign in.', 'success')
  return redirect(url_for('auth_page'))


@app.route('/login', methods=['POST'])
def login():
  email = request.form.get('email')
  password = request.form.get('password')

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
      return redirect(url_for('dashboard'))

  flash('Invalid credentials.', 'error')
  return redirect(url_for('auth_page'))
```

---

## 6) Seller Book Management

**Description:**
Sellers can add books to DynamoDB, including title, author, price, stock, and genre. Each book is linked to the seller’s email.

```python
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

    send_notification("New Book Added", f"Seller {email} added: {request.form.get('title')}")
    flash('Book added successfully!', 'success')
    return redirect(url_for('seller_books'))

  return render_template('seller_add_book.html', user=user)
```

---

## 7) Cart and Checkout

**Description:**
The cart is stored in the Flask session. During checkout, orders are created for each seller involved, and book stock is updated in DynamoDB.

```python
@app.route('/payment', methods=['GET', 'POST'])
def payment():
  user = session.get('user')
  if not user:
    flash('Please sign in.', 'error')
    return redirect(url_for('auth_page'))

  if request.method == 'POST':
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
        sellers_involved.setdefault(seller_email, []).append(item)

    order_id = f"ORD-{int(datetime.utcnow().timestamp()*1000)}"

    for seller_email, seller_items in sellers_involved.items():
      seller_total = sum(float(it.get('subtotal', 0) or 0) for it in seller_items)
      orders_table.put_item(Item={
        'id': f"{order_id}-{seller_email}",
        'original_order_id': order_id,
        'buyer_email': user.get('email'),
        'buyer_name': user.get('name', ''),
        'seller_email': seller_email,
        'created_at': datetime.utcnow().isoformat(),
        'status': 'Placed',
        'items': seller_items,
        'total': Decimal(str(seller_total))
      })

    send_notification("New Order", f"Order {order_id} placed by {user.get('email')} for ${total:.2f}")
    flash('Order placed (Cash on Delivery).', 'success')
    session['cart'] = {}
    return redirect(url_for('orders'))

  return render_template('payment.html', user=user)
```

---

## 8) Admin Analytics

**Description:**
Admin analytics aggregates users, books, orders, revenue, and order status counts for display on the admin analytics page.

```python
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
  completed_orders = sum(1 for o in all_orders if o.get('status') == 'Delivered')

  genre_stats = {}
  for book in all_books:
    genre = book.get('genre', 'Unknown')
    genre_stats[genre] = genre_stats.get(genre, 0) + 1

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
```

---

## 9) Chatbot API Endpoint

**Description:**
The chatbot uses Hugging Face for AI responses. If the AI fails, it falls back to pattern-based recommendations.

```python
@app.route('/api/chatbot', methods=['POST'])
def chatbot_api():
  data = request.get_json()
  message = data.get('message', '').strip()

  response = books_table.scan()
  all_books = response.get('Items', [])
  available_books = [b for b in all_books if int(b.get('stock', 0)) > 0]

  # AI response (with fallback)
  response_text = None
  if HF_CLIENT:
    try:
      completion = HF_CLIENT.chat.completions.create(
        model=HF_MODEL,
        messages=[
          {"role": "system", "content": "BookBazaar chatbot system prompt"},
          {"role": "user", "content": message}
        ],
        max_tokens=500,
        temperature=0.7
      )
      response_text = completion.choices[0].message.content.strip()
    except Exception:
      response_text = None

  if not response_text:
    response_text = "Fallback response when AI is unavailable."

  return jsonify({'response': response_text, 'books': []})
```

---

## 10) Local Setup Commands

**Description:**
Use the following commands to run the backend locally after setting up DynamoDB and environment variables.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:AWS_ACCESS_KEY_ID = 'test'
$env:AWS_SECRET_ACCESS_KEY = 'test'
$env:AWS_REGION = 'us-east-1'

python aws_app.py
```

---

## Completion Criteria

Milestone 4 is complete when the backend runs locally, DynamoDB tables are connected, SNS notifications are sent, and all role-based flows work end-to-end.
