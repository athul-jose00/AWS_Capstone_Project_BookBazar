from flask import Flask, render_template, request, redirect, url_for, flash, session
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
    return redirect(url_for('index'))


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
    return render_template('dashboard.html', user=user)


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


if __name__ == '__main__':
    app.run(debug=True)
