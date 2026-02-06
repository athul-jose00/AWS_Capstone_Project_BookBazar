import boto3
import os
from decimal import Decimal
from datetime import datetime
from werkzeug.security import generate_password_hash

# AWS Configuration
REGION = 'us-east-1'
dynamodb = boto3.resource('dynamodb', region_name=REGION)

# Tables
users_table = dynamodb.Table('BookBazaar_Users')
books_table = dynamodb.Table('BookBazaar_Books')
orders_table = dynamodb.Table('BookBazaar_Orders')


def seed_data():
    print("Starting data seeding...")

    # 1. Define Data Source (Mirrors app.py)

    # Mock Books from app.py
    # Note: IDs are converted to strings for DynamoDB compatibility
    mock_books_data = [
        {
            'id': '1',
            'title': 'The Great Gatsby',
            'author': 'F. Scott Fitzgerald',
            'summary': 'A classic novel of the Jazz Age that tells the story of the mysteriously wealthy Jay Gatsby and his love for Daisy Buchanan.',
            'seller': {'name': 'ClassicBooks Co.', 'contact': 'classic@bookseller.example.com'},
            'price': 10.99,
            'genre': 'Fiction',
            'cover_url': 'https://upload.wikimedia.org/wikipedia/commons/7/7a/The_Great_Gatsby_Cover_1925_Retouched.jpg',
            'stock': 10
        },
        {
            'id': '2',
            'title': '1984',
            'author': 'George Orwell',
            'summary': 'A dystopian social science fiction novel and cautionary tale about surveillance and totalitarianism.',
            'seller': {'name': 'Dystopia Books', 'contact': 'sales@dystopiabooks.example.com'},
            'price': 8.99,
            'genre': 'Sci-Fi',
            'cover_url': 'https://m.media-amazon.com/images/I/71kxa1-0mfL._AC_UF1000,1000_QL80_.jpg',
            'stock': 10
        },
        {
            'id': '3',
            'title': 'The Hobbit',
            'author': 'J.R.R. Tolkien',
            'summary': 'Bilbo Baggins embarks on a grand adventure with a group of dwarves to reclaim their mountain home.',
            'seller': {'name': 'MiddleEarth Books', 'contact': 'hobbit@middleearth.example.com'},
            'price': 12.99,
            'genre': 'Sci-Fi',
            'cover_url': 'https://upload.wikimedia.org/wikipedia/en/4/4a/TheHobbit_FirstEdition.jpg',
            'stock': 10
        },
        {
            'id': '4',
            'title': 'Clean Code',
            'author': 'Robert C. Martin',
            'summary': 'A handbook of agile software craftsmanship, focusing on writing readable, maintainable code.',
            'seller': {'name': 'TechReads', 'contact': 'support@techreads.example.com'},
            'price': 29.99,
            'genre': 'Non-Fiction',
            'cover_url': 'https://m.media-amazon.com/images/I/71T7aD3EOTL._UF1000,1000_QL80_.jpg',
            'stock': 10
        },
        {
            'id': '5',
            'title': 'Design Patterns',
            'author': 'Gang of Four',
            'summary': 'Elements of reusable object-oriented software — classic reference for software design patterns.',
            'seller': {'name': 'Patterns Shop', 'contact': 'info@patternsshop.example.com'},
            'price': 35.50,
            'genre': 'Non-Fiction',
            'cover_url': 'https://m.media-amazon.com/images/I/81gtKoapHFL._AC_UF1000,1000_QL80_.jpg',
            'stock': 10
        },
        {
            'id': '6',
            'title': 'The Alchemist',
            'author': 'Paulo Coelho',
            'summary': 'A philosophical tale about following your dreams and listening to your heart on the journey of life.',
            'seller': {'name': 'Inspirations Ltd', 'contact': 'hello@inspirations.example.com'},
            'price': 9.99,
            'genre': 'Fiction',
            'cover_url': 'https://m.media-amazon.com/images/I/51Z0nLAfLmL._AC_UF1000,1000_QL80_.jpg',
            'stock': 10
        }
    ]

    # Additional Demo Data
    demo_seller_email = 'seller_demo@example.com'
    demo_buyer_email = 'buyer_demo@example.com'

    demo_book_a = {
        'id': '7',
        'title': "Demo: Learning Flask",
        'author': 'Demo Author',
        'summary': 'A short demo book about building apps with Flask.',
        'seller': {'name': 'Demo Seller', 'contact': demo_seller_email},
        'price': 7.00,
        'genre': 'Programming',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Flask',
        'stock': 5
    }
    demo_book_b = {
        'id': '8',
        'title': "Demo: Web UI Design",
        'author': 'Design Demo',
        'summary': 'A demo book about designing simple web UIs.',
        'seller': {'name': 'Demo Seller', 'contact': demo_seller_email},
        'price': 15.00,
        'genre': 'Design',
        'cover_url': 'https://placehold.co/150x220/e0e0e0/333333?text=Design',
        'stock': 5
    }

    mock_books_data.append(demo_book_a)
    mock_books_data.append(demo_book_b)

    # Prepare Users Dictionary
    users_to_seed = {}

    # 1. Admin
    users_to_seed['admin@bookbazaar.com'] = {
        'name': 'Administrator',
        'password': generate_password_hash('admin@bookbazaar.com'),
        'role': 'admin'
    }

    # 2. Sellers from Books
    for book in mock_books_data:
        s_email = book['seller']['contact']
        s_name = book['seller']['name']
        if s_email not in users_to_seed:
            users_to_seed[s_email] = {
                'name': s_name,
                'password': generate_password_hash(s_email),
                'role': 'seller'
            }

    # 3. Demo Buyer
    users_to_seed[demo_buyer_email] = {
        'name': 'Demo Buyer',
        'password': generate_password_hash('buyer_demo@example.com'),
        'role': 'customer'
    }

    # 4. Demo Order (Split by seller as per AWS app logic)
    # The demo order contains items from demo_book_a and demo_book_b, both owned by 'seller_demo@example.com'
    # So it will be just one order entry in DynamoDB

    order_id = 'ORD-DEMO-1'
    order_created = datetime.utcnow().isoformat()

    # Items need to be Decimal for DynamoDB
    items = []
    items.append({
        'book_id': demo_book_a['id'],  # aws_app uses book_id in items
        'title': demo_book_a['title'],
        'author': demo_book_a['author'],
        'qty': 1,
        'price': Decimal(str(demo_book_a['price'])),
        'subtotal': Decimal(str(demo_book_a['price']))
    })
    items.append({
        'book_id': demo_book_b['id'],
        'title': demo_book_b['title'],
        'author': demo_book_b['author'],
        'qty': 2,
        'price': Decimal(str(demo_book_b['price'])),
        'subtotal': Decimal(str(demo_book_b['price'] * 2))
    })

    total = sum(it['subtotal'] for it in items)

    demo_orders = [
        {
            'id': f"{order_id}-{demo_seller_email}",
            'original_order_id': order_id,
            'buyer_email': demo_buyer_email,
            'buyer_name': 'Demo Buyer',
            'seller_email': demo_seller_email,
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
    ]

    # --- EXECUTE SEEDING ---

    # 1. Seed Users
    print("\nSeeding Users...")
    with users_table.batch_writer() as batch:
        for email, u_data in users_to_seed.items():
            item = {
                'email': email,
                'name': u_data['name'],
                'password': u_data['password'],
                'role': u_data['role'],
                'created_at': datetime.utcnow().isoformat(),
                'addresses': [],  # Initialize empty
                # 'cart': {}, # DynamoDB doesn't like empty maps sometimes, better to leave out or handle carefully
                # 'wishlist': []
            }
            batch.put_item(Item=item)
            print(f"  Processed User: {email}")

    # 2. Seed Books
    print("\nSeeding Books...")
    with books_table.batch_writer() as batch:
        for book in mock_books_data:
            item = {
                'id': book['id'],
                'title': book['title'],
                'author': book['author'],
                'summary': book['summary'],
                'seller_name': book['seller']['name'],
                'seller_email': book['seller']['contact'],
                'price': Decimal(str(book['price'])),
                'genre': book['genre'],
                'cover_url': book['cover_url'],
                'stock': int(book['stock']),
                'created_at': datetime.utcnow().isoformat()
            }
            batch.put_item(Item=item)
            print(f"  Processed Book: {book['title']}")

    # 3. Seed Orders
    print("\nSeeding Orders...")
    with orders_table.batch_writer() as batch:
        for order in demo_orders:
            batch.put_item(Item=order)
            print(f"  Processed Order: {order['id']}")

    print("\nSeeding Complete!")
    print("\n--- List of Seeded Emails ---")
    for email in sorted(users_to_seed.keys()):
        print(email)


if __name__ == '__main__':
    seed_data()
