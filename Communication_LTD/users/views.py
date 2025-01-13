from django.shortcuts import render, redirect
from .models import User
import os, hashlib, hmac
import sqlite3
import random
import hashlib
import json
import re
# Load the password policy from config.json
with open('config.json') as config_file:
    config = json.load(config_file)

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


def register(request):

    #payload - username: test' || (SELECT group_concat(username) FROM users_user) || '--

    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']

        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()

        try:
            # Perform SQL injection using the provided username
            query = f"INSERT INTO users_user (username, email, password_hash, password_salt, created_at) VALUES ('{username}', '{email}', '{password}', 'salt', datetime('now'))"
            print("Executing query:", query)

            cursor.execute(query)
            conn.commit()

            # Display the username including SQL injection result
            success_message = f"User '{username}' registered successfully!"
            return render(request, 'users/login.html', {'success': success_message})

        except sqlite3.Error as e:
            return render(request, 'users/register.html', {'error': str(e)})

        finally:
            conn.close()

    return render(request, 'users/register.html')




def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        # Vulnerable raw SQL query with username and password
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        query = f"SELECT * FROM users_user WHERE username='{username}' AND password='{password}'"
        cursor.execute(query)
        user = cursor.fetchone()

        print(query)

        if user:
            return redirect('dashboard')
        else:
            return render(request, 'users/login.html', {'error': 'Invalid credentials'})

    return render(request, 'users/login.html')

def forgot_password(request):
    def forgot_password(request):
        if request.method == 'POST':
            email = request.POST['email']
            try:
                user = User.objects.get(email=email)
                reset_token = hashlib.sha1(str(random.random()).encode()).hexdigest()

                # Display reset token (for demo purposes)
                return render(request, 'users/forgot_password.html', {'reset_token': reset_token})

            except User.DoesNotExist:
                return render(request, 'users/forgot_password.html', {'error': 'User not found'})

        return render(request, 'users/forgot_password.html')


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

    # SQLi: add client - client name: test' || (SELECT sqlite_version()) || '--
    # View clients
    if request.method == 'POST':
        client_name = request.POST['client_name']
        client_email = request.POST['client_email']

        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()

        try:
            query = f"INSERT INTO users_client (name, email) VALUES ('{client_name}', '{client_email}')"
            print("Executing query:", query)
            cursor.execute(query)
            conn.commit()
        except sqlite3.Error as e:
            return render(request, 'users/add_client.html', {'error': str(e)})
        finally:
            conn.close()

        return render(request, 'users/dashboard.html', {'message': 'Client added successfully!'})

    return render(request, 'users/add_client.html')



# Client List View
def client_list(request):
    search_query = request.GET.get('search', '')

    # Vulnerable SQL Query (intentionally unsanitized for SQL injection demonstration)
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    query = f"SELECT name, email FROM users_client WHERE name LIKE '%{search_query}%'"
    cursor.execute(query)
    clients = cursor.fetchall()
    conn.close()

    # Convert the list of tuples into a list of dictionaries
    clients_dict = [{'name': client[0], 'email': client[1]} for client in clients]

    return render(request, 'users/client_list.html', {'clients': clients_dict})



# Dashboard View
def dashboard(request):
    # Fetch clients from the database
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users_client")
    clients = cursor.fetchall()
    conn.close()

    return render(request, 'users/dashboard.html', {'clients': clients})
# Logout View
def logout(request):
    return redirect('login')

def index(request):
    return render(request, 'users/index.html', {'welcome_message': 'Welcome to Communication LTD'})
