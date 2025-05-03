import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from constants import COLORS, FONTS
from utils import truncate_text, show_loading, hide_loading

def create_multidevice_access_frame(parent, app):
    frame = tk.Frame(parent, bg=COLORS["background"])
    frame.load = lambda: load_access_logs()

    content_frame = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                             highlightbackground=COLORS["border"])
    content_frame.pack(pady=60, padx=60, fill="both", expand=True)

    tk.Label(content_frame, text="Multi-Device Access", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=30)

    input_frame = tk.Frame(content_frame, bg=COLORS["card_bg"])
    input_frame.pack(fill="x", padx=20, pady=20)

    tk.Label(input_frame, text="Device", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_device = ttk.Entry(input_frame, width=20)
    entry_device.pack(side="left", padx=10)

    tk.Label(input_frame, text="IP Address", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_ip = ttk.Entry(input_frame, width=20)
    entry_ip.pack(side="left", padx=10)

    tk.Label(input_frame, text="Location", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_location = ttk.Entry(input_frame, width=20)
    entry_location.pack(side="left", padx=10)

    tk.Button(input_frame, text="Add Access", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: add_access_log(), relief="flat").pack(side="left", padx=20)
    
    tk.Button(input_frame, text="Delete Access", bg=COLORS["danger"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: delete_record(), relief="flat").pack(side="left", padx=20)

    tree_frame = tk.Frame(content_frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                          highlightbackground=COLORS["border"])
    tree_frame.pack(fill="both", expand=True, padx=20, pady=20)

    tree = ttk.Treeview(tree_frame, columns=("Device", "IP Address", "Access Time", "Location", "Created At", "Updated At"), show="headings",
                        style="Treeview")
    tree.heading("Device", text="Device")
    tree.heading("IP Address", text="IP Address")
    tree.heading("Access Time", text="Access Time")
    tree.heading("Location", text="Location")
    tree.heading("Created At", text="Created At")
    tree.heading("Updated At", text="Updated At")
    tree.column("Device", width=150)
    tree.column("IP Address", width=150)
    tree.column("Access Time", width=150)
    tree.column("Location", width=150)
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
            entry_device.delete(0, tk.END)
            entry_device.insert(0, item["values"][0])
            entry_ip.delete(0, tk.END)
            entry_ip.insert(0, item["values"][1])
            entry_location.delete(0, tk.END)
            entry_location.insert(0, item["values"][3])

    tree.bind("<<TreeviewSelect>>", on_row_select)

    def alternate_row_colors():
        for i, item in enumerate(tree.get_children()):
            if i % 2 == 0:
                tree.item(item, tags=("even",))
            else:
                tree.item(item, tags=("odd",))
        tree.tag_configure("even", background=COLORS["table_bg"])
        tree.tag_configure("odd", background=COLORS["table_alt"])

    def add_access_log():
        device = entry_device.get().strip()
        ip_address = entry_ip.get().strip()
        location = entry_location.get().strip()

        if not all([device, ip_address]):
            messagebox.showerror("Error", "Device and IP Address are required.")
            return

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO access_logs (user_id, device_name, ip_address, access_time, location, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (app.current_user_id, device, ip_address, current_time, location or None, current_time, current_time)
            )
            db.commit()
            load_access_logs()
            entry_device.delete(0, tk.END)
            entry_ip.delete(0, tk.END)
            entry_location.delete(0, tk.END)
            messagebox.showinfo("Success", "Access log added successfully!")
        except Exception as e:
            logging.error(f"Add access log error: {e}")
            messagebox.showerror("Error", "Failed to add access log.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    def delete_record():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select an access log to delete.")
            return

        device_name = tree.item(selected_item)["values"][0]
        access_time = tree.item(selected_item)["values"][2]
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete access log for '{device_name}'?"):
            loading = show_loading(frame)
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                cursor.execute(
                    "DELETE FROM access_logs WHERE user_id=%s AND device_name=%s AND access_time=%s",
                    (app.current_user_id, device_name, access_time)
                )
                db.commit()
                load_access_logs()
                entry_device.delete(0, tk.END)
                entry_ip.delete(0, tk.END)
                entry_location.delete(0, tk.END)
                messagebox.showinfo("Success", "Access log deleted successfully!")
            except Exception as e:
                logging.error(f"Delete access log error: {e}")
                messagebox.showerror("Error", "Failed to delete access log.")
            finally:
                hide_loading(loading)
                if 'db' in locals():
                    db.close()

    def load_access_logs():
        for item in tree.get_children():
            tree.delete(item)
        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            cursor.execute(
                "SELECT device_name, ip_address, access_time, location, created_at, updated_at "
                "FROM access_logs WHERE user_id=%s",
                (app.current_user_id,)
            )
            for row in cursor.fetchall():
                tree.insert("", "end", values=(
                    truncate_text(row[0]),
                    truncate_text(row[1]),
                    truncate_text(str(row[2])),
                    truncate_text(row[3] or "N/A"),
                    truncate_text(str(row[4])),
                    truncate_text(str(row[5]))
                ))
            alternate_row_colors()
        except Exception as e:
            logging.error(f"Load access logs error: {e}")
            messagebox.showerror("Error", "Failed to load access logs.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    return frame