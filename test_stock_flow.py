from app import app, USERS, MOCK_BOOKS


def find_book_by_title(title):
    for b in MOCK_BOOKS:
        if b.get('title') == title:
            return b
    return None


with app.test_client() as c:
    # Create seller
    seller_email = 'test_seller@example.com'
    seller_pw = 'sellerpass'
    c.post('/signup', data={'name': 'Test Seller',
           'email': seller_email, 'password': seller_pw, 'role': 'seller'})
    # Login seller
    c.post('/login', data={'email': seller_email, 'password': seller_pw})
    # Add a book with stock 3
    title = 'Test Book For Stock'
    resp = c.post('/seller/add-book', data={
        'title': title,
        'author': 'Author A',
        'price': '5.00',
        'summary': 'A test book',
        'genre': 'Test',
        'cover_url': '',
        'stock': '3'
    }, follow_redirects=True)

    book = find_book_by_title(title)
    assert book is not None, 'Book was not added by seller'
    print('Initial stock:', book.get('stock'))

    # logout seller
    c.get('/logout')

    # create customer
    cust_email = 'test_customer@example.com'
    cust_pw = 'custpass'
    c.post('/signup', data={'name': 'Test Customer',
           'email': cust_email, 'password': cust_pw, 'role': 'customer'})
    c.post('/login', data={'email': cust_email, 'password': cust_pw})

    # add to cart twice
    bid = book.get('id')
    r1 = c.post(f'/cart/add/{bid}', follow_redirects=True)
    r2 = c.post(f'/cart/add/{bid}', follow_redirects=True)
    # verify cart in session-like (we can't access session easily here), proceed to payment
    payment_data = {
        'name': 'Test Customer',
        'line1': '123 Test St',
        'city': 'City',
        'state': 'ST',
        'zip': '11111',
        'country': 'Test',
        'phone': '000',
        'save_address': 'on'
    }
    pay = c.post('/payment', data=payment_data, follow_redirects=True)
    # after payment, stock should have decreased by 2
    book_after = find_book_by_title(title)
    print('Stock after order:', book_after.get('stock'))
    assert book_after.get('stock') == max(0, 3 - 2)
    print('Seller copy stock:', USERS.get(
        seller_email, {}).get('books', [])[-1].get('stock'))

print('Test completed')
