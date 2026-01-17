from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'dev-secret-change-me'


USERS = {}


@app.route('/')
def index():
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
    user = USERS.get(email)
    if not user or not check_password_hash(user.get('password', ''), password):
        flash('Invalid credentials.', 'error')
        return redirect(url_for('index'))

    session['user'] = {'email': email, 'name': user.get('name', '')}
    flash('Logged in successfully.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    user = session.get('user')
    if not user:
        return redirect(url_for('index'))
    return render_template('dashboard.html', user=user)


@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out.', 'info')
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
