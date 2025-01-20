from django.shortcuts import render, redirect
from .models import User
import os, hashlib, hmac
import sqlite3
import random
import json
import re
# Load the password policy from config.json
with open('config.json') as config_file:
    config = json.load(config_file)
import string
from django.core.mail import send_mail
from django.shortcuts import render, redirect


def is_password_valid(password):
    policy = config["complexity"]

    if len(password) < config["password_length"]:
        return False

    if policy["uppercase"] and not any(char.isupper() for char in password):
        return False

    if policy["lowercase"] and not any(char.islower() for char in password):
        return False

    if policy["digits"] and not any(char.isdigit() for char in password):
        return False

    if policy["special_characters"] and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False

    return True

def hash_password(password, salt=None):
    if not salt:
        salt = os.urandom(16)  # Generate random salt
    hashed = hmac.new(salt, password.encode(), hashlib.sha256).hexdigest()
    return hashed, salt.hex()


def register(request):
    # SQLi attack
    # Payloads:
    # 1) Show SQL version: test' || (SELECT sqlite_version()) || '-' || random() || '--
    # 2) Show table names: test' || (SELECT group_concat(name) FROM sqlite_master WHERE type='table') || '-' || random() || '--

    if request.method == 'POST':
        username = request.POST.get('username', '')
        email = request.POST.get('email', '')
        password = request.POST.get('password', '')

        # Ensure all fields are provided
        if not username or not email or not password:
            return render(request, 'users/register.html', {'error': 'All fields are required.'})

        # Generate salt and hashed password using HMAC
        salt = os.urandom(16).hex()  # Generate random salt
        key = b'secret_key'  # Use a consistent key for HMAC
        hashed_password = hmac.new(key, (password + salt).encode(), hashlib.sha256).hexdigest()

        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()

        try:
            # Insert query vulnerable to SQL injection
            query = f"INSERT INTO users_user (username, email, password_hash, password_salt, created_at) VALUES ('{username}', '{email}', '{hashed_password}', '{salt}', datetime('now'))"
            print("Executing query:", query)
            cursor.execute(query)
            conn.commit()

            # Query the last inserted username to reflect the SQL injection result
            cursor.execute("SELECT username FROM users_user ORDER BY id DESC LIMIT 1")
            injected_username = cursor.fetchone()[0]

            # Display the success message with the injected username
            return render(request, 'users/login.html', {'success': f"User '{injected_username}' registered successfully!"})
        except sqlite3.Error as e:
            return render(request, 'users/register.html', {'error': str(e)})
        finally:
            conn.close()

    return render(request, 'users/register.html')


import hashlib
import hmac
import sqlite3

def login(request):

    #SQLi payload: username ' OR 1=1 --

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()

        # Vulnerable raw SQL query allowing injection in the username field
        query = f"SELECT password_hash, password_salt FROM users_user WHERE username='{username}'"
        print("Executing query:", query)
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()

        if user:
            stored_password_hash, stored_salt = user

            # Validate the password using HMAC and stored salt
            key = b'secret_key'  # Use the same key as in the registration function
            computed_hash = hmac.new(key, (password + stored_salt).encode(), hashlib.sha256).hexdigest()
            print("Computed hash:", computed_hash)  # Debug print

            # SQLi logic to demonstrate bypass
            if computed_hash == stored_password_hash or 'OR' in username or '--' in username:
                # Store user session
                request.session['username'] = username
                return render(request, 'users/dashboard.html',
                              {'message': f"User '{username}' logged in successfully!"})
            else:
                return render(request, 'users/login.html', {'error': 'Invalid credentials'})

        return render(request, 'users/login.html', {'error': 'Invalid credentials'})

    return render(request, 'users/login.html')


def forgot_password(request):
    if request.method == 'POST':
        email = request.POST['email']

        # Generate a random token using SHA-1
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        token = hashlib.sha1(random_string.encode()).hexdigest()

        # Store the token in the database
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        cursor.execute("UPDATE users_user SET reset_token = ? WHERE email = ?", (token, email))
        conn.commit()
        conn.close()

        reset_link = f"http://127.0.0.1:8000/reset-password/{token}"
        email_body = f"""
        Hello,

        You requested to reset your password. Please use the following token to reset your password:

        Reset Token: {token}

        To reset your password, click the link below:
        {reset_link}

        If you didn't request this password reset, you can safely ignore this email.

        Thanks,
        Communication LTD Team
        """
        # Send the token via email
        send_mail(
            'Password Reset Request',
            email_body,
            'communication.ltd001@gmail.com',
            [email],
            fail_silently=False,
        )

        return render(request, 'users/forgot_password.html', {'message': 'Password reset token sent to your email!'})

    return render(request, 'users/forgot_password.html')

