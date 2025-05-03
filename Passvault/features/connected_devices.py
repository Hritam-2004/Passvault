import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime
from constants import COLORS, FONTS
from utils import truncate_text, show_loading, hide_loading

def create_connected_devices_frame(parent, app):
    frame = tk.Frame(parent, bg=COLORS["background"])
    frame.load = lambda: load_devices()

    content_frame = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                             highlightbackground=COLORS["border"])
    content_frame.pack(pady=60, padx=60, fill="both", expand=True)

    tk.Label(content_frame, text="Connected Devices", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=30)

    input_frame = tk.Frame(content_frame, bg=COLORS["card_bg"])
    input_frame.pack(fill="x", padx=20, pady=20)

    tk.Label(input_frame, text="Device Name", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_device_name = ttk.Entry(input_frame, width=20)
    entry_device_name.pack(side="left", padx=10)

    tk.Label(input_frame, text="Device Type", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_device_type = ttk.Entry(input_frame, width=20)
    entry_device_type.pack(side="left", padx=10)

    tk.Label(input_frame, text="Status", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_status = ttk.Entry(input_frame, width=20)
    entry_status.pack(side="left", padx=10)

    tk.Button(input_frame, text="Add Device", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: add_device(), relief="flat").pack(side="left", padx=20)
    
    tk.Button(input_frame, text="Delete Device", bg=COLORS["danger"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: delete_record(), relief="flat").pack(side="left", padx=20)

    tree_frame = tk.Frame(content_frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                          highlightbackground=COLORS["border"])
    tree_frame.pack(fill="both", expand=True, padx=20, pady=20)

    tree = ttk.Treeview(tree_frame, columns=("Device Name", "Device Type", "Status", "Last Seen", "Created At", "Updated At"), show="headings",
                        style="Treeview")
    tree.heading("Device Name", text="Device Name")
    tree.heading("Device Type", text="Device Type")
    tree.heading("Status", text="Status")
    tree.heading("Last Seen", text="Last Seen")
    tree.heading("Created At", text="Created At")
    tree.heading("Updated At", text="Updated At")
    tree.column("Device Name", width=150)
    tree.column("Device Type", width=150)
    tree.column("Status", width=150)
    tree.column("Last Seen", width=150)
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
            entry_device_name.delete(0, tk.END)
            entry_device_name.insert(0, item["values"][0])
            entry_device_type.delete(0, tk.END)
            entry_device_type.insert(0, item["values"][1])
            entry_status.delete(0, tk.END)
            entry_status.insert(0, item["values"][2])

    tree.bind("<<TreeviewSelect>>", on_row_select)

    def alternate_row_colors():
        for i, item in enumerate(tree.get_children()):
            if i % 2 == 0:
                tree.item(item, tags=("even",))
            else:
                tree.item(item, tags=("odd",))
        tree.tag_configure("even", background=COLORS["table_bg"])
        tree.tag_configure("odd", background=COLORS["table_alt"])

    def add_device():
        device_name = entry_device_name.get().strip()
        device_type = entry_device_type.get().strip()
        status = entry_status.get().strip() or "Active"

        if not all([device_name, device_type]):
            messagebox.showerror("Error", "Device Name and Device Type are required.")
            return

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO connected_devices (user_id, device_name, device_type, status, last_seen, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (app.current_user_id, device_name, device_type, status, current_time, current_time, current_time)
            )
            db.commit()
            load_devices()
            entry_device_name.delete(0, tk.END)
            entry_device_type.delete(0, tk.END)
            entry_status.delete(0, tk.END)
            messagebox.showinfo("Success", "Device added successfully!")
        except Exception as e:
            logging.error(f"Add device error: {e}")
            messagebox.showerror("Error", "Failed to add device.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    def delete_record():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a device to delete.")
            return

        device_name = tree.item(selected_item)["values"][0]
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete device '{device_name}'?"):
            loading = show_loading(frame)
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                cursor.execute(
                    "DELETE FROM connected_devices WHERE user_id=%s AND device_name=%s",
                    (app.current_user_id, device_name)
                )
                db.commit()
                load_devices()
                entry_device_name.delete(0, tk.END)
                entry_device_type.delete(0, tk.END)
                entry_status.delete(0, tk.END)
                messagebox.showinfo("Success", "Device deleted successfully!")
            except Exception as e:
                logging.error(f"Delete device error: {e}")
                messagebox.showerror("Error", "Failed to delete device.")
            finally:
                hide_loading(loading)
                if 'db' in locals():
                    db.close()

    def load_devices():
        for item in tree.get_children():
            tree.delete(item)
        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            cursor.execute(
                "SELECT device_name, device_type, status, last_seen, created_at, updated_at "
                "FROM connected_devices WHERE user_id=%s",
                (app.current_user_id,)
            )
            for row in cursor.fetchall():
                tree.insert("", "end", values=(
                    truncate_text(row[0]),
                    truncate_text(row[1]),
                    truncate_text(row[2]),
                    truncate_text(str(row[3])),
                    truncate_text(str(row[4])),
                    truncate_text(str(row[5]))
                ))
            alternate_row_colors()
        except Exception as e:
            logging.error(f"Load devices error: {e}")
            messagebox.showerror("Error", "Failed to load devices.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    return frame