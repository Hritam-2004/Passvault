import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from datetime import datetime
import os
import mysql.connector
from cryptography.fernet import Fernet
from constants import COLORS, FONTS
from utils import truncate_text, show_loading, hide_loading

def create_file_manager_frame(parent, app):
    frame = tk.Frame(parent, bg=COLORS["background"])
    frame.load = lambda: load_files()

    # Generate encryption key (in production, store per user securely)
    encryption_key = Fernet.generate_key()
    cipher = Fernet(encryption_key)

    content = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2, highlightbackground=COLORS["border"])
    content.pack(pady=60, padx=60, fill="both", expand=True)

    tk.Label(content, text="File Manager", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=20)
    tk.Label(content, text="Securely store and manage files", font=FONTS["subheading"], bg=COLORS["card_bg"],
             fg=COLORS["subtext"]).pack(pady=10)

    input_frame = tk.Frame(content, bg=COLORS["card_bg"])
    input_frame.pack(pady=20, padx=20, fill="x")

    tk.Label(input_frame, text="File", font=FONTS["small"], bg=COLORS["card_bg"]).pack(side="left", padx=10)
    entry_file = ttk.Entry(input_frame, width=30)
    entry_file.pack(side="left", padx=10)

    tk.Button(input_frame, text="Browse", bg=COLORS["secondary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: browse_file(), relief="flat").pack(side="left", padx=10)

    tk.Button(input_frame, text="Upload File", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: upload_file(), relief="flat").pack(side="left", padx=20)

    tk.Button(input_frame, text="Download File", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: download_file(), relief="flat").pack(side="left", padx=20)

    tk.Button(input_frame, text="Delete File", bg=COLORS["danger"], fg=COLORS["dark_fg"],
              font=FONTS["button"], command=lambda: delete_file(), relief="flat").pack(side="left", padx=20)

    tree_frame = tk.Frame(content, bg=COLORS["card_bg"], bd=0, highlightthickness=2, highlightbackground=COLORS["border"])
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

    columns = ("ID", "File Name", "File Size", "Created At", "Updated At")
    tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
    tree.heading("ID", text="ID")
    tree.heading("File Name", text="File Name")
    tree.heading("File Size", text="File Size (Bytes)")
    tree.heading("Created At", text="Created At")
    tree.heading("Updated At", text="Updated At")
    tree.column("ID", width=50)
    tree.column("File Name", width=200)
    tree.column("File Size", width=150)
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
            entry_file.delete(0, tk.END)
            entry_file.insert(0, item["values"][1])  # File Name

    tree.bind("<<TreeviewSelect>>", on_row_select)

    def browse_file():
        file_path = filedialog.askopenfilename()
        if file_path:
            entry_file.delete(0, tk.END)
            entry_file.insert(0, os.path.basename(file_path))

    def upload_file():
        file_name = entry_file.get().strip()
        if not file_name:
            messagebox.showerror("Error", "Please select a file to upload.")
            return

        file_path = filedialog.askopenfilename(initialfile=file_name)
        if not file_path:
            return

        try:
            with open(file_path, "rb") as f:
                file_data = f.read()
            encrypted_data = cipher.encrypt(file_data)
            file_size = len(file_data)
            max_retries = 3
            retry_count = 0
            loading = show_loading(frame)
            while retry_count < max_retries:
                try:
                    db = app.db_pool.get_connection()
                    cursor = db.cursor()
                    db.start_transaction()
                    cursor.execute("CALL AddFile(%s, %s, %s, %s)",
                                   (app.current_user_id, file_name, encrypted_data, file_size))
                    db.commit()
                    load_files()
                    entry_file.delete(0, tk.END)
                    messagebox.showinfo("Success", "File uploaded successfully!")
                    break
                except mysql.connector.Error as e:
                    logging.error(f"Upload file error (attempt {retry_count + 1}): {e}")
                    if 'db' in locals():
                        db.rollback()
                    retry_count += 1
                    if retry_count == max_retries:
                        messagebox.showerror("Error", f"Failed to upload file after retries: {e}")
                finally:
                    hide_loading(loading)
                    if 'cursor' in locals():
                        cursor.close()
                    if 'db' in locals():
                        db.close()
        except Exception as e:
            logging.error(f"File read error: {e}")
            messagebox.showerror("Error", "Failed to read file.")

    def download_file():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a file to download.")
            return

        file_id = tree.item(selected_item)["values"][0]  # ID
        file_name = tree.item(selected_item)["values"][1]  # File Name
        save_path = filedialog.asksaveasfilename(defaultextension=os.path.splitext(file_name)[1], initialfile=file_name)
        if not save_path:
            return

        max_retries = 3
        retry_count = 0
        loading = show_loading(frame)
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("SELECT encrypted_data FROM file_vault WHERE id=%s AND user_id=%s",
                               (file_id, app.current_user_id))
                result = cursor.fetchone()
                if result:
                    encrypted_data = result[0]
                    decrypted_data = cipher.decrypt(encrypted_data)
                    with open(save_path, "wb") as f:
                        f.write(decrypted_data)
                    db.commit()
                    messagebox.showinfo("Success", "File downloaded successfully!")
                    break
                else:
                    db.rollback()
                    messagebox.showerror("Error", "File not found or unauthorized.")
                    break
            except mysql.connector.Error as e:
                logging.error(f"Download file error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    messagebox.showerror("Error", f"Failed to download file after retries: {e}")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def delete_file():
        selected_item = tree.selection()
        if not selected_item:
            messagebox.showerror("Error", "Please select a file to delete.")
            return

        file_id = tree.item(selected_item)["values"][0]  # ID
        file_name = tree.item(selected_item)["values"][1]  # File Name
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete file '{file_name}'?"):
            max_retries = 3
            retry_count = 0
            loading = show_loading(frame)
            while retry_count < max_retries:
                try:
                    db = app.db_pool.get_connection()
                    cursor = db.cursor()
                    db.start_transaction()
                    cursor.execute("CALL DeleteFile(%s, %s)", (file_id, app.current_user_id))
                    db.commit()
                    load_files()
                    entry_file.delete(0, tk.END)
                    messagebox.showinfo("Success", "File deleted successfully!")
                    break
                except mysql.connector.Error as e:
                    logging.error(f"Delete file error (attempt {retry_count + 1}): {e}")
                    if 'db' in locals():
                        db.rollback()
                    retry_count += 1
                    if retry_count == max_retries:
                        messagebox.showerror("Error", f"Failed to delete file after retries: {e}")
                finally:
                    hide_loading(loading)
                    if 'cursor' in locals():
                        cursor.close()
                    if 'db' in locals():
                        db.close()

    def load_files():
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
                cursor.execute("""
                    SELECT id, file_name, file_size, created_at, updated_at
                    FROM file_vault
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                """, (app.current_user_id,))
                files = cursor.fetchall()
                for file in files:
                    tree.insert("", "end", values=(
                        file[0],
                        truncate_text(file[1]),
                        file[2],
                        file[3],
                        file[4]
                    ))
                db.commit()
                break
            except mysql.connector.Error as e:
                logging.error(f"Load files error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    messagebox.showerror("Error", f"Failed to load files after retries: {e}")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    return frame