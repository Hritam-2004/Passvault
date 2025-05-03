import tkinter as tk
from tkinter import ttk, messagebox
import logging
from datetime import datetime, timedelta
from constants import COLORS, FONTS
from utils import truncate_text, show_loading, hide_loading

def create_expiration_alerts_frame(parent, app):
    frame = tk.Frame(parent, bg=COLORS["background"])
    frame.load = lambda: load_alerts()

    content_frame = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                             highlightbackground=COLORS["border"])
    content_frame.pack(pady=60, padx=60, fill="both", expand=True)

    tk.Label(content_frame, text="Expiration Alerts", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=30)

    input_frame = tk.Frame(content_frame, bg=COLORS["card_bg"])
    input_frame.pack(fill="x", padx=20, pady=20)

    tk.Button(input_frame, text="Delete Alert", bg=COLORS["danger"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: delete_record(), relief="flat").pack(side="left", padx=20)

    tree_frame = tk.Frame(content_frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                          highlightbackground=COLORS["border"])
    tree_frame.pack(fill="both", expand=True, padx=20, pady=20)

    tree = ttk.Treeview(tree_frame, columns=("Service", "Expiration Date", "Status", "Password ID", "Created At", "Updated At"), show="headings",
                        style="Treeview")
    tree.heading("Service", text="Service")
    tree.heading("Expiration Date", text="Expiration Date")
    tree.heading("Status", text="Status")
    tree.heading("Password ID", text="Password ID")
    tree.heading("Created At", text="Created At")
    tree.heading("Updated At", text="Updated At")
    tree.column("Service", width=150)
    tree.column("Expiration Date", width=150)
    tree.column("Status", width=150)
    tree.column("Password ID", width=100)
    tree.column("Created At", width=150)
    tree.column("Updated At", width=150)

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def alternate_row_colors():
        for i, item in enumerate(tree.get_children()):
            if i % 2 == 0:
                tree.item(item, tags=("even",))
            else:
                tree.item(item, tags=("odd",))
        tree.tag_configure("even", background=COLORS["table_bg"])
        tree.tag_configure("odd", background=COLORS["table_alt"])

    def delete_record():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select an alert to delete.")
            return

        password_id = tree.item(selected_item)["values"][3]
        service = tree.item(selected_item)["values"][0]
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete the alert for '{service}'?"):
            loading = show_loading(frame)
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                cursor.execute(
                    "DELETE FROM expiration_alerts WHERE user_id=%s AND password_id=%s",
                    (app.current_user_id, password_id)
                )
                db.commit()
                load_alerts()
                messagebox.showinfo("Success", "Alert deleted successfully!")
            except Exception as e:
                logging.error(f"Delete alert error: {e}")
                messagebox.showerror("Error", "Failed to delete alert.")
            finally:
                hide_loading(loading)
                if 'db' in locals():
                    db.close()

    def load_alerts():
        for item in tree.get_children():
            tree.delete(item)
        loading = show_loading(frame)
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()

            # Clear existing alerts
            cursor.execute("DELETE FROM expiration_alerts WHERE user_id=%s", (app.current_user_id,))

            # Check passwords table for expiration status
            cursor.execute(
                "SELECT id, service, expiration_date FROM passwords WHERE user_id=%s AND expiration_date IS NOT NULL",
                (app.current_user_id,)
            )
            current_time = datetime.now()
            threshold = current_time + timedelta(days=7)

            for row in cursor.fetchall():
                password_id, service, exp_date = row
                exp_date = datetime.strptime(str(exp_date), "%Y-%m-%d")
                if exp_date < current_time:
                    status = "Expired"
                elif exp_date <= threshold:
                    status = "Expiring Soon"
                else:
                    continue  # Skip passwords not nearing expiration

                updated_time = current_time.strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO expiration_alerts (user_id, password_id, service, expiration_date, status, created_at, updated_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (app.current_user_id, password_id, service, exp_date, status, updated_time, updated_time)
                )
                # Notification is now handled by DB trigger, so no need to insert here

            db.commit()

            # Load alerts into table
            cursor.execute(
                "SELECT service, expiration_date, status, password_id, created_at, updated_at "
                "FROM expiration_alerts WHERE user_id=%s",
                (app.current_user_id,)
            )
            for row in cursor.fetchall():
                tree.insert("", "end", values=(
                    truncate_text(row[0]),
                    truncate_text(str(row[1])),
                    truncate_text(row[2]),
                    truncate_text(str(row[3])),
                    truncate_text(str(row[4])),
                    truncate_text(str(row[5]))
                ))
            alternate_row_colors()
        except Exception as e:
            logging.error(f"Load alerts error: {e}")
            messagebox.showerror("Error", "Failed to load alerts.")
        finally:
            hide_loading(loading)
            if 'db' in locals():
                db.close()

    return frame