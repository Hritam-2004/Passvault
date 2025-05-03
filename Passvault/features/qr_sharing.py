import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from constants import COLORS, FONTS
from utils import truncate_text, show_loading, hide_loading

def create_qr_sharing_frame(parent, app):
    frame = tk.Frame(parent, bg=COLORS["background"])
    frame.load = lambda: load_qr_codes()

    content_frame = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                             highlightbackground=COLORS["border"])
    content_frame.pack(pady=60, padx=60, fill="both", expand=True)

    tk.Label(content_frame, text="QR Code Sharing", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=30)

    input_frame = tk.Frame(content_frame, bg=COLORS["card_bg"])
    input_frame.pack(fill="x", padx=20, pady=20)

    tk.Label(input_frame, text="Service", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_service = ttk.Entry(input_frame, width=20)
    entry_service.pack(side="left", padx=10)

    tk.Label(input_frame, text="Username", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_username = ttk.Entry(input_frame, width=20)
    entry_username.pack(side="left", padx=10)

    tk.Label(input_frame, text="QR Code Data", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_qr_code_data = ttk.Entry(input_frame, width=20)
    entry_qr_code_data.pack(side="left", padx=10)

    tk.Button(input_frame, text="Generate QR", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: generate_qr(), relief="flat").pack(side="left", padx=20)
    
    tk.Button(input_frame, text="Delete QR", bg=COLORS["danger"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: delete_record(), relief="flat").pack(side="left", padx=20)

    tree_frame = tk.Frame(content_frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                          highlightbackground=COLORS["border"])
    tree_frame.pack(fill="both", expand=True, padx=20, pady=20)

    tree = ttk.Treeview(tree_frame, columns=("Service", "Username", "QR Code Data", "Created At", "Updated At"), show="headings",
                        style="Treeview")
    tree.heading("Service", text="Service")
    tree.heading("Username", text="Username")
    tree.heading("QR Code Data", text="QR Code Data")
    tree.heading("Created At", text="Created At")
    tree.heading("Updated At", text="Updated At")
    tree.column("Service", width=150)
    tree.column("Username", width=150)
    tree.column("QR Code Data", width=150)
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
            entry_qr_code_data.delete(0, tk.END)
            entry_qr_code_data.insert(0, item["values"][2])

    tree.bind("<<TreeviewSelect>>", on_row_select)

    def alternate_row_colors():
        for i, item in enumerate(tree.get_children()):
            if i % 2 == 0:
                tree.item(item, tags=("even",))
            else:
                tree.item(item, tags=("odd",))
        tree.tag_configure("even", background=COLORS["table_bg"])
        tree.tag_configure("odd", background=COLORS["table_alt"])

    def generate_qr():
        service = entry_service.get().strip()
        username = entry_username.get().strip()
        qr_code_data = entry_qr_code_data.get().strip()

        if not all([service, username, qr_code_data]):
            messagebox.showerror("Error", "Service, Username, and QR Code Data are required.")
            return

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO qr_codes (user_id, service, username, qr_code_data, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (app.current_user_id, service, username, qr_code_data, current_time, current_time)
            )
            db.commit()
            load_qr_codes()
            entry_service.delete(0, tk.END)
            entry_username.delete(0, tk.END)
            entry_qr_code_data.delete(0, tk.END)
            messagebox.showinfo("Success", "QR code generated!")
        except Exception as e:
            logging.error(f"Generate QR error: {e}")
            messagebox.showerror("Error", "Failed to generate QR code.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    def delete_record():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a QR code to delete.")
            return

        service = tree.item(selected_item)["values"][0]
        username = tree.item(selected_item)["values"][1]
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete QR code for '{service}'?"):
            loading = show_loading(frame)
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                cursor.execute(
                    "DELETE FROM qr_codes WHERE user_id=%s AND service=%s AND username=%s",
                    (app.current_user_id, service, username)
                )
                db.commit()
                load_qr_codes()
                entry_service.delete(0, tk.END)
                entry_username.delete(0, tk.END)
                entry_qr_code_data.delete(0, tk.END)
                messagebox.showinfo("Success", "QR code deleted successfully!")
            except Exception as e:
                logging.error(f"Delete QR code error: {e}")
                messagebox.showerror("Error", "Failed to delete QR code.")
            finally:
                hide_loading(loading)
                if 'db' in locals():
                    db.close()

    def load_qr_codes():
        for item in tree.get_children():
            tree.delete(item)
        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            cursor.execute(
                "SELECT service, username, qr_code_data, created_at, updated_at "
                "FROM qr_codes WHERE user_id=%s",
                (app.current_user_id,)
            )
            for row in cursor.fetchall():
                tree.insert("", "end", values=(
                    truncate_text(row[0]),
                    truncate_text(row[1]),
                    truncate_text(row[2] or "N/A"),
                    truncate_text(str(row[3])),
                    truncate_text(str(row[4]))
                ))
            alternate_row_colors()
        except Exception as e:
            logging.error(f"Load QR codes error: {e}")
            messagebox.showerror("Error", "Failed to load QR codes.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    return frame