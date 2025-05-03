import re
import string
import random
import tkinter as tk
from tkinter import messagebox
from constants import COLORS
from cryptography.fernet import Fernet
import qrcode
import base64
import logging
import os

def truncate_text(text, length=30):
    """Truncate text to a specified length, appending '...' if longer."""
    return text[:length] + "..." if len(text) > length else text

def validate_email(email):
    """Validate email format using regex."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_phone(phone):
    """Validate phone number format (10-15 digits, optional +) or allow empty."""
    pattern = r'^\+?1?\d{10,15}$'
    return bool(re.match(pattern, phone)) or not phone

def validate_password(password):
    """Validate password: min 8 chars, at least one uppercase, one digit."""
    return len(password) >= 8 and any(c.isupper() for c in password) and any(c.isdigit() for c in password)

def generate_password(length=16, use_uppercase=True, use_numbers=True, use_special=True):
    """Generate a random password based on specified criteria."""
    try:
        characters = string.ascii_lowercase
        if use_uppercase:
            characters += string.ascii_uppercase
        if use_numbers:
            characters += string.digits
        if use_special:
            characters += string.punctuation

        if not characters:
            raise ValueError("At least one character set must be selected.")

        password = [
            random.choice(string.ascii_lowercase),
            random.choice(string.ascii_uppercase) if use_uppercase else random.choice(string.ascii_lowercase),
            random.choice(string.digits) if use_numbers else random.choice(string.ascii_lowercase),
            random.choice(string.punctuation) if use_special else random.choice(string.ascii_lowercase)
        ]

        password += [random.choice(characters) for _ in range(length - len(password))]
        random.shuffle(password)
        return ''.join(password)
    except Exception as e:
        logging.error(f"Password generation error: {e}")
        messagebox.showerror("Error", "Failed to generate password.")
        return None

def generate_encryption_key():
    """Generate a Fernet encryption key."""
    try:
        return Fernet.generate_key()
    except Exception as e:
        logging.error(f"Encryption key generation error: {e}")
        messagebox.showerror("Error", "Failed to generate encryption key.")
        return None

def encrypt_data(data, key):
    """Encrypt data using Fernet symmetric encryption."""
    try:
        if isinstance(data, str):
            data = data.encode()
        fernet = Fernet(key)
        return fernet.encrypt(data)
    except Exception as e:
        logging.error(f"Data encryption error: {e}")
        messagebox.showerror("Error", "Failed to encrypt data.")
        return None

def decrypt_data(encrypted_data, key):
    """Decrypt data using Fernet symmetric encryption."""
    try:
        fernet = Fernet(key)
        decrypted = fernet.decrypt(encrypted_data)
        return decrypted.decode()
    except Exception as e:
        logging.error(f"Data decryption error: {e}")
        messagebox.showerror("Error", "Failed to decrypt data.")
        return None

def generate_qr_code(data, filename="qr_code.png"):
    """Generate a QR code from data and save it as an image."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filename)
        return filename
    except Exception as e:
        logging.error(f"QR code generation error: {e}")
        messagebox.showerror("Error", "Failed to generate QR code.")
        return None

def format_audit_log(table_name, action, record_id, details):
    """Format an audit log entry for consistency."""
    try:
        return {
            "table_name": table_name,
            "action": action,
            "record_id": record_id,
            "change_details": truncate_text(str(details), 100),
            "timestamp": "CURRENT_TIMESTAMP"  # Handled by SQL
        }
    except Exception as e:
        logging.error(f"Audit log formatting error: {e}")
        return None

def validate_file_path(file_path):
    """Validate that a file path is safe and exists."""
    try:
        if not file_path:
            return False
        absolute_path = os.path.abspath(file_path)
        if not os.path.exists(absolute_path):
            return False
        if not os.path.isfile(absolute_path):
            return False
        # Prevent path traversal
        if ".." in os.path.relpath(absolute_path):
            return False
        return True
    except Exception as e:
        logging.error(f"File path validation error: {e}")
        return False

def show_loading(parent):
    """Display a loading animation with rotating arcs."""
    loading_frame = tk.Frame(parent, bg=COLORS["background"])
    loading_frame.place(relx=0.5, rely=0.5, anchor="center")
    canvas = tk.Canvas(loading_frame, width=50, height=50, bg=COLORS["background"], highlightthickness=0)
    canvas.pack()
    angles = [0, 90, 180, 270]
    arcs = []
    for i, angle in enumerate(angles):
        arcs.append(canvas.create_arc(10, 10, 40, 40, start=angle, extent=89, outline=COLORS["primary"], width=4))
    
    def animate():
        for arc in arcs:
            current_start = float(canvas.itemcget(arc, "start"))
            canvas.itemconfig(arc, start=current_start + 10)
        if loading_frame.winfo_exists():
            loading_frame.after(50, animate)
    
    animate()
    return loading_frame

def hide_loading(loading_frame):
    """Remove the loading animation."""
    if loading_frame and loading_frame.winfo_exists():
        loading_frame.destroy()