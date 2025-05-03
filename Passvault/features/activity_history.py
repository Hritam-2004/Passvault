import tkinter as tk
from tkinter import ttk, messagebox
import logging
import mysql.connector
from datetime import datetime
from constants import COLORS, FONTS
from utils import truncate_text, show_loading, hide_loading

def create_activity_history_frame(parent, app):
    frame = tk.Frame(parent, bg=COLORS["background"])
    frame.load = lambda: load_logs()

    content = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2, highlightbackground=COLORS["border"])
    content.pack(pady=60, padx=60, fill="both", expand=True)

    tk.Label(content, text="Activity History", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=20)
    tk.Label(content, text="View your account activity logs", font=FONTS["subheading"], bg=COLORS["card_bg"],
             fg=COLORS["subtext"]).pack(pady=10)

    input_frame = tk.Frame(content, bg=COLORS["card_bg"])
    input_frame.pack(pady=20, padx=20, fill="x")

    tk.Label(input_frame, text="Action Type", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    action_types = ["All", "INSERT", "UPDATE", "DELETE"]
    combo_action_type = ttk.Combobox(input_frame, values=action_types, width=20, state="readonly")
    combo_action_type.set("All")
    combo_action_type.pack(side="left", padx=10)

    tk.Label(input_frame, text="Start Date", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_start_date = ttk.Entry(input_frame, width=20)
    entry_start_date.insert(0, "YYYY-MM-DD")
    entry_start_date.pack(side="left", padx=10)

    tk.Label(input_frame, text="End Date", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_end_date = ttk.Entry(input_frame, width=20)
    entry_end_date.insert(0, "YYYY-MM-DD")
    entry_end_date.pack(side="left", padx=10)

    tk.Button(input_frame, text="Filter Logs", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: load_logs(), relief="flat").pack(side="left", padx=20)

    tk.Button(input_frame, text="Clear Logs", bg=COLORS["danger"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: clear_logs(), relief="flat").pack(side="left", padx=20)

    tree_frame = tk.Frame(content, bg=COLORS["card_bg"], bd=0, highlightthickness=2, highlightbackground=COLORS["border"])
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    columns = ("ID", "Table", "Action", "Record ID", "Change Details", "Timestamp")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
    tree.heading("ID", text="ID")
    tree.heading("Table", text="Table")
    tree.heading("Action", text="Action")
    tree.heading("Record ID", text="Record ID")
    tree.heading("Change Details", text="Change Details")
    tree.heading("Timestamp", text="Timestamp")
    tree.column("ID", width=50)
    tree.column("Table", width=120)
    tree.column("Action", width=80)
    tree.column("Record ID", width=80)
    tree.column("Change Details", width=300)
    tree.column("Timestamp", width=150)

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def load_logs():
        for item in tree.get_children():
            tree.delete(item)
        max_retries = 3
        retry_count = 0
        loading = show_loading(frame)
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()

                query = """
                    SELECT id, table_name, action, record_id, change_details, timestamp
                    FROM audit_logs
                    WHERE user_id = %s
                """
                params = [app.current_user_id]
                conditions = []

                action_type = combo_action_type.get()
                if action_type != "All":
                    conditions.append("action = %s")
                    params.append(action_type)

                start_date = entry_start_date.get().strip()
                end_date = entry_end_date.get().strip()
                try:
                    if start_date and start_date != "YYYY-MM-DD":
                        datetime.strptime(start_date, "%Y-%m-%d")
                        conditions.append("timestamp >= %s")
                        params.append(start_date)
                    if end_date and end_date != "YYYY-MM-DD":
                        datetime.strptime(end_date, "%Y-%m-%d")
                        conditions.append("timestamp <= %s")
                        params.append(end_date)
                except ValueError:
                    messagebox.showerror("Error", "Invalid date format (use YYYY-MM-DD).")
                    return

                if conditions:
                    query += " AND " + " AND ".join(conditions)
                query += " ORDER BY timestamp DESC LIMIT 50"

                cursor.execute(query, params)
                logs = cursor.fetchall()
                for log in logs:
                    tree.insert("", "end", values=(
                        log[0],
                        truncate_text(log[1]),
                        log[2],
                        log[3],
                        truncate_text(str(log[4]), 50),
                        log[5]
                    ))
                db.commit()
                break
            except mysql.connector.Error as e:
                logging.error(f"Load logs error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    messagebox.showerror("Error", f"Failed to load activity logs after retries: {e}")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def clear_logs():
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all activity logs?"):
            max_retries = 3
            retry_count = 0
            loading = show_loading(frame)
            while retry_count < max_retries:
                try:
                    db = app.db_pool.get_connection()
                    cursor = db.cursor()
                    db.start_transaction()
                    cursor.execute("DELETE FROM audit_logs WHERE user_id=%s", (app.current_user_id,))
                    db.commit()
                    load_logs()
                    messagebox.showinfo("Success", "Activity logs cleared successfully!")
                    break
                except mysql.connector.Error as e:
                    logging.error(f"Clear logs error (attempt {retry_count + 1}): {e}")
                    if 'db' in locals():
                        db.rollback()
                    retry_count += 1
                    if retry_count == max_retries:
                        messagebox.showerror("Error", f"Failed to clear logs after retries: {e}")
                finally:
                    hide_loading(loading)
                    if 'cursor' in locals():
                        cursor.close()
                    if 'db' in locals():
                        db.close()

    return frame