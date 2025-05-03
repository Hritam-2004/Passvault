import tkinter as tk
from tkinter import ttk, messagebox
import mysql.connector
import logging
from constants import COLORS, FONTS
from ui import create_login_frame, create_signup_frame, create_dashboard_frame
from db import DatabaseConnectionPool
from utils import validate_email, show_loading, hide_loading

try:
    import bcrypt
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "bcrypt"])
    import importlib
    bcrypt = importlib.import_module("bcrypt")

# Ensure cryptography is installed before importing anything that uses it
try:
    from cryptography.fernet import Fernet
except ImportError:
    import sys
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
    from cryptography.fernet import Fernet

class PasswordManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PassVault")
        self.root.geometry("1440x900")
        self.db_pool = DatabaseConnectionPool()
        self.current_user_id = None

        # Main container
        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        # Initialize frames
        self.login_frame = create_login_frame(self.container, self)
        self.signup_frame = create_signup_frame(self.container, self)
        self.dashboard_frame = create_dashboard_frame(self.container, self)

        # Show login frame by default
        self.switch_to_login()

        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                            filename='passvault.log')

    def switch_to_login(self):
        self.current_user_id = None
        self.signup_frame.pack_forget()
        self.dashboard_frame.pack_forget()
        self.login_frame.pack(fill="both", expand=True)

    def switch_to_signup(self):
        self.login_frame.pack_forget()
        self.dashboard_frame.pack_forget()
        self.signup_frame.pack(fill="both", expand=True)

    def switch_to_dashboard(self):
        self.login_frame.pack_forget()
        self.signup_frame.pack_forget()
        self.dashboard_frame.pack(fill="both", expand=True)

    def login(self):
        username = self.login_entry_user.get().strip()
        password = self.login_entry_pass.get().strip()

        if not all([username, password]):
            messagebox.showerror("Error", "All fields are required.")
            return

        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                db = self.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
                user = cursor.fetchone()
                if user and bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8')):
                    self.current_user_id = user[0]
                    db.commit()
                    self.switch_to_dashboard()
                    messagebox.showinfo("Success", "Login successful!")
                    return
                else:
                    db.rollback()
                    messagebox.showerror("Error", "Invalid username or password.")
                    return
            except mysql.connector.Error as e:
                logging.error(f"Login error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to login. Try restoring from backup?"):
                        self.restore_backup()
                    else:
                        messagebox.showerror("Error", f"Failed to login after retries: {e}")
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def signup(self):
        username = self.signup_entry_user.get().strip()
        email = self.signup_entry_email.get().strip()
        password = self.signup_entry_pass.get().strip()

        if not all([username, email, password]):
            messagebox.showerror("Error", "All fields are required.")
            return
        if not validate_email(email):
            messagebox.showerror("Error", "Invalid email format.")
            return
        if len(password) < 8:
            messagebox.showerror("Error", "Password must be at least 8 characters.")
            return

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                db = self.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("CALL BackupUserData(%s)", (0,))  # 0 for new user
                cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
                if cursor.fetchone():
                    db.rollback()
                    messagebox.showerror("Error", "Username or email already exists.")
                    return
                cursor.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                               (username, email, hashed_password))
                user_id = cursor.lastrowid
                cursor.execute("CALL UpdateUserSettings(%s, %s, %s)", (user_id, False, True))
                db.commit()
                messagebox.showinfo("Success", "Account created! Please login.")
                self.switch_to_login()
                return
            except mysql.connector.Error as e:
                logging.error(f"Signup error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to create account. Try restoring from backup?"):
                        self.restore_backup()
                    else:
                        messagebox.showerror("Error", f"Failed to create account after retries: {e}")
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def change_password(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Change Password")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        card = tk.Frame(dialog, bg=COLORS["card_bg"], bd=0, highlightbackground=COLORS["primary"], highlightthickness=2)
        card.pack(pady=20, padx=20, fill="both", expand=True)

        tk.Label(card, text="Change Password", font=FONTS["subheading"], bg=COLORS["card_bg"]).pack(pady=10)
        
        tk.Label(card, text="Current Password", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
        current_pass = ttk.Entry(card, show="*", width=25)
        current_pass.pack(pady=5)
        
        tk.Label(card, text="New Password", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
        new_pass = ttk.Entry(card, show="*", width=25)
        new_pass.pack(pady=5)
        
        tk.Label(card, text="Confirm New Password", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
        confirm_pass = ttk.Entry(card, show="*", width=25)
        confirm_pass.pack(pady=5)

        def submit():
            current = current_pass.get().strip()
            new = new_pass.get().strip()
            confirm = confirm_pass.get().strip()

            if not all([current, new, confirm]):
                messagebox.showerror("Error", "All fields are required.", parent=dialog)
                return
            if new != confirm:
                messagebox.showerror("Error", "New passwords do not match.", parent=dialog)
                return
            if len(new) < 8:
                messagebox.showerror("Error", "New password must be at least 8 characters.", parent=dialog)
                return

            max_retries = 3
            retry_count = 0
            while retry_count < max_retries:
                try:
                    db = self.db_pool.get_connection()
                    cursor = db.cursor()
                    db.start_transaction()
                    cursor.execute("CALL BackupUserData(%s)", (self.current_user_id,))
                    cursor.execute("SELECT password FROM users WHERE id = %s", (self.current_user_id,))
                    stored_password = cursor.fetchone()[0]
                    if not bcrypt.checkpw(current.encode('utf-8'), stored_password.encode('utf-8')):
                        db.rollback()
                        messagebox.showerror("Error", "Current password is incorrect.", parent=dialog)
                        return
                    hashed_new_password = bcrypt.hashpw(new.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    cursor.execute("UPDATE users SET password = %s WHERE id = %s",
                                   (hashed_new_password, self.current_user_id))
                    db.commit()
                    messagebox.showinfo("Success", "Password changed successfully!", parent=dialog)
                    dialog.destroy()
                    return
                except mysql.connector.Error as e:
                    logging.error(f"Change password error (attempt {retry_count + 1}): {e}")
                    if 'db' in locals():
                        db.rollback()
                    retry_count += 1
                    if retry_count == max_retries:
                        if messagebox.askyesno("Error", "Failed to change password. Try restoring from backup?", parent=dialog):
                            self.restore_backup()
                        else:
                            messagebox.showerror("Error", f"Failed to change password after retries: {e}", parent=dialog)
                finally:
                    if 'cursor' in locals():
                        cursor.close()
                    if 'db' in locals():
                        db.close()

        tk.Button(card, text="Submit", bg=COLORS["primary"], fg=COLORS["dark_fg"],
                  font=FONTS["button"], width=15, command=submit, relief="flat").pack(pady=10)
        tk.Button(card, text="Cancel", bg=COLORS["secondary"], fg=COLORS["dark_fg"],
                  font=FONTS["button"], width=15, command=dialog.destroy, relief="flat").pack(pady=5)

    def restore_backup(self):
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                db = self.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("""
                    SELECT id, table_name, backup_time
                    FROM backup_logs
                    WHERE record_id = %s
                    ORDER BY backup_time DESC
                    LIMIT 5
                """, (self.current_user_id or 0,))
                backups = cursor.fetchall()
                if not backups:
                    messagebox.showinfo("Info", "No backups available.")
                    db.rollback()
                    return
                backup_options = [f"ID: {b[0]} | Table: {b[1]} | Time: {b[2]}" for b in backups]
                selected = tk.StringVar()
                dialog = tk.Toplevel(self.root)
                dialog.title("Select Backup")
                dialog.geometry("400x300")
                tk.Label(dialog, text="Select a backup to restore:", font=FONTS["body"]).pack(pady=10)
                combo = ttk.Combobox(dialog, textvariable=selected, values=backup_options, state="readonly")
                combo.pack(pady=10)
                def confirm_restore():
                    if not selected.get():
                        messagebox.showerror("Error", "Please select a backup.", parent=dialog)
                        return
                    backup_id = int(selected.get().split(" | ")[0].replace("ID: ", ""))
                    try:
                        cursor.execute("CALL RestoreUserData(%s)", (backup_id,))
                        db.commit()
                        messagebox.showinfo("Success", "Backup restored successfully!", parent=dialog)
                        dialog.destroy()
                    except mysql.connector.Error as e:
                        db.rollback()
                        messagebox.showerror("Error", f"Failed to restore backup: {e}", parent=dialog)
                        dialog.destroy()
                tk.Button(dialog, text="Restore", command=confirm_restore, bg=COLORS["primary"],
                          fg=COLORS["dark_fg"], font=FONTS["button"]).pack(pady=10)
                tk.Button(dialog, text="Cancel", command=dialog.destroy, bg=COLORS["secondary"],
                          fg=COLORS["dark_fg"], font=FONTS["button"]).pack(pady=10)
                dialog.transient(self.root)
                dialog.grab_set()
                self.root.wait_window(dialog)
                break
            except mysql.connector.Error as e:
                logging.error(f"Restore backup error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    messagebox.showerror("Error", f"Failed to load backups after retries: {e}")
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def create_backup(self):
        if not self.current_user_id:
            messagebox.showerror("Error", "You must be logged in to create a backup.")
            return
        max_retries = 3
        retry_count = 0
        loading = show_loading(self.frames.get("home", self.container))
        while retry_count < max_retries:
            try:
                db = self.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("CALL BackupUserData(%s)", (self.current_user_id,))
                db.commit()
                messagebox.showinfo("Success", "Backup created successfully!")
                self.load_backups()  # Refresh the backups list
                break
            except mysql.connector.Error as e:
                logging.error(f"Create backup error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    messagebox.showerror("Error", f"Failed to create backup after retries: {e}")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def load_backups(self):
        if not hasattr(self, 'backups_tree'):
            logging.warning("Backups Treeview not initialized.")
            return
        tree = self.backups_tree
        for item in tree.get_children():
            tree.delete(item)
        max_retries = 3
        retry_count = 0
        loading = show_loading(self.frames.get("backups", self.container))
        while retry_count < max_retries:
            try:
                db = self.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("""
                    SELECT id, table_name, record_id, backup_time
                    FROM backup_logs
                    WHERE record_id = %s
                    ORDER BY backup_time DESC
                    LIMIT 50
                """, (self.current_user_id,))
                backups = cursor.fetchall()
                for backup in backups:
                    tree.insert("", "end", values=(
                        backup[0],
                        backup[1],
                        backup[2],
                        backup[3]
                    ))
                db.commit()
                break
            except mysql.connector.Error as e:
                logging.error(f"Load backups error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    messagebox.showerror("Error", f"Failed to load backups after retries: {e}")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def generate_password_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Generate Password")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        card = tk.Frame(dialog, bg=COLORS["card_bg"], bd=0, highlightbackground=COLORS["primary"], highlightthickness=2)
        card.pack(pady=20, padx=20, fill="both", expand=True)

        tk.Label(card, text="Generate Password", font=FONTS["subheading"], bg=COLORS["card_bg"]).pack(pady=10)
        tk.Label(card, text="Feature not yet implemented.", font=FONTS["body"], bg=COLORS["card_bg"]).pack(pady=10)
        tk.Button(card, text="Close", bg=COLORS["secondary"], fg=COLORS["dark_fg"],
                  font=FONTS["button"], width=15, command=dialog.destroy, relief="flat").pack(pady=10)

    def upload_file_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Upload File")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        card = tk.Frame(dialog, bg=COLORS["card_bg"], bd=0, highlightbackground=COLORS["primary"], highlightthickness=2)
        card.pack(pady=20, padx=20, fill="both", expand=True)

        tk.Label(card, text="Upload File", font=FONTS["subheading"], bg=COLORS["card_bg"]).pack(pady=10)
        tk.Label(card, text="Feature not yet implemented.", font=FONTS["body"], bg=COLORS["card_bg"]).pack(pady=10)
        tk.Button(card, text="Close", bg=COLORS["secondary"], fg=COLORS["dark_fg"],
                  font=FONTS["button"], width=15, command=dialog.destroy, relief="flat").pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = PasswordManagerApp(root)
    root.mainloop()