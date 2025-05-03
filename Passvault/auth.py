import tkinter as tk
from tkinter import messagebox
import bcrypt
from utils import validate_email, validate_password, show_loading, hide_loading
import mysql.connector
import logging
import re

def signup(app, username, email, password):
    if not all([username, email, password]):
        messagebox.showerror("Error", "All fields required.")
        return
    if not validate_email(email):
        messagebox.showerror("Error", "Invalid email format.")
        return
    if not validate_password(password):
        messagebox.showerror("Error", "Password must be 8+ characters with uppercase, lowercase, numbers, special characters.")
        return

    loading = show_loading(app.signup_frame)
    try:
        db = app.db_pool.get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s OR email=%s", (username, email))
        if cursor.fetchone():
            messagebox.showerror("Error", "Username or Email exists.")
        else:
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            hashed_password_str = hashed_password.decode('utf-8')
            logging.info(f"Generated bcrypt hash for user {username}: {hashed_password_str[:10]}...")
            cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                           (username, email, hashed_password_str))
            db.commit()
            messagebox.showinfo("Success", "Account created!")
            app.switch_to_login()
    except mysql.connector.Error as e:
        logging.error(f"Signup database error: {e}")
        messagebox.showerror("Error", f"Database error during signup: {str(e)}")
    except Exception as e:
        logging.error(f"Signup error: {e}")
        messagebox.showerror("Error", "Failed to create account.")
    finally:
        hide_loading(loading)
        if 'db' in locals():
            db.close()

def login(app, username, password):
    if not all([username, password]):
        messagebox.showerror("Error", "All fields required.")
        return

    loading = show_loading(app.login_frame)
    try:
        db = app.db_pool.get_connection()
        cursor = db.cursor()
        cursor.execute("SELECT id, password FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        if not user:
            messagebox.showerror("Error", "Invalid username or password.")
            return

        stored_hash = user[1]
        if not re.match(r'^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$', stored_hash):
            logging.error(f"Invalid bcrypt hash format for user {username}: {stored_hash[:10]}...")
            messagebox.showerror("Error", "Stored password hash is invalid. Please re-register.")
            return

        logging.info(f"Verifying password for user {username}, stored hash: {stored_hash[:10]}...")
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            app.current_user_id = user[0]
            messagebox.showinfo("Success", f"Welcome, {username}!")
            app.switch_to_dashboard()
        else:
            messagebox.showerror("Error", "Invalid username or password.")
    except mysql.connector.OperationalError as e:
        logging.error(f"Login database connection error: {e}")
        messagebox.showerror("Error", "Cannot connect to the database. Please check your MySQL server.")
    except mysql.connector.ProgrammingError as e:
        logging.error(f"Login query error: {e}")
        messagebox.showerror("Error", "Database query failed. Ensure the 'users' table exists.")
    except ValueError as e:
        logging.error(f"Login bcrypt error for user {username}: {e}, hash: {stored_hash[:10]}...")
        messagebox.showerror("Error", "Stored password hash is invalid. Please re-register.")
    except Exception as e:
        logging.error(f"Login error for user {username}: {e}")
        messagebox.showerror("Error", f"Failed to login: {str(e)}")
    finally:
        hide_loading(loading)
        if 'db' in locals():
            db.close()