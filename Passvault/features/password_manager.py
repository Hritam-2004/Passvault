import tkinter as tk
from tkinter import ttk, messagebox
import logging
import re
from datetime import datetime
from constants import COLORS, FONTS
from utils import truncate_text, show_loading, hide_loading

def create_password_manager_frame(parent, app):
    frame = tk.Frame(parent, bg=COLORS["background"])
    frame.load = lambda: load_passwords()

    content_frame = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                             highlightbackground=COLORS["border"])
    content_frame.pack(pady=60, padx=60, fill="both", expand=True)

    tk.Label(content_frame, text="Password Manager", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=30)

    input_frame = tk.Frame(content_frame, bg=COLORS["card_bg"])
    input_frame.pack(fill="x", padx=20, pady=20)

    tk.Label(input_frame, text="Service", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_service = ttk.Entry(input_frame, width=20)
    entry_service.pack(side="left", padx=10)

    tk.Label(input_frame, text="Username", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_username = ttk.Entry(input_frame, width=20)
    entry_username.pack(side="left", padx=10)

    tk.Label(input_frame, text="Password", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_password = ttk.Entry(input_frame, width=20, show="*")
    entry_password.pack(side="left", padx=10)

    tk.Label(input_frame, text="Expiry Date", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_expiration = ttk.Entry(input_frame, width=20)
    entry_expiration.pack(side="left", padx=10)

    tk.Button(input_frame, text="Add Password", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: add_password(), relief="flat").pack(side="left", padx=20)
    
    tk.Button(input_frame, text="Delete Password", bg=COLORS["danger"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: delete_record(), relief="flat").pack(side="left", padx=20)

    tree_frame = tk.Frame(content_frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                          highlightbackground=COLORS["border"])
    tree_frame.pack(fill="both", expand=True, padx=20, pady=20)

    tree = ttk.Treeview(tree_frame, columns=("Service", "Username", "Password", "Expiry Date", "Strength", "Created At", "Updated At"), show="headings",
                        style="Treeview")
    tree.heading("Service", text="Service")
    tree.heading("Username", text="Username")
    tree.heading("Password", text="Password")
    tree.heading("Expiry Date", text="Expiry Date")
    tree.heading("Strength", text="Strength")
    tree.heading("Created At", text="Created At")
    tree.heading("Updated At", text="Updated At")
    tree.column("Service", width=150)
    tree.column("Username", width=150)
    tree.column("Password", width=150)
    tree.column("Expiry Date", width=150)
    tree.column("Strength", width=100)
    tree.column("Created At", width=150)
    tree.column("Updated At", width=150)

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def on_row_select(event):
        selected_item = tree.selection()
        if selected_item:
            item = tree.item(selected_item)
            entry_service.delete(0, tk.END)
            entry_service.insert(0, item["values"][0])
            entry_username.delete(0, tk.END)
            entry_username.insert(0, item["values"][1])
            entry_password.delete(0, tk.END)
            entry_password.insert(0, item["values"][2])
            entry_expiration.delete(0, tk.END)
            entry_expiration.insert(0, item["values"][3])

    tree.bind("<<TreeviewSelect>>", on_row_select)

    def alternate_row_colors():
        for i, item in enumerate(tree.get_children()):
            if i % 2 == 0:
                tree.item(item, tags=("even",))
            else:
                tree.item(item, tags=("odd",))
        tree.tag_configure("even", background=COLORS["table_bg"])
        tree.tag_configure("odd", background=COLORS["table_alt"])

    def calculate_password_strength(password):
        length = len(password)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))

        score = sum([has_upper, has_lower, has_digit, has_special]) + (length // 8)
        if score >= 4 or length >= 12:
            return "Strong"
        elif score >= 3 or length >= 8:
            return "Medium"
        else:
            return "Weak"

    def add_password():
        service = entry_service.get().strip()
        username = entry_username.get().strip()
        password = entry_password.get().strip()
        expiration_date = entry_expiration.get().strip()

        if not all([service, username, password]):
            messagebox.showerror("Error", "Service, Username, and Password are required.")
            return

        try:
            if expiration_date:
                datetime.strptime(expiration_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid expiration date format (use YYYY-MM-DD).")
            return

        password_strength = calculate_password_strength(password)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO passwords (user_id, service, username, password, expiration_date, password_strength, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (app.current_user_id, service, username, password, expiration_date or None, password_strength, current_time, current_time)
            )
            db.commit()
            load_passwords()
            entry_service.delete(0, tk.END)
            entry_username.delete(0, tk.END)
            entry_password.delete(0, tk.END)
            entry_expiration.delete(0, tk.END)
            messagebox.showinfo("Success", "Password added successfully!")
        except Exception as e:
            logging.error(f"Add password error: {e}")
            messagebox.showerror("Error", "Failed to add password.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    def delete_record():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a password to delete.")
            return

        service = tree.item(selected_item)["values"][0]
        username = tree.item(selected_item)["values"][1]
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete password for '{service}'?"):
            loading = show_loading(frame)
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                cursor.execute(
                    "DELETE FROM passwords WHERE user_id=%s AND service=%s AND username=%s",
                    (app.current_user_id, service, username)
                )
                db.commit()
                load_passwords()
                entry_service.delete(0, tk.END)
                entry_username.delete(0, tk.END)
                entry_password.delete(0, tk.END)
                entry_expiration.delete(0, tk.END)
                messagebox.showinfo("Success", "Password deleted successfully!")
            except Exception as e:
                logging.error(f"Delete password error: {e}")
                messagebox.showerror("Error", "Failed to delete password.")
            finally:
                hide_loading(loading)
                if 'db' in locals():
                    db.close()

    def load_passwords():
        for item in tree.get_children():
            tree.delete(item)
        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            cursor.execute(
                "SELECT service, username, password, expiration_date, password_strength, created_at, updated_at "
                "FROM passwords WHERE user_id=%s",
                (app.current_user_id,)
            )
            for row in cursor.fetchall():
                tree.insert("", "end", values=(
                    truncate_text(row[0]),
                    truncate_text(row[1]),
                    "*" * 8,
                    truncate_text(str(row[3]) if row[3] else "N/A"),
                    truncate_text(row[4]),
                    truncate_text(str(row[5])),
                    truncate_text(str(row[6]))
                ))
            alternate_row_colors()
        except Exception as e:
            logging.error(f"Load passwords error: {e}")
            messagebox.showerror("Error", "Failed to load passwords.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    return frame