# Reset Password Form
def reset_password(request, token):
    if request.method == 'POST':
        new_password = request.POST.get('password')

        # Validate inputs
        if not new_password:
            return render(request, 'users/reset_password.html', {'error': 'Password is required!', 'token': token})

        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        try:
            # Update the password if the reset token matches
            hashed_password = hash_password(new_password)  # Replace with your hashing logic
            cursor.execute("UPDATE users_user SET password_hash = ? WHERE reset_token = ?", (hashed_password, token))

            if cursor.rowcount == 0:
                return render(request, 'users/reset_password.html', {'error': 'Invalid or expired reset token.', 'token': token})
            conn.commit()
            message = "Password reset successful! You can now log in."
        except sqlite3.Error as e:
            message = f"Error: {str(e)}"
        finally:
            conn.close()

        cursor.execute("UPDATE users_user SET reset_token = NULL WHERE reset_token = ?", (token,))

        return render(request, 'users/login.html', {'message': message})

    # For GET requests, render the reset password page
    return render(request, 'users/reset_password.html', {'token': token})


# Change Password View
def change_password(request):
    if request.method == 'POST':
        username = request.POST['username']
        current_password = request.POST['current_password']
        new_password = request.POST['new_password']

        # Fetch user from database
        try:
            user = User.objects.get(username=username)

            # Verify current password
            salt = user.password_salt
            current_password_hash = hmac.new(salt, current_password.encode(), hashlib.sha256).digest()
            if current_password_hash != user.password_hash:
                return render(request, 'users/change_password.html', {'error': 'Current password is incorrect'})

            # Generate salt and hash the new password
            new_salt = os.urandom(16)
            new_password_hash = hmac.new(new_salt, new_password.encode(), hashlib.sha256).digest()

            # Update user password
            user.password_salt = new_salt
            user.password_hash = new_password_hash
            user.save()

            return redirect('login')
        except User.DoesNotExist:
            return render(request, 'users/change_password.html', {'error': 'User not found'})

    return render(request, 'users/change_password.html')


def add_client(request):
    # .\sqlite3.exe .\db.sqlite3
    # SELECT * FROM users_client;
    # INSERT INTO users_client (name, email) VALUES ('<script>alert("XSS");</script>', 'xss@test.com');
    # DELETE FROM users_client WHERE name LIKE '%<script>%';

    #XSS attack:ADD CLIENT
    #     # PAYLOAD: name <script>alert("Stored XSS");</script>
    #     # Then go to View clients - window should pop up
    #     # ENABLE TO SHOW POP UP WINDOWS IN BROWSER SETTINGS
    #     # Clean database before presentation!

    #SQLi atack: add client name: test' || (SELECT sqlite_version()) || '--

    if request.method == 'POST':
        client_name = request.POST['client_name']
        client_email = request.POST['client_email']

        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()

        try:
            # Insert the user-provided input into the database
            query = f"INSERT INTO users_client (name, email) VALUES ('{client_name}', '{client_email}')"
            print("Executing query:", query)
            cursor.execute(query)
            conn.commit()

            # Retrieve the last inserted name from the database
            cursor.execute("SELECT name FROM users_client ORDER BY id DESC LIMIT 1")
            result = cursor.fetchone()
            print("Retrieved result:", result)

            if result:
                processed_name = result[0]
                print("Processed name:", processed_name)
            else:
                processed_name = "Unknown"

            # Render success message
            return render(request, 'users/dashboard.html', {
                'message': f"Client '{processed_name}' added successfully!"
            })
        except sqlite3.Error as e:
            print("Database error:", e)
            return render(request, 'users/add_client.html', {'error': str(e)})
        finally:
            conn.close()

    return render(request, 'users/add_client.html')



def client_list(request):
    # xss ATTACK IN DASHBOARD-ADD CLIENT
    #     # PAYLOAD: name <script>alert("Stored XSS");</script>
    #     # Then go to View clients - window should pop up
    #     # ENABLE TO SHOW POP UP WINDOWS IN BROWSER SETTINGS
    #     # Clean database before presentation!

    ##.\sqlite3.exe .\db.sqlite3
    search_query = request.GET.get('search', '')
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    query = f"SELECT name, email FROM users_client WHERE name LIKE '%{search_query}%'"
    print(f"Executing query: {query}")
    cursor.execute(query)
    clients = cursor.fetchall()
    conn.close()
    clients_dict = [{'name': client[0], 'email': client[1]} for client in clients]

    return render(request, 'users/client_list.html', {'clients': clients_dict, 'search_query': search_query})


# Dashboard View
def dashboard(request):

    # Check if the user is logged in
    if 'username' not in request.session:
        return redirect('login')  # Redirect to login page if not logged in

    return render(request, 'users/dashboard.html', {'message': f"Welcome back, {request.session['username']}!"})

    #Fetch clients from database
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users_client")
    clients = cursor.fetchall()
    conn.close()

    return render(request, 'users/dashboard.html', {'clients': clients})

# Logout View
def logout(request):
    request.session.flush()  # Clear all session data
    return redirect('login')

def index(request):
    return render(request, 'users/index.html', {'welcome_message': 'Welcome to Communication LTD'})
