import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from constants import COLORS, FONTS
from utils import truncate_text, show_loading, hide_loading

def create_secure_pass_sharing_frame(parent, app):
    frame = tk.Frame(parent, bg=COLORS["background"])
    frame.load = lambda: load_shared_passwords()

    content_frame = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                             highlightbackground=COLORS["border"])
    content_frame.pack(pady=60, padx=60, fill="both", expand=True)

    tk.Label(content_frame, text="Secure Password Sharing", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=30)

    input_frame = tk.Frame(content_frame, bg=COLORS["card_bg"])
    input_frame.pack(fill="x", padx=20, pady=20)

    tk.Label(input_frame, text="Service", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_service = ttk.Entry(input_frame, width=20)
    entry_service.pack(side="left", padx=10)

    tk.Label(input_frame, text="Recipient", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_recipient = ttk.Entry(input_frame, width=20)
    entry_recipient.pack(side="left", padx=10)

    tk.Label(input_frame, text="Share Status", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_share_status = ttk.Entry(input_frame, width=20)
    entry_share_status.pack(side="left", padx=10)

    tk.Button(input_frame, text="Share Pass", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: share_password(), relief="flat").pack(side="left", padx=20)
    
    tk.Button(input_frame, text="Delete Share", bg=COLORS["danger"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: delete_record(), relief="flat").pack(side="left", padx=20)

    tree_frame = tk.Frame(content_frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                          highlightbackground=COLORS["border"])
    tree_frame.pack(fill="both", expand=True, padx=20, pady=20)

    tree = ttk.Treeview(tree_frame, columns=("Service", "Recipient", "Shared Date", "Share Status", "Created At", "Updated At"), show="headings",
                        style="Treeview")
    tree.heading("Service", text="Service")
    tree.heading("Recipient", text="Recipient")
    tree.heading("Shared Date", text="Shared Date")
    tree.heading("Share Status", text="Share Status")
    tree.heading("Created At", text="Created At")
    tree.heading("Updated At", text="Updated At")
    tree.column("Service", width=150)
    tree.column("Recipient", width=150)
    tree.column("Shared Date", width=150)
    tree.column("Share Status", width=150)
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
            entry_recipient.delete(0, tk.END)
            entry_recipient.insert(0, item["values"][1])
            entry_share_status.delete(0, tk.END)
            entry_share_status.insert(0, item["values"][3])

    tree.bind("<<TreeviewSelect>>", on_row_select)

    def alternate_row_colors():
        for i, item in enumerate(tree.get_children()):
            if i % 2 == 0:
                tree.item(item, tags=("even",))
            else:
                tree.item(item, tags=("odd",))
        tree.tag_configure("even", background=COLORS["table_bg"])
        tree.tag_configure("odd", background=COLORS["table_alt"])

    def share_password():
        service = entry_service.get().strip()
        recipient = entry_recipient.get().strip()
        share_status = entry_share_status.get().strip() or "Pending"

        if not all([service, recipient]):
            messagebox.showerror("Error", "Service and Recipient are required.")
            return

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO shared_passwords (user_id, service, recipient, shared_date, share_status, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (app.current_user_id, service, recipient, current_time, share_status, current_time, current_time)
            )
            db.commit()
            load_shared_passwords()
            entry_service.delete(0, tk.END)
            entry_recipient.delete(0, tk.END)
            entry_share_status.delete(0, tk.END)
            messagebox.showinfo("Success", "Password shared successfully!")
        except Exception as e:
            logging.error(f"Share password error: {e}")
            messagebox.showerror("Error", "Failed to share password.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    def delete_record():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a shared password to delete.")
            return

        service = tree.item(selected_item)["values"][0]
        recipient = tree.item(selected_item)["values"][1]
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete shared password for '{service}'?"):
            loading = show_loading(frame)
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                cursor.execute(
                    "DELETE FROM shared_passwords WHERE user_id=%s AND service=%s AND recipient=%s",
                    (app.current_user_id, service, recipient)
                )
                db.commit()
                load_shared_passwords()
                entry_service.delete(0, tk.END)
                entry_recipient.delete(0, tk.END)
                entry_share_status.delete(0, tk.END)
                messagebox.showinfo("Success", "Shared password deleted successfully!")
            except Exception as e:
                logging.error(f"Delete shared password error: {e}")
                messagebox.showerror("Error", "Failed to delete shared password.")
            finally:
                hide_loading(loading)
                if 'db' in locals():
                    db.close()

    def load_shared_passwords():
        for item in tree.get_children():
            tree.delete(item)
        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            cursor.execute(
                "SELECT service, recipient, shared_date, share_status, created_at, updated_at "
                "FROM shared_passwords WHERE user_id=%s",
                (app.current_user_id,)
            )
            for row in cursor.fetchall():
                tree.insert("", "end", values=(
                    truncate_text(row[0]),
                    truncate_text(row[1]),
                    truncate_text(str(row[2])),
                    truncate_text(row[3]),
                    truncate_text(str(row[4])),
                    truncate_text(str(row[5]))
                ))
            alternate_row_colors()
        except Exception as e:
            logging.error(f"Load shared passwords error: {e}")
            messagebox.showerror("Error", "Failed to load shared passwords.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    return frame