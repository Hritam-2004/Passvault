import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import logging
import mysql.connector
from constants import COLORS, FONTS
from utils import truncate_text, validate_email, validate_phone, show_loading, hide_loading
from features.password_manager import create_password_manager_frame
from features.qr_sharing import create_qr_sharing_frame
from features.multidevice_access import create_multidevice_access_frame
from features.secure_pass_sharing import create_secure_pass_sharing_frame
from features.connected_devices import create_connected_devices_frame
from features.expiration_alerts import create_expiration_alerts_frame
from features.activity_history import create_activity_history_frame
from features.file_manager import create_file_manager_frame

# --- Tooltip Helper ---
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)
    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert") if hasattr(self.widget, "bbox") else (0,0,0,0)
        x = x + self.widget.winfo_rootx() + 30
        y = y + self.widget.winfo_rooty() + 30
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#222", foreground="#fff",
                         relief='solid', borderwidth=1,
                         font=FONTS["small"])
        label.pack(ipadx=8, ipady=4)
    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

# --- Enhanced Theme ---
def apply_theme(app, root):
    style = ttk.Style()
    style.theme_use("clam")
    fg_color = COLORS["dark_fg"] if app.var_dark_mode.get() else COLORS["text"]
    card_bg = COLORS["table_bg"] if app.var_dark_mode.get() else COLORS["card_bg"]
    gradient_start = COLORS["gradient_start"]
    gradient_end = COLORS["gradient_end"]
    border_radius = 12

    # Card/Frame with shadow
    style.configure("Card.TFrame", background=card_bg, relief="flat", borderwidth=0)
    style.configure("Shadow.TFrame", background=gradient_start, relief="flat", borderwidth=0)

    # Labels
    style.configure("TLabel", font=FONTS["body"], background=card_bg, foreground=fg_color)

    # Entries with rounded corners
    style.configure("TEntry", padding=10, font=FONTS["body"], fieldbackground=card_bg, foreground=fg_color,
                    borderwidth=2, relief="groove")

    # Combobox
    style.configure("TCombobox", padding=10, font=FONTS["body"], fieldbackground=card_bg, foreground=fg_color)

    # Buttons with gradient and hover effects
    style.configure("Accent.TButton", font=FONTS["button"], padding=10, background=gradient_start,
                    foreground=COLORS["dark_fg"], borderwidth=0, relief="flat")
    style.map("Accent.TButton",
        background=[("active", gradient_end), ("!active", gradient_start)],
        relief=[("pressed", "sunken"), ("!pressed", "flat")]
    )
    style.configure("TButton", font=FONTS["button"], padding=10, background=COLORS["secondary"],
                    foreground=COLORS["dark_fg"], borderwidth=0, relief="flat")
    style.map("TButton",
        background=[("active", COLORS["secondary_hover"]), ("!active", COLORS["secondary"])],
        relief=[("pressed", "sunken"), ("!pressed", "flat")]
    )

    # Scrollbar
    style.configure("Vertical.TScrollbar", troughcolor=COLORS["border"],
                    background=COLORS["primary"], activebackground=COLORS["primary_hover"], width=10)

    # Treeview
    style.configure("Treeview", font=FONTS["table"], rowheight=38, background=COLORS["table_bg"],
                    fieldbackground=COLORS["table_bg"], foreground=fg_color, borderwidth=0)
    style.configure("Treeview.Heading", font=FONTS["body_bold"], background=gradient_start,
                    foreground=COLORS["dark_fg"])
    style.map("Treeview", background=[("selected", gradient_end)], foreground=[("selected", COLORS["dark_fg"])])
def update_theme(app, root):
    bg_color = COLORS["dark_bg"] if app.var_dark_mode.get() else COLORS["background"]
    fg_color = COLORS["dark_fg"] if app.var_dark_mode.get() else COLORS["text"]
    card_bg = COLORS["table_bg"] if app.var_dark_mode.get() else COLORS["card_bg"]
    root.configure(bg=bg_color)
    apply_theme(app, root)
    def update_widget_styles(widget):
        if isinstance(widget, tk.Frame):
            widget.configure(bg=card_bg if "card" in str(widget).lower() else bg_color)
        elif isinstance(widget, tk.Label):
            widget.configure(bg=card_bg if "card" in str(widget).lower() else bg_color, fg=fg_color, font=FONTS["body"])
        elif isinstance(widget, tk.Checkbutton):
            widget.configure(bg=card_bg if "card" in str(widget).lower() else bg_color, fg=fg_color, selectcolor=bg_color, font=FONTS["body"])
        elif isinstance(widget, tk.Button):
            widget.configure(bg=COLORS["primary"], fg=COLORS["dark_fg"], relief="flat", font=FONTS["button"], bd=0, highlightthickness=0)
        elif isinstance(widget, (ttk.Entry, ttk.Combobox)):
            pass  # Handled by apply_theme
        elif isinstance(widget, tk.Canvas):
            widget.configure(bg=card_bg)
        if isinstance(widget, (ttk.Button, ttk.Label, ttk.Treeview, ttk.Scrollbar)):
            pass  # Handled by ttk.Style
        for child in widget.winfo_children():
            update_widget_styles(child)
    frames = [getattr(app, attr, None) for attr in ['container', 'login_frame', 'signup_frame', 'dashboard_frame']]
    frames = [f for f in frames if f is not None]
    for frame in frames:
        update_widget_styles(frame)
    for frame in app.frames.values():
        update_widget_styles(frame)

def create_login_frame(container, app):
    frame = tk.Frame(container, bg=COLORS["background"], width=1440, height=900)

    # Add shadow effect
    shadow = tk.Frame(frame, bg=COLORS["shadow"], width=560, height=560)
    shadow.place(relx=0.5, rely=0.5, anchor="center")

    card = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightbackground=COLORS["primary"], highlightthickness=2)
    card.place(relx=0.5, rely=0.5, anchor="center", width=550, height=550)
    card.configure(relief="flat", highlightcolor=COLORS["gradient_end"])
    card.grid_propagate(False)

    ttk.Label(card, text="PassVault", font=FONTS["heading"], foreground=COLORS["gradient_start"]).pack(pady=(30, 20))
    ttk.Label(card, text="Sign in to your account", font=FONTS["subheading"], foreground=COLORS["subtext"]).pack(pady=(0, 20))

    app.login_entry_user = ttk.Entry(card, width=35)
    app.login_entry_user.pack(pady=12, padx=30, ipady=6)
    app.login_entry_user.insert(0, "Username")
    app.login_entry_user.bind("<FocusIn>", lambda e: app.login_entry_user.delete(0, tk.END) if app.login_entry_user.get() == "Username" else None)
    app.login_entry_user.configure(justify='center')

    app.login_entry_pass = ttk.Entry(card, show="*", width=35)
    app.login_entry_pass.pack(pady=12, padx=30, ipady=6)
    app.login_entry_pass.insert(0, "Password")
    app.login_entry_pass.bind("<FocusIn>", lambda e: app.login_entry_pass.delete(0, tk.END) if app.login_entry_pass.get() == "Password" else None)
    app.login_entry_pass.configure(justify='center')

    login_btn = ttk.Button(card, text="Sign In", style="Accent.TButton", command=app.login)
    login_btn.pack(pady=25)
    ToolTip(login_btn, "Sign in to your PassVault account")

    create_btn = ttk.Button(card, text="Create an account", style="TButton", command=app.switch_to_signup)
    create_btn.pack(pady=12)
    ToolTip(create_btn, "Register a new PassVault account")

    return frame

def create_signup_frame(container, app):
    frame = tk.Frame(container, bg=COLORS["background"], width=1440, height=900)
    card = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightbackground=COLORS["primary"], highlightthickness=2)
    card.place(relx=0.5, rely=0.5, anchor="center", width=550, height=600)
    card.configure(relief="flat", highlightcolor=COLORS["gradient_end"])
    card.config(borderwidth=0, highlightbackground=COLORS["primary"], highlightthickness=2)
    card.grid_propagate(False)
    # Add shadow effect (simulate with border)
    card.config(highlightbackground=COLORS["primary"], highlightcolor=COLORS["primary"], highlightthickness=3)

    ttk.Label(card, text="PassVault", font=FONTS["heading"]).pack(pady=(30, 20))
    ttk.Label(card, text="Create a new account", font=FONTS["subheading"], foreground=COLORS["subtext"]).pack(pady=(0, 20))

    app.signup_entry_user = ttk.Entry(card, width=35)
    app.signup_entry_user.pack(pady=12, padx=30, ipady=6)
    app.signup_entry_user.insert(0, "Username")
    app.signup_entry_user.bind("<FocusIn>", lambda e: app.signup_entry_user.delete(0, tk.END) if app.signup_entry_user.get() == "Username" else None)
    app.signup_entry_user.configure(justify='center')

    app.signup_entry_email = ttk.Entry(card, width=35)
    app.signup_entry_email.pack(pady=12, padx=30, ipady=6)
    app.signup_entry_email.insert(0, "Email")
    app.signup_entry_email.bind("<FocusIn>", lambda e: app.signup_entry_email.delete(0, tk.END) if app.signup_entry_email.get() == "Email" else None)
    app.signup_entry_email.configure(justify='center')

    app.signup_entry_pass = ttk.Entry(card, show="*", width=35)
    app.signup_entry_pass.pack(pady=12, padx=30, ipady=6)
    app.signup_entry_pass.insert(0, "Password")
    app.signup_entry_pass.bind("<FocusIn>", lambda e: app.signup_entry_pass.delete(0, tk.END) if app.signup_entry_pass.get() == "Password" else None)
    app.signup_entry_pass.configure(justify='center')

    signup_btn = ttk.Button(card, text="Sign Up", style="Accent.TButton", command=app.signup)
    signup_btn.pack(pady=25)
    ToolTip(signup_btn, "Create your PassVault account")

    already_btn = tk.Button(card, text="Already have an account?", bg=COLORS["card_bg"], fg=COLORS["primary"],
              bd=0, font=FONTS["small"], command=app.switch_to_login, relief="flat", highlightthickness=0)
    already_btn.pack(pady=12)
    ToolTip(already_btn, "Go back to login")

    return frame

def create_audit_logs_frame(parent, app):
    frame = tk.Frame(parent, bg=COLORS["background"])
    
    content = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2, highlightbackground=COLORS["border"])
    content.pack(pady=60, padx=60, fill="both", expand=True)
    
    tk.Label(content, text="Audit Logs", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=20)
    tk.Label(content, text="View your account activity", font=FONTS["subheading"], bg=COLORS["card_bg"],
             fg=COLORS["subtext"]).pack(pady=10)

    # Treeview for audit logs
    columns = ("ID", "Table", "Action", "Record ID", "Change Details", "Timestamp")
    tree = ttk.Treeview(content, columns=columns, show="headings", height=15)
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
    
    scrollbar = ttk.Scrollbar(content, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    scrollbar.pack(side="right", fill="y")
    
    def load_audit_logs():
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
                    SELECT id, table_name, action, record_id, change_details, timestamp
                    FROM audit_logs
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                    LIMIT 50
                """, (app.current_user_id,))
                logs = cursor.fetchall()
                for log in logs:
                    tree.insert("", "end", values=(
                        log[0],
                        log[1],
                        log[2],
                        log[3],
                        truncate_text(str(log[4]), 50),
                        log[5]
                    ))
                db.commit()
                break
            except mysql.connector.Error as e:
                logging.error(f"Load audit logs error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    messagebox.showerror("Error", f"Failed to load audit logs after retries: {e}")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()
    
    tk.Button(content, text="Refresh Logs", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, command=load_audit_logs, relief="flat").pack(pady=10)
    
    def load():
        load_audit_logs()
    
    frame.load = load
    return frame

def create_backups_frame(parent, app):
    frame = tk.Frame(parent, bg=COLORS["background"])
    
    content = tk.Frame(frame, bg=COLORS["card_bg"], bd=0, highlightthickness=2, highlightbackground=COLORS["border"])
    content.pack(pady=60, padx=60, fill="both", expand=True)
    
    tk.Label(content, text="Backup Management", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=20)
    tk.Label(content, text="View, create, and restore backups", font=FONTS["subheading"], bg=COLORS["card_bg"],
             fg=COLORS["subtext"]).pack(pady=10)

    # Treeview for backups
    columns = ("ID", "Table", "Record ID", "Backup Time")
    tree = ttk.Treeview(content, columns=columns, show="headings", height=15)
    tree.heading("ID", text="ID")
    tree.heading("Table", text="Table")
    tree.heading("Record ID", text="Record ID")
    tree.heading("Backup Time", text="Backup Time")
    tree.column("ID", width=50)
    tree.column("Table", width=120)
    tree.column("Record ID", width=80)
    tree.column("Backup Time", width=150)
    
    scrollbar = ttk.Scrollbar(content, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
    scrollbar.pack(side="right", fill="y")
    
    # Store Treeview in app for load_backups
    app.backups_tree = tree
    
    # Ensure selection on click
    tree.bind("<Button-1>", lambda event: tree.selection_set(tree.identify_row(event.y)))
    
    def restore_selected_backup():
        selected_item = tree.selection()
        if not selected_item or len(selected_item) != 1:
            messagebox.showerror("Error", "Please select exactly one backup to restore.")
            return
        selected_values = tree.item(selected_item[0])["values"]
        if not selected_values or len(selected_values) < 1:
            messagebox.showerror("Error", "Invalid backup selection.")
            return
        backup_id = selected_values[0]
        logging.debug(f"Selected backup: {selected_values}")
        max_retries = 3
        retry_count = 0
        loading = show_loading(frame)
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("CALL RestoreUserData(%s)", (backup_id,))
                db.commit()
                messagebox.showinfo("Success", "Backup restored successfully!")
                app.load_backups()  # Refresh the list
                break
            except mysql.connector.Error as e:
                logging.error(f"Restore backup error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    messagebox.showerror("Error", f"Failed to restore backup after retries: {e}")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()
    
    button_frame = tk.Frame(content, bg=COLORS["card_bg"])
    button_frame.pack(pady=10, fill="x")
    
    tk.Button(button_frame, text="Refresh Backups", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, command=app.load_backups, relief="flat").pack(side="left", padx=10)
    
    tk.Button(button_frame, text="Create Backup", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, command=app.create_backup, relief="flat").pack(side="left", padx=10)
    
    tk.Button(button_frame, text="Restore Selected", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, command=restore_selected_backup, relief="flat").pack(side="left", padx=10)
    
    def load():
        app.load_backups()
    
    frame.load = load
    return frame

def create_dashboard_frame(container, app):
    # --- Variables ---
    app.var_dark_mode = tk.BooleanVar(value=False)
    app.var_notifications = tk.BooleanVar(value=True)
    app.var_password_length = tk.StringVar(value="16")
    app.var_auto_lock_timeout = tk.StringVar(value="10")
    app.var_require_uppercase = tk.BooleanVar(value=True)
    app.var_require_numbers = tk.BooleanVar(value=True)
    app.var_require_special_chars = tk.BooleanVar(value=True)
    app.var_default_sharing_method = tk.StringVar(value="qr_code")
    app.var_password_check_interval = tk.StringVar(value="30")
    app.active_canvas = None
    app.frames = {}

    dashboard_frame = tk.Frame(container, bg=COLORS["background"])
    apply_theme(app, root=app.root)

    # --- Sidebar ---
    sidebar = tk.Frame(dashboard_frame, width=220, bg=COLORS["dark_bg"])
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    # Sidebar: User Info (Avatar + Username)
    user_info_frame = tk.Frame(sidebar, bg=COLORS["dark_bg"])
    user_info_frame.pack(pady=(30, 10), padx=10, fill="x")
    try:
        avatar_img = Image.open("avatar.png")
        avatar_img = avatar_img.resize((56, 56), Image.Resampling.LANCZOS)
        avatar_photo = ImageTk.PhotoImage(avatar_img)
        app.image_references = getattr(app, 'image_references', []) + [avatar_photo]
        avatar_label = tk.Label(user_info_frame, image=avatar_photo, bg=COLORS["dark_bg"], bd=0)
        avatar_label.pack(side="left", padx=(0, 10))
    except Exception:
        avatar_label = tk.Label(user_info_frame, text="👤", font=FONTS["heading"], bg=COLORS["dark_bg"])
        avatar_label.pack(side="left", padx=(0, 10))
    app.sidebar_username_label = tk.Label(user_info_frame, text="User", font=FONTS["body_bold"], fg=COLORS["primary"], bg=COLORS["dark_bg"])
    app.sidebar_username_label.pack(side="left", anchor="w")

    # Sidebar: Section - Main
    section_label = tk.Label(sidebar, text="MAIN", font=FONTS["small"], fg=COLORS["subtext"], bg=COLORS["dark_bg"])
    section_label.pack(pady=(20, 0), padx=20, anchor="w")

    def create_sidebar_button(text, command, is_logout=False, tooltip=None):
        bg_color = COLORS["logout"] if is_logout else COLORS["secondary"]
        active_bg = COLORS["logout_hover"] if is_logout else COLORS["secondary_hover"]
        btn_frame = tk.Frame(sidebar, bg=COLORS["dark_bg"])
        if is_logout:
            btn_frame.pack(side="bottom", pady=35, padx=10, fill="x")
        else:
            btn_frame.pack(pady=7, padx=10, fill="x")
        btn = tk.Button(btn_frame, text=f"  {text}", bg=bg_color, fg=COLORS["dark_fg"],
                        font=FONTS["button"], width=18, height=1, bd=0, anchor="w",
                        activebackground=active_bg, command=command, relief="flat")
        btn.pack(side="left", fill="x")
        btn.bind("<Enter>", lambda e: btn.configure(bg=active_bg))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg_color))
        btn.configure(cursor="hand2")
        if tooltip:
            ToolTip(btn, tooltip)
        return btn

    create_sidebar_button("Home", lambda: show_frame("home"), tooltip="Dashboard Overview")
    create_sidebar_button("Profile", lambda: show_frame("profile"), tooltip="View/Edit Profile")
    create_sidebar_button("Settings", lambda: show_frame("settings"), tooltip="App Settings")
    # Remove FEATURES and SECURITY section labels and buttons
    # Sidebar: Logout
    create_sidebar_button("Logout", app.switch_to_login, is_logout=True, tooltip="Sign Out")

    # --- Navbar ---
    navbar = tk.Frame(dashboard_frame, bg=COLORS["gradient_start"], height=70)
    navbar.pack(side="top", fill="x")
    navbar.pack_propagate(False)

    # Navbar: App Logo/Name
    try:
        logo_img = Image.open("logo.png")
        logo_img = logo_img.resize((48, 48), Image.Resampling.LANCZOS)
        logo_photo = ImageTk.PhotoImage(logo_img)
        app.image_references = getattr(app, 'image_references', []) + [logo_photo]
        logo_label = tk.Label(navbar, image=logo_photo, bg=COLORS["gradient_start"], bd=0)
        logo_label.pack(side="left", padx=18, pady=10)
    except Exception:
        logo_label = tk.Label(navbar, text="PassVault", font=FONTS["heading"], fg=COLORS["primary"], bg=COLORS["gradient_start"])
        logo_label.pack(side="left", padx=18, pady=10)

    # Navbar: Navigation Buttons
    def create_nav_button(text, command, tooltip=None):
        btn = tk.Button(navbar, text=text, bg=COLORS["gradient_start"], fg=COLORS["dark_fg"],
                        font=FONTS["button"], width=12, height=1, bd=0,
                        activebackground=COLORS["gradient_end"], command=command, relief="flat")
        btn.pack(side="left", padx=8, pady=12)
        btn.bind("<Enter>", lambda e: btn.configure(bg=COLORS["gradient_end"]))
        btn.bind("<Leave>", lambda e: btn.configure(bg=COLORS["gradient_start"]))
        btn.configure(cursor="hand2")
        if tooltip:
            ToolTip(btn, tooltip)
        return btn

    create_nav_button("Home", lambda: show_frame("home"), tooltip="Dashboard")
    create_nav_button("About Us", lambda: show_frame("about_us"), tooltip="About PassVault")
    create_nav_button("Features", lambda: show_frame("features"), tooltip="Features Overview")

    # Navbar: Spacer
    tk.Label(navbar, bg=COLORS["gradient_start"]).pack(side="left", expand=True)

    # --- Navbar: Notification Icon ---
    notif_icon = tk.Label(navbar, text="🔔", font=FONTS["heading"], bg=COLORS["gradient_start"])
    notif_icon.pack(side="right", padx=12)
    ToolTip(notif_icon, "Notifications")

    def show_notifications():
        if not hasattr(app, "current_user_id") or not app.current_user_id:
            messagebox.showinfo("Notifications", "No user logged in.")
            return

        def load_and_display_notifications(dialog_frame):
            # Clear previous notifications
            for widget in dialog_frame.winfo_children():
                widget.destroy()
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                cursor.execute("""
                    SELECT id, title, message, is_read, created_at
                    FROM notifications
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT 20
                """, (app.current_user_id,))
                notifications = cursor.fetchall()
            except Exception as e:
                tk.Label(dialog_frame, text=f"Failed to load notifications: {e}", font=FONTS["body"], bg=COLORS["card_bg"]).pack(pady=20)
                return
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()
            if not notifications:
                tk.Label(dialog_frame, text="No notifications.", font=FONTS["body"], bg=COLORS["card_bg"]).pack(pady=20)
            else:
                for notif in notifications:
                    notif_frame = tk.Frame(dialog_frame, bg=COLORS["card_bg"], bd=1, relief="solid", highlightbackground=COLORS["border"])
                    notif_frame.pack(fill="x", pady=5, padx=2)
                    title = notif[1]
                    message = notif[2]
                    is_read = notif[3]
                    created_at = notif[4]
                    title_label = tk.Label(notif_frame, text=title, font=FONTS["body_bold"], bg=COLORS["card_bg"])
                    title_label.pack(anchor="w", padx=5, pady=(2,0))
                    msg_label = tk.Label(notif_frame, text=message, font=FONTS["body"], bg=COLORS["card_bg"], wraplength=350, justify="left")
                    msg_label.pack(anchor="w", padx=5)
                    meta = f"{'Read' if is_read else 'Unread'} | {created_at}"
                    meta_label = tk.Label(notif_frame, text=meta, font=FONTS["small"], fg=COLORS["subtext"], bg=COLORS["card_bg"])
                    meta_label.pack(anchor="w", padx=5, pady=(0,2))

        dialog = tk.Toplevel(app.root)
        dialog.title("Notifications")
        dialog.geometry("420x400")
        dialog.transient(app.root)
        dialog.grab_set()
        frame = tk.Frame(dialog, bg=COLORS["card_bg"])
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        load_and_display_notifications(frame)
        tk.Button(dialog, text="Refresh", command=lambda: load_and_display_notifications(frame), bg=COLORS["primary"], fg=COLORS["dark_fg"], font=FONTS["button"]).pack(pady=5)
        tk.Button(dialog, text="Close", command=dialog.destroy, bg=COLORS["primary"], fg=COLORS["dark_fg"], font=FONTS["button"]).pack(pady=5)

    notif_icon.bind("<Button-1>", lambda e: show_notifications())

    # --- Main Content ---
    main_content = tk.Frame(dashboard_frame, bg=COLORS["background"])
    main_content.pack(side="right", fill="both", expand=True)

    app.frames["home"] = tk.Frame(main_content, bg=COLORS["background"])
    app.frames["about_us"] = tk.Frame(main_content, bg=COLORS["background"])
    app.frames["features"] = tk.Frame(main_content, bg=COLORS["background"])
    app.frames["profile"] = tk.Frame(main_content, bg=COLORS["background"])
    app.frames["settings"] = tk.Frame(main_content, bg=COLORS["background"])
    app.frames["multidevice_access"] = create_multidevice_access_frame(main_content, app)
    app.frames["secure_pass_sharing"] = create_secure_pass_sharing_frame(main_content, app)
    app.frames["qr_sharing"] = create_qr_sharing_frame(main_content, app)
    app.frames["connected_devices"] = create_connected_devices_frame(main_content, app)
    app.frames["password_manager"] = create_password_manager_frame(main_content, app)
    app.frames["expiration_alerts"] = create_expiration_alerts_frame(main_content, app)
    app.frames["audit_logs"] = create_audit_logs_frame(main_content, app)
    app.frames["backups"] = create_backups_frame(main_content, app)
    app.frames["activity_history"] = create_activity_history_frame(main_content, app)
    app.frames["file_manager"] = create_file_manager_frame(main_content, app)

    # --- Home Frame (Dashboard) ---
    home_frame = app.frames["home"]
    home_canvas = tk.Canvas(home_frame, bg=COLORS["background"], highlightthickness=0)
    home_scrollbar = ttk.Scrollbar(home_frame, orient="vertical", command=home_canvas.yview)
    home_content = tk.Frame(home_canvas, bg=COLORS["background"], bd=0)
    home_content.bind("<Configure>", lambda e: home_canvas.configure(scrollregion=home_canvas.bbox("all")))
    home_canvas.create_window((0, 0), window=home_content, anchor="nw")
    home_canvas.configure(yscrollcommand=home_scrollbar.set)
    home_canvas.pack(side="left", fill="both", expand=True, padx=0, pady=0)
    home_scrollbar.pack(side="right", fill="y")

    def on_home_mouse_wheel(event):
        if home_canvas == app.active_canvas:
            delta = -1 if event.delta > 0 else 1
            home_canvas.yview_scroll(delta, "units")
        return "break"
    home_canvas.bind("<MouseWheel>", on_home_mouse_wheel)
    home_canvas.bind("<Button-4>", on_home_mouse_wheel)
    home_canvas.bind("<Button-5>", on_home_mouse_wheel)

    # Dashboard Title
    tk.Label(home_content, text="Dashboard", font=FONTS["heading"], bg=COLORS["background"], anchor="w").pack(pady=(28, 8), padx=32, anchor="w")

    # --- Dashboard Cards Row 1: Stats + Recent Activity ---
    cards_row1 = tk.Frame(home_content, bg=COLORS["background"])
    cards_row1.pack(pady=8, padx=32, fill="x")

    # Stats Card
    stats_card = tk.Frame(cards_row1, bg=COLORS["card_bg"], bd=0, highlightthickness=2, highlightbackground=COLORS["border"])
    stats_card.pack(side="left", padx=(0, 16), fill="y", ipadx=10, ipady=10)
    tk.Label(stats_card, text="Account Stats", font=FONTS["body_bold"], bg=COLORS["card_bg"]).pack(pady=(16, 8))
    app.home_stats_passwords = tk.Label(stats_card, text="Passwords: 0", font=FONTS["body"], bg=COLORS["card_bg"])
    app.home_stats_passwords.pack(pady=4)
    app.home_stats_files = tk.Label(stats_card, text="Files: 0", font=FONTS["body"], bg=COLORS["card_bg"])
    app.home_stats_files.pack(pady=4)
    app.home_stats_last_login = tk.Label(stats_card, text="Last Login: N/A", font=FONTS["body"], bg=COLORS["card_bg"])
    app.home_stats_last_login.pack(pady=4)

    # Separator
    sep1 = tk.Frame(cards_row1, width=18, bg=COLORS["background"])
    sep1.pack(side="left")

    # Recent Activity Card
    activity_card = tk.Frame(cards_row1, bg=COLORS["card_bg"], bd=0, highlightthickness=2, highlightbackground=COLORS["border"])
    activity_card.pack(side="left", fill="y", ipadx=10, ipady=10)
    tk.Label(activity_card, text="Recent Activity", font=FONTS["body_bold"], bg=COLORS["card_bg"]).pack(pady=(16, 8))
    activity_tree = ttk.Treeview(activity_card, columns=("Action", "Timestamp"), show="headings", height=5)
    activity_tree.heading("Action", text="Action")
    activity_tree.heading("Timestamp", text="Timestamp")
    activity_tree.column("Action", width=200)
    activity_tree.column("Timestamp", width=150)
    activity_tree.pack(pady=4, padx=10)
    app.home_activity_tree = activity_tree

    # --- Dashboard Cards Row 2: Security Score + Backup Status ---
    cards_row2 = tk.Frame(home_content, bg=COLORS["background"])
    cards_row2.pack(pady=8, padx=32, fill="x")

    # Security Score Card
    score_card = tk.Frame(cards_row2, bg=COLORS["card_bg"], bd=0, highlightthickness=2, highlightbackground=COLORS["border"])
    score_card.pack(side="left", padx=(0, 16), fill="y", ipadx=10, ipady=10)
    tk.Label(score_card, text="Security Score", font=FONTS["body_bold"], bg=COLORS["card_bg"]).pack(pady=(16, 8))
    app.home_score_canvas = tk.Canvas(score_card, width=100, height=100, bg=COLORS["card_bg"], highlightthickness=0)
    app.home_score_canvas.pack(pady=5)
    app.home_score_label = tk.Label(score_card, text="0%", font=FONTS["body"], bg=COLORS["card_bg"])
    app.home_score_label.pack(pady=5)
    tk.Button(score_card, text="View Details", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, relief="flat",
              command=lambda: show_frame("audit_logs")).pack(pady=5)
    ToolTip(app.home_score_canvas, "Your overall security score")

    # Separator
    sep2 = tk.Frame(cards_row2, width=18, bg=COLORS["background"])
    sep2.pack(side="left")

    # Backup Status Card
    backup_card = tk.Frame(cards_row2, bg=COLORS["card_bg"], bd=0, highlightthickness=2, highlightbackground=COLORS["border"])
    backup_card.pack(side="left", fill="y", ipadx=10, ipady=10)
    tk.Label(backup_card, text="Backup Status", font=FONTS["body_bold"], bg=COLORS["card_bg"]).pack(pady=(16, 8))
    app.home_backup_label = tk.Label(backup_card, text="Last: N/A", font=FONTS["body"], bg=COLORS["card_bg"])
    app.home_backup_label.pack(pady=5)
    tk.Button(backup_card, text="Create Backup", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, relief="flat",
              command=app.create_backup).pack(pady=5)
    ToolTip(app.home_backup_label, "Last backup time")

    # --- Quick Actions ---
    actions_section = tk.Frame(home_content, bg=COLORS["background"])
    actions_section.pack(pady=(18, 8), padx=32, fill="x")
    tk.Label(actions_section, text="Quick Actions", font=FONTS["body_bold"], bg=COLORS["background"]).pack(anchor="w", pady=(0, 8))
    actions_buttons = tk.Frame(actions_section, bg=COLORS["background"])
    actions_buttons.pack(pady=5)
    tk.Button(actions_buttons, text="Password Manager", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, relief="flat",
              command=lambda: show_frame("password_manager")).pack(side="left", padx=5)
    tk.Button(actions_buttons, text="File Manager", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, relief="flat",
              command=lambda: show_frame("file_manager")).pack(side="left", padx=5)
    tk.Button(actions_buttons, text="Generate Password", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, relief="flat",
              command=lambda: app.generate_password_dialog()).pack(side="left", padx=5)
    tk.Button(actions_buttons, text="Upload File", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, relief="flat",
              command=lambda: app.upload_file_dialog()).pack(side="left", padx=5)

    # --- Welcome Message ---
    welcome_section = tk.Frame(home_content, bg=COLORS["background"])
    welcome_section.pack(pady=(8, 0), padx=32, fill="x")
    app.home_welcome_label = tk.Label(welcome_section, text="Welcome!", font=FONTS["subheading"],
                                      bg=COLORS["background"], fg=COLORS["subtext"], anchor="w")
    app.home_welcome_label.pack(pady=10, anchor="w")

    # --- About Us frame with scrollable content ---
    about_frame = app.frames["about_us"]
    about_canvas = tk.Canvas(about_frame, bg=COLORS["card_bg"], highlightthickness=0)
    about_scrollbar = ttk.Scrollbar(about_frame, orient="vertical", command=about_canvas.yview)
    about_content = tk.Frame(about_canvas, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                             highlightbackground=COLORS["border"])
    about_content.bind("<Configure>", lambda e: about_canvas.configure(scrollregion=about_canvas.bbox("all")))
    about_canvas.create_window((0, 0), window=about_content, anchor="nw")
    about_canvas.configure(yscrollcommand=about_scrollbar.set)

    def on_about_mouse_wheel(event):
        if about_canvas == app.active_canvas:
            delta = -1 if event.delta > 0 else 1
            about_canvas.yview_scroll(delta, "units")
        return "break"

    about_canvas.bind("<MouseWheel>", on_about_mouse_wheel)
    about_canvas.bind("<Button-4>", on_about_mouse_wheel)
    about_canvas.bind("<Button-5>", on_about_mouse_wheel)
    about_canvas.pack(side="left", fill="both", expand=True, padx=20, pady=20)
    about_scrollbar.pack(side="right", fill="y")

    # Title and subtitle
    tk.Label(about_content, text="About PassVault", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=20)
    tk.Label(about_content, text="Your Trusted Security Partner", font=FONTS["subheading"], bg=COLORS["card_bg"],
             fg=COLORS["subtext"]).pack(pady=10)

    # Mission and Vision
    mission_frame = tk.Frame(about_content, bg=COLORS["card_bg"])
    mission_frame.pack(pady=20, padx=20, fill="x")
    tk.Label(mission_frame, text="Our Mission", font=FONTS["body_bold"], bg=COLORS["card_bg"]).pack(anchor="w")
    tk.Label(mission_frame, text="To empower users with secure, accessible, and user-friendly password management solutions.",
             font=FONTS["body"], bg=COLORS["card_bg"], wraplength=650, justify="left").pack(anchor="w", pady=5)
    tk.Label(mission_frame, text="Our Vision", font=FONTS["body_bold"], bg=COLORS["card_bg"]).pack(anchor="w", pady=10)
    tk.Label(mission_frame, text="Building a future where digital security is seamless and trustworthy.",
             font=FONTS["body"], bg=COLORS["card_bg"], wraplength=650, justify="left").pack(anchor="w", pady=5)

    # Team Section
    team_frame = tk.Frame(about_content, bg=COLORS["card_bg"])
    team_frame.pack(pady=20, padx=20, fill="x")
    tk.Label(team_frame, text="Meet the Team", font=FONTS["body_bold"], bg=COLORS["card_bg"]).pack(anchor="w")
    
    # Team Member 1 (Placeholder for Vineet Sahoo)
    member1_frame = tk.Frame(team_frame, bg=COLORS["card_bg"], bd=2, highlightthickness=2,
                             highlightbackground=COLORS["border"])
    member1_frame.pack(pady=10, padx=10, fill="x")
    tk.Label(member1_frame, text="Ansh Chopra", font=FONTS["body"], bg=COLORS["card_bg"]).pack(anchor="w", padx=10, pady=5)
    tk.Label(member1_frame, text="Lead Developer - Backend logic and database integration",
             font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["subtext"]).pack(anchor="w", padx=10, pady=5)

    # Team Member 2 (Placeholder for Saumye Singh)
    member2_frame = tk.Frame(team_frame, bg=COLORS["card_bg"], bd=2, highlightthickness=2,
                             highlightbackground=COLORS["border"])
    member2_frame.pack(pady=10, padx=10, fill="x")
    tk.Label(member2_frame, text="Hritam Roy", font=FONTS["body"], bg=COLORS["card_bg"]).pack(anchor="w", padx=10, pady=5)
    tk.Label(member2_frame, text="UI/UX Designer - Intuitive and secure user interface",
             font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["subtext"]).pack(anchor="w", padx=10, pady=5)

    # Team Member 3 (Placeholder for Saumye Singh)
    member3_frame = tk.Frame(team_frame, bg=COLORS["card_bg"], bd=2, highlightthickness=2,
                             highlightbackground=COLORS["border"])
    member3_frame.pack(pady=10, padx=10, fill="x")
    tk.Label(member3_frame, text="Vidant Chandak", font=FONTS["body"], bg=COLORS["card_bg"]).pack(anchor="w", padx=10, pady=5)
    tk.Label(member3_frame, text="R & D - Intuitive and secure user interface",
             font=FONTS["small"], bg=COLORS["card_bg"], fg=COLORS["subtext"]).pack(anchor="w", padx=10, pady=5)
    # Why PassVault
    why_frame = tk.Frame(about_content, bg=COLORS["card_bg"])
    why_frame.pack(pady=20, padx=20, fill="x")
    tk.Label(why_frame, text="Why Choose PassVault?", font=FONTS["body_bold"], bg=COLORS["card_bg"]).pack(anchor="w")
    tk.Label(why_frame, text="• AES-256 encryption for top-tier security",
             font=FONTS["body"], bg=COLORS["card_bg"], justify="left").pack(anchor="w", pady=5)
    tk.Label(why_frame, text="• Seamless multi-device synchronization",
             font=FONTS["body"], bg=COLORS["card_bg"], justify="left").pack(anchor="w", pady=5)
    tk.Label(why_frame, text="• User-friendly QR code sharing",
             font=FONTS["body"], bg=COLORS["card_bg"], justify="left").pack(anchor="w", pady=5)

    # Contact Section
    contact_frame = tk.Frame(about_content, bg=COLORS["card_bg"])
    contact_frame.pack(pady=20, padx=20, fill="x")
    tk.Button(contact_frame, text="Contact Us", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, relief="flat",
              command=lambda: messagebox.showinfo("Contact", "Reach us at support@passvault.com")).pack(side="left", padx=10)
    tk.Button(contact_frame, text="Learn More", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=15, relief="flat",
              command=lambda: messagebox.showinfo("Learn More", "Visit our website (coming soon)!")).pack(side="left", padx=10)

    # --- Features frame with side-by-side layout ---
    features_content = tk.Frame(app.frames["features"], bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                                highlightbackground=COLORS["border"])
    features_content.pack(pady=60, padx=60, fill="both", expand=True)
    tk.Label(features_content, text="PassVault Features", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=35)
    app.feature_text = tk.StringVar()
    app.feature_text.set("Explore Our Premium Features")
    tk.Label(features_content, textvariable=app.feature_text, font=FONTS["subheading"], bg=COLORS["card_bg"],
             fg=COLORS["subtext"]).pack(pady=20)

    feature_canvas = tk.Canvas(features_content, bg=COLORS["card_bg"], height=650, highlightthickness=0)
    feature_scrollbar = ttk.Scrollbar(features_content, orient="vertical", command=feature_canvas.yview)
    feature_button_frame = tk.Frame(feature_canvas, bg=COLORS["card_bg"])
    feature_button_frame.bind("<Configure>", lambda e: feature_canvas.configure(scrollregion=feature_canvas.bbox("all")))
    feature_canvas.create_window((0, 0), window=feature_button_frame, anchor="n")
    feature_canvas.configure(yscrollcommand=feature_scrollbar.set)

    def on_feature_mouse_wheel(event):
        if feature_canvas == app.active_canvas:
            delta = -1 if event.delta > 0 else 1
            feature_canvas.yview_scroll(delta, "units")
        return "break"

    feature_canvas.bind("<MouseWheel>", on_feature_mouse_wheel)
    feature_canvas.bind("<Button-4>", on_feature_mouse_wheel)
    feature_canvas.bind("<Button-5>", on_feature_mouse_wheel)
    feature_canvas.pack(side="left", fill="both", expand=True)
    feature_scrollbar.pack(side="right", fill="y")

    feature_descriptions = {
        "MultiDevice Access": "Access passwords across devices with real-time synchronization.",
        "Secure Pass Sharing": "Share passwords securely with trusted contacts using encryption.",
        "QRCode Sharing": "Quickly share passwords via QR codes for device-to-device transfer.",
        "Connected Devices": "Manage and monitor all devices linked to your PassVault account.",
        "Password Manager": "Store, organize, and generate strong passwords effortlessly.",
        "Expiration Alerts": "Get notified when passwords are about to expire or need updates.",
        "Audit Logs": "Track account activity and changes for enhanced security.",
        "Backups": "Create and restore data backups to protect your information.",
        "Activity History": "View detailed logs of your account actions with filtering options.",
        "File Manager": "Securely store, manage, and retrieve encrypted files."
    }

    # Create a frame to hold feature buttons in a grid
    feature_grid_frame = tk.Frame(feature_button_frame, bg=COLORS["card_bg"])
    feature_grid_frame.pack(pady=12, padx=15, fill="x")

    # Arrange features in a 2-column grid
    row = 0
    col = 0
    for feature in feature_descriptions:
        frame_key = feature.lower().replace(" ", "_").replace("qrcode", "qr")
        btn_frame = tk.Frame(feature_grid_frame, bg=COLORS["card_bg"], bd=2, relief="solid",
                             highlightbackground=COLORS["border"], width=300)
        btn_frame.grid(row=row, column=col, pady=12, padx=10, sticky="nsew")
        btn_frame.grid_propagate(False)
        btn = tk.Button(btn_frame, text=feature, bg=COLORS["primary"], fg=COLORS["dark_fg"],
                        font=FONTS["button"], width=32, height=2, bd=0, activebackground=COLORS["primary_hover"],
                        command=lambda f=frame_key: show_frame(f), relief="flat")
        btn.pack(pady=5, padx=5)
        btn.bind("<Enter>", lambda e, b=btn: b.configure(bg=COLORS["primary_hover"]))
        btn.bind("<Leave>", lambda e, b=btn: b.configure(bg=COLORS["primary"]))
        tk.Label(btn_frame, text=feature_descriptions[feature], font=FONTS["body"],
                 bg=COLORS["card_bg"], fg=COLORS["subtext"], wraplength=280).pack(pady=5, padx=5)
        
        col += 1
        if col > 1:
            col = 0
            row += 1

    # --- Profile and Preferences parent frame ---
    profile_parent = app.frames["profile"]

    # Profile sub-frame with scrollbar
    profile_frame = tk.Frame(profile_parent, bg=COLORS["background"])
    profile_frame.pack(side="left", fill="both", expand=True, padx=10)
    profile_canvas = tk.Canvas(profile_frame, bg=COLORS["card_bg"], highlightthickness=0, width=600)
    profile_scrollbar = ttk.Scrollbar(profile_frame, orient="vertical", command=profile_canvas.yview)
    profile_content = tk.Frame(profile_canvas, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                              highlightbackground=COLORS["border"])
    profile_content.bind("<Configure>", lambda e: profile_canvas.configure(scrollregion=profile_canvas.bbox("all")))
    profile_canvas.create_window((0, 0), window=profile_content, anchor="nw")
    profile_canvas.configure(yscrollcommand=profile_scrollbar.set)

    def on_profile_mouse_wheel(event):
        if profile_canvas == app.active_canvas:
            delta = -1 if event.delta > 0 else 1
            profile_canvas.yview_scroll(delta, "units")
        return "break"

    profile_canvas.bind("<MouseWheel>", on_profile_mouse_wheel)
    profile_canvas.bind("<Button-4>", on_profile_mouse_wheel)
    profile_canvas.bind("<Button-5>", on_profile_mouse_wheel)
    profile_canvas.pack(side="left", fill="both", expand=True, pady=50)
    profile_scrollbar.pack(side="right", fill="y")

    tk.Label(profile_content, text="User Profile", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=35)
    input_frame = tk.Frame(profile_content, bg=COLORS["card_bg"])
    input_frame.pack(pady=20)
    tk.Label(input_frame, text="Username", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.entry_profile_username = ttk.Entry(input_frame, width=35)
    app.entry_profile_username.pack(pady=10)
    tk.Label(input_frame, text="Email", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.entry_profile_email = ttk.Entry(input_frame, width=35)
    app.entry_profile_email.pack(pady=10)
    tk.Label(input_frame, text="Full Name", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.entry_profile_full_name = ttk.Entry(input_frame, width=35)
    app.entry_profile_full_name.pack(pady=10)
    tk.Label(input_frame, text="Phone", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.entry_profile_phone = ttk.Entry(input_frame, width=35)
    app.entry_profile_phone.pack(pady=10)
    tk.Button(input_frame, text="Edit Profile", bg=COLORS["secondary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=22, command=lambda: app.entry_profile_username.configure(state="normal") or
                             app.entry_profile_email.configure(state="normal") or
                             app.entry_profile_full_name.configure(state="normal") or
                             app.entry_profile_phone.configure(state="normal"), relief="flat").pack(pady=12)
    tk.Button(input_frame, text="Save Profile", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=22, command=lambda: save_profile(), relief="flat").pack(pady=12)
    tk.Button(input_frame, text="Change Password", bg=COLORS["secondary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=22, command=app.change_password, relief="flat").pack(pady=12)

    # Preferences sub-frame with scrollbar
    preferences_frame = tk.Frame(profile_parent, bg=COLORS["background"])
    preferences_frame.pack(side="left", fill="both", expand=True, padx=10)
    preferences_canvas = tk.Canvas(preferences_frame, bg=COLORS["card_bg"], highlightthickness=0, width=600)
    preferences_scrollbar = ttk.Scrollbar(preferences_frame, orient="vertical", command=preferences_canvas.yview)
    preferences_content = tk.Frame(preferences_canvas, bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                                  highlightbackground=COLORS["border"])
    preferences_content.bind("<Configure>", lambda e: preferences_canvas.configure(scrollregion=preferences_canvas.bbox("all")))
    preferences_canvas.create_window((0, 0), window=preferences_content, anchor="nw")
    preferences_canvas.configure(yscrollcommand=preferences_scrollbar.set)

    def on_preferences_mouse_wheel(event):
        if preferences_canvas == app.active_canvas:
            delta = -1 if event.delta > 0 else 1
            preferences_canvas.yview_scroll(delta, "units")
        return "break"

    preferences_canvas.bind("<MouseWheel>", on_preferences_mouse_wheel)
    preferences_canvas.bind("<Button-4>", on_preferences_mouse_wheel)
    preferences_canvas.bind("<Button-5>", on_preferences_mouse_wheel)
    preferences_canvas.pack(side="left", fill="both", expand=True, pady=50)
    preferences_scrollbar.pack(side="right", fill="y")

    tk.Label(preferences_content, text="User Preferences", font=FONTS["subheading"], bg=COLORS["card_bg"]).pack(pady=20)
    preferences_input_frame = tk.Frame(preferences_content, bg=COLORS["card_bg"])
    preferences_input_frame.pack(pady=15)
    tk.Label(preferences_input_frame, text="Default Password Length", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.combo_password_length = ttk.Combobox(preferences_input_frame, textvariable=app.var_password_length,
                                            values=["12", "16", "20"], width=32, state="readonly")
    app.combo_password_length.pack(pady=8)
    tk.Label(preferences_input_frame, text="Auto-Lock Timeout (minutes)", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.combo_auto_lock_timeout = ttk.Combobox(preferences_input_frame, textvariable=app.var_auto_lock_timeout,
                                              values=["5", "10", "15"], width=32, state="readonly")
    app.combo_auto_lock_timeout.pack(pady=8)
    tk.Label(preferences_input_frame, text="Require Uppercase Letters", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.check_require_uppercase = tk.Checkbutton(preferences_input_frame, variable=app.var_require_uppercase,
                                                bg=COLORS["card_bg"], font=FONTS["small"], state="disabled")
    app.check_require_uppercase.pack(pady=8)
    tk.Label(preferences_input_frame, text="Require Numbers", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.check_require_numbers = tk.Checkbutton(preferences_input_frame, variable=app.var_require_numbers,
                                              bg=COLORS["card_bg"], font=FONTS["small"], state="disabled")
    app.check_require_numbers.pack(pady=8)
    tk.Label(preferences_input_frame, text="Require Special Characters", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.check_require_special_chars = tk.Checkbutton(preferences_input_frame, variable=app.var_require_special_chars,
                                                    bg=COLORS["card_bg"], font=FONTS["small"], state="disabled")
    app.check_require_special_chars.pack(pady=8)
    tk.Label(preferences_input_frame, text="Default Sharing Method", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.combo_default_sharing_method = ttk.Combobox(preferences_input_frame, textvariable=app.var_default_sharing_method,
                                                   values=["qr_code", "secure_link"], width=32, state="readonly")
    app.combo_default_sharing_method.pack(pady=8)
    tk.Label(preferences_input_frame, text="Password Check Interval (days)", font=FONTS["small"], bg=COLORS["card_bg"]).pack()
    app.combo_password_check_interval = ttk.Combobox(preferences_input_frame, textvariable=app.var_password_check_interval,
                                                    values=["30", "60", "90"], width=32, state="readonly")
    app.combo_password_check_interval.pack(pady=8)
    tk.Button(preferences_input_frame, text="Edit Preferences", bg=COLORS["secondary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=22, command=lambda: [
                  app.combo_password_length.configure(state="normal"),
                  app.combo_auto_lock_timeout.configure(state="normal"),
                  app.check_require_uppercase.configure(state="normal"),
                  app.check_require_numbers.configure(state="normal"),
                  app.check_require_special_chars.configure(state="normal"),
                  app.combo_default_sharing_method.configure(state="normal"),
                  app.combo_password_check_interval.configure(state="normal")
              ], relief="flat").pack(pady=12)
    tk.Button(preferences_input_frame, text="Save Preferences", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=22, command=lambda: save_preferences(), relief="flat").pack(pady=12)

    # --- Settings frame ---
    settings_content = tk.Frame(app.frames["settings"], bg=COLORS["card_bg"], bd=0, highlightthickness=2,
                               highlightbackground=COLORS["border"])
    settings_content.pack(pady=100, padx=80, fill="both")
    tk.Label(settings_content, text="Settings", font=FONTS["heading"], bg=COLORS["card_bg"]).pack(pady=35)
    tk.Checkbutton(settings_content, text="Dark Mode", variable=app.var_dark_mode,
                   font=FONTS["body"], bg=COLORS["card_bg"], command=lambda: update_theme(app, app.root)).pack(pady=12)
    tk.Checkbutton(settings_content, text="Enable Notifications", variable=app.var_notifications,
                   font=FONTS["body"], bg=COLORS["card_bg"]).pack(pady=12)
    def save_settings():
        max_retries = 3
        retry_count = 0
        loading = show_loading(app.frames["settings"])
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("CALL BackupUserData(%s)", (app.current_user_id,))
                cursor.execute("CALL UpdateUserSettings(%s, %s, %s)",
                               (app.current_user_id, app.var_dark_mode.get(), app.var_notifications.get()))
                db.commit()
                messagebox.showinfo("Success", "Settings saved!")
                update_theme(app, app.root)
                break
            except mysql.connector.Error as e:
                logging.error(f"MySQL error in save_settings (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to save settings. Try restoring from backup?"):
                        restore_backup()
                    else:
                        messagebox.showerror("Error", f"Failed to save settings after retries: {e}")
            except Exception as e:
                logging.error(f"Unexpected error in save_settings (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to save settings. Try restoring from backup?"):
                        restore_backup()
                    else:
                        messagebox.showerror("Error", f"Failed to save settings after retries: {e}")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    tk.Button(settings_content, text="Save Settings", bg=COLORS["primary"], fg=COLORS["dark_fg"],
              font=FONTS["button"], width=22, command=lambda: save_settings(), relief="flat").pack(pady=20)

    def show_frame(frame_name):
        app.active_canvas = None
        for frame in app.frames.values():
            frame.pack_forget()
        target_frame = app.frames[frame_name]
        target_frame.pack(fill="both", expand=True)
        # Update sidebar/navbar username
        if hasattr(app, "current_user_id") and app.current_user_id:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                cursor.execute("SELECT username FROM users WHERE id=%s", (app.current_user_id,))
                user = cursor.fetchone()
                username = user[0] if user else "User"
                app.sidebar_username_label.config(text=username)
                app.navbar_username_label.config(text=username)
            except Exception:
                app.sidebar_username_label.config(text="User")
                app.navbar_username_label.config(text="User")
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()
        if frame_name == "features":
            app.active_canvas = feature_canvas
        elif frame_name == "profile":
            app.active_canvas = profile_canvas
            load_profile()
        elif frame_name == "home":
            app.active_canvas = home_canvas
            load_home()
        elif frame_name == "about_us":
            app.active_canvas = about_canvas
        elif frame_name == "settings":
            load_settings()
        elif frame_name in ["multidevice_access", "secure_pass_sharing", "qr_sharing",
                            "connected_devices", "password_manager", "expiration_alerts",
                            "audit_logs", "backups", "activity_history", "file_manager"]:
            app.feature_text.set(f"🧭 Exploring: {frame_name.replace('_', ' ').title()}")
            if hasattr(app.frames[frame_name], 'load'):
                app.frames[frame_name].load()

    def load_home():
        if not app.current_user_id:
            # Set default UI state when no user is logged in
            app.home_welcome_label.config(text="Welcome!")
            app.home_stats_passwords.config(text="Passwords: 0")
            app.home_stats_files.config(text="Files: 0")
            app.home_stats_last_login.config(text="Last Login: N/A")
            for item in app.home_activity_tree.get_children():
                app.home_activity_tree.delete(item)
            app.home_score_label.config(text="0%")
            app.home_score_canvas.delete("all")
            app.home_score_canvas.create_oval(10, 10, 90, 90, outline=COLORS["primary"], width=4)
            app.home_backup_label.config(text="Last: N/A")
            return

        max_retries = 3
        retry_count = 0
        loading = show_loading(app.frames["home"])
        try:
            db = app.db_pool.get_connection()
            cursor = db.cursor()
            db.start_transaction()

            # Welcome message
            cursor.execute("SELECT username FROM users WHERE id=%s", (app.current_user_id,))
            user = cursor.fetchone()
            if user:
                username = user[0]
                app.home_welcome_label.config(text=f"Welcome, {username}!")
            else:
                app.home_welcome_label.config(text="Welcome!")

            # Stats
            cursor.execute("SELECT COUNT(*) FROM passwords WHERE user_id=%s", (app.current_user_id,))
            password_count = cursor.fetchone()[0]
            app.home_stats_passwords.config(text=f"Passwords: {password_count}")

            cursor.execute("SELECT COUNT(*) FROM file_vault WHERE user_id=%s", (app.current_user_id,))
            file_count = cursor.fetchone()[0]
            app.home_stats_files.config(text=f"Files: {file_count}")

            cursor.execute("SELECT timestamp FROM audit_logs WHERE user_id=%s AND action='login' ORDER BY timestamp DESC LIMIT 1",
                           (app.current_user_id,))
            last_login = cursor.fetchone()
            app.home_stats_last_login.config(text=f"Last Login: {last_login[0] if last_login else 'N/A'}")

            # Recent Activity
            for item in app.home_activity_tree.get_children():
                app.home_activity_tree.delete(item)
            cursor.execute("""
                SELECT change_details, timestamp
                FROM audit_logs
                WHERE user_id=%s
                ORDER BY timestamp DESC
                LIMIT 5
            """, (app.current_user_id,))
            for log in cursor.fetchall():
                app.home_activity_tree.insert("", "end", values=(truncate_text(log[0], 30), log[1]))

            # Security Score (simplified: based on password count and last login)
            score = 0
            if password_count > 0:
                score += 50  # Base score for having passwords
            if last_login:
                score += 30  # Additional score for recent login
            score = min(100, score)  # Cap at 100%
            app.home_score_label.config(text=f"{score}%")
            app.home_score_canvas.delete("all")
            app.home_score_canvas.create_oval(10, 10, 90, 90, outline=COLORS["primary"], width=4)
            angle = (score / 100) * 360
            app.home_score_canvas.create_arc(10, 10, 90, 90, start=90, extent=-angle, fill=COLORS["primary"], outline="")

            # Backup Status
            cursor.execute("SELECT backup_time FROM backup_logs WHERE record_id=%s ORDER BY backup_time DESC LIMIT 1",
                           (app.current_user_id,))
            last_backup = cursor.fetchone()
            app.home_backup_label.config(text=f"Last: {last_backup[0] if last_backup else 'N/A'}")

            db.commit()
        except mysql.connector.Error as e:
            logging.error(f"Load home error (attempt {retry_count + 1}): {e}")
            if 'db' in locals():
                db.rollback()
            retry_count += 1
            if retry_count == max_retries:
                messagebox.showerror("Error", f"Failed to load dashboard data: {e}")
        finally:
            hide_loading(loading)
            if 'cursor' in locals():
                cursor.close()
            if 'db' in locals():
                db.close()

    def load_profile():
        max_retries = 3
        retry_count = 0
        loading = show_loading(app.frames["profile"])
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("SELECT username, email, full_name, phone FROM user_profiles WHERE user_id=%s",
                               (app.current_user_id,))
                profile = cursor.fetchone()
                if profile:
                    app.entry_profile_username.delete(0, tk.END)
                    app.entry_profile_username.insert(0, profile[0])
                    app.entry_profile_email.delete(0, tk.END)
                    app.entry_profile_email.insert(0, profile[1])
                    app.entry_profile_full_name.delete(0, tk.END)
                    app.entry_profile_full_name.insert(0, profile[2] or "")
                    app.entry_profile_phone.delete(0, tk.END)
                    app.entry_profile_phone.insert(0, profile[3] or "")
                else:
                    cursor.execute("SELECT username, email FROM users WHERE id=%s", (app.current_user_id,))
                    user = cursor.fetchone()
                    app.entry_profile_username.delete(0, tk.END)
                    app.entry_profile_username.insert(0, user[0])
                    app.entry_profile_email.delete(0, tk.END)
                    app.entry_profile_email.insert(0, user[1])
                    app.entry_profile_full_name.delete(0, tk.END)
                    app.entry_profile_phone.delete(0, tk.END)
                app.entry_profile_username.configure(state="disabled")
                app.entry_profile_email.configure(state="disabled")
                app.entry_profile_full_name.configure(state="disabled")
                app.entry_profile_phone.configure(state="disabled")
                cursor.execute("""
                    SELECT password_length, auto_lock_timeout, require_uppercase, require_numbers,
                           require_special_chars, default_sharing_method, password_check_interval
                    FROM user_preferences WHERE user_id=%s
                """, (app.current_user_id,))
                preferences = cursor.fetchone()
                if preferences:
                    app.var_password_length.set(str(preferences[0]))
                    app.var_auto_lock_timeout.set(str(preferences[1]))
                    app.var_require_uppercase.set(preferences[2])
                    app.var_require_numbers.set(preferences[3])
                    app.var_require_special_chars.set(preferences[4])
                    app.var_default_sharing_method.set(preferences[5])
                    app.var_password_check_interval.set(str(preferences[6]))
                else:
                    app.var_password_length.set("16")
                    app.var_auto_lock_timeout.set("10")
                    app.var_require_uppercase.set(True)
                    app.var_require_numbers.set(True)
                    app.var_require_special_chars.set(True)
                    app.var_default_sharing_method.set("qr_code")
                    app.var_password_check_interval.set("30")
                    cursor.execute("""
                        CALL UpdateUserPreferences(%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (app.current_user_id, 16, 10, True, True, True, 'qr_code', 30))
                app.combo_password_length.configure(state="readonly")
                app.combo_auto_lock_timeout.configure(state="readonly")
                app.check_require_uppercase.configure(state="disabled")
                app.check_require_numbers.configure(state="disabled")
                app.check_require_special_chars.configure(state="disabled")
                app.combo_default_sharing_method.configure(state="readonly")
                app.combo_password_check_interval.configure(state="readonly")
                db.commit()
                break
            except Exception as e:
                logging.error(f"Load profile error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to load profile or preferences. Try restoring from backup?"):
                        restore_backup()
                    else:
                        messagebox.showerror("Error", "Failed to load profile or preferences after retries.")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def save_profile():
        username = app.entry_profile_username.get().strip()
        email = app.entry_profile_email.get().strip()
        full_name = app.entry_profile_full_name.get().strip()
        phone = app.entry_profile_phone.get().strip()

        if not all([username, email]):
            messagebox.showerror("Error", "Username and Email required.")
            return
        if not validate_email(email):
            messagebox.showerror("Error", "Invalid email format.")
            return
        if phone and not validate_phone(phone):
            messagebox.showerror("Error", "Invalid phone format.")
            return

        max_retries = 3
        retry_count = 0
        loading = show_loading(app.frames["profile"])
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("CALL BackupUserData(%s)", (app.current_user_id,))
                cursor.execute("SELECT id FROM users WHERE (username=%s OR email=%s) AND id!=%s",
                               (username, email, app.current_user_id))
                if cursor.fetchone():
                    db.rollback()
                    messagebox.showerror("Error", "Username or Email exists.")
                    return
                cursor.execute("UPDATE users SET username=%s, email=%s WHERE id=%s",
                               (username, email, app.current_user_id))
                cursor.execute("CALL UpdateUserProfile(%s, %s, %s, %s, %s)",
                               (app.current_user_id, username, email, full_name, phone))
                db.commit()
                messagebox.showinfo("Success", "Profile updated!")
                app.entry_profile_username.configure(state="disabled")
                app.entry_profile_email.configure(state="disabled")
                app.entry_profile_full_name.configure(state="disabled")
                app.entry_profile_phone.configure(state="disabled")
                break
            except Exception as e:
                logging.error(f"Save profile error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to save profile. Try restoring from backup?"):
                        restore_backup()
                    else:
                        messagebox.showerror("Error", "Failed to save profile after retries.")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def restore_backup():
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("""
                    SELECT id, table_name, backup_time
                    FROM backup_logs
                    WHERE record_id = %s
                    ORDER BY backup_time DESC
                    LIMIT 5
                """, (app.current_user_id,))
                backups = cursor.fetchall()
                if not backups:
                    messagebox.showinfo("Info", "No backups available for this user.")
                    db.rollback()
                    return
                backup_options = [f"ID: {b[0]} | Table: {b[1]} | Time: {b[2]}" for b in backups]
                selected = tk.StringVar()
                dialog = tk.Toplevel(app.root)
                dialog.title("Select Backup")
                dialog.geometry("400x300")
                tk.Label(dialog, text="Select a backup to restore:", font=FONTS["body"]).pack(pady=10)
                combo = ttk.Combobox(dialog, textvariable=selected, values=backup_options, state="readonly")
                combo.pack(pady=10)
                def confirm_restore():
                    if not selected.get():
                        messagebox.showerror("Error", "Please select a backup.")
                        return
                    backup_id = int(selected.get().split(" | ")[0].replace("ID: ", ""))
                    try:
                        cursor.execute("CALL RestoreUserData(%s)", (backup_id,))
                        db.commit()
                        messagebox.showinfo("Success", "Backup restored successfully!")
                        dialog.destroy()
                        load_profile()
                        load_settings()
                    except Exception as e:
                        db.rollback()
                        messagebox.showerror("Error", f"Failed to restore backup: {e}")
                        dialog.destroy()
                tk.Button(dialog, text="Restore", command=confirm_restore, bg=COLORS["primary"],
                          fg=COLORS["dark_fg"], font=FONTS["button"]).pack(pady=10)
                tk.Button(dialog, text="Cancel", command=dialog.destroy, bg=COLORS["secondary"],
                          fg=COLORS["dark_fg"], font=FONTS["button"]).pack(pady=10)
                dialog.transient(app.root)
                dialog.grab_set()
                app.root.wait_window(dialog)
                break
            except Exception as e:
                logging.error(f"Restore backup error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    messagebox.showerror("Error", "Failed to load backups after retries.")
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def save_preferences():
        try:
            password_length = int(app.var_password_length.get())
            auto_lock_timeout = int(app.var_auto_lock_timeout.get())
            password_check_interval = int(app.var_password_check_interval.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid preference values.")
            return

        max_retries = 3
        retry_count = 0
        loading = show_loading(app.frames["profile"])
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("CALL BackupUserData(%s)", (app.current_user_id,))
                cursor.execute("""
                    CALL UpdateUserPreferences(%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    app.current_user_id,
                    password_length,
                    auto_lock_timeout,
                    app.var_require_uppercase.get(),
                    app.var_require_numbers.get(),
                    app.var_require_special_chars.get(),
                    app.var_default_sharing_method.get(),
                    password_check_interval
                ))
                db.commit()
                messagebox.showinfo("Success", "Preferences saved!")
                app.combo_password_length.configure(state="readonly")
                app.combo_auto_lock_timeout.configure(state="readonly")
                app.check_require_uppercase.configure(state="disabled")
                app.check_require_numbers.configure(state="disabled")
                app.check_require_special_chars.configure(state="disabled")
                app.combo_default_sharing_method.configure(state="readonly")
                app.combo_password_check_interval.configure(state="readonly")
                break
            except Exception as e:
                logging.error(f"Save preferences error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to save preferences. Try restoring from backup?"):
                        restore_backup()
                    else:
                        messagebox.showerror("Error", "Failed to save preferences after retries.")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def load_settings():
        max_retries = 3
        retry_count = 0
        loading = show_loading(app.frames["settings"])
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("SELECT dark_mode, notifications_enabled FROM user_settings WHERE user_id=%s",
                               (app.current_user_id,))
                settings = cursor.fetchone()
                if settings:
                    app.var_dark_mode.set(settings[0])
                    app.var_notifications.set(settings[1])
                else:
                    app.var_dark_mode.set(False)
                    app.var_notifications.set(True)
                    cursor.execute("CALL UpdateUserSettings(%s, %s, %s)",
                                   (app.current_user_id, False, True))
                db.commit()
                update_theme(app, app.root)
                break
            except mysql.connector.Error as e:
                logging.error(f"MySQL error in load_settings (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to load settings. Try restoring from backup?"):
                        restore_backup()
                    else:
                        messagebox.showerror("Error", f"Failed to load settings after retries: {e}")
            except Exception as e:
                logging.error(f"Unexpected error in load_settings (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to load settings. Try restoring frombackup?"):
                        restore_backup()
                    else:
                        messagebox.showerror("Error", f"Failed to load settings after retries: {e}")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def save_settings():
        max_retries = 3
        retry_count = 0
        loading = show_loading(app.frames["settings"])
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("CALL BackupUserData(%s)", (app.current_user_id,))
                cursor.execute("CALL UpdateUserSettings(%s, %s, %s)",
                               (app.current_user_id, app.var_dark_mode.get(), app.var_notifications.get()))
                db.commit()
                messagebox.showinfo("Success", "Settings saved!")
                update_theme(app, app.root)
                break
            except mysql.connector.Error as e:
                logging.error(f"MySQL error in save_settings (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to save settings. Try restoring from backup?"):
                        restore_backup()
                    else:
                        messagebox.showerror("Error", f"Failed to save settings after retries: {e}")
            except Exception as e:
                logging.error(f"Unexpected error in save_settings (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    if messagebox.askyesno("Error", "Failed to save settings. Try restoring from backup?"):
                        restore_backup()
                    else:
                        messagebox.showerror("Error", f"Failed to save settings after retries: {e}")
            finally:
                hide_loading(loading)
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    def restore_backup():
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                db = app.db_pool.get_connection()
                cursor = db.cursor()
                db.start_transaction()
                cursor.execute("""
                    SELECT id, table_name, backup_time
                    FROM backup_logs
                    WHERE record_id = %s
                    ORDER BY backup_time DESC
                    LIMIT 5
                """, (app.current_user_id,))
                backups = cursor.fetchall()
                if not backups:
                    messagebox.showinfo("Info", "No backups available for this user.")
                    db.rollback()
                    return
                backup_options = [f"ID: {b[0]} | Table: {b[1]} | Time: {b[2]}" for b in backups]
                selected = tk.StringVar()
                dialog = tk.Toplevel(app.root)
                dialog.title("Select Backup")
                dialog.geometry("400x300")
                tk.Label(dialog, text="Select a backup to restore:", font=FONTS["body"]).pack(pady=10)
                combo = ttk.Combobox(dialog, textvariable=selected, values=backup_options, state="readonly")
                combo.pack(pady=10)
                def confirm_restore():
                    if not selected.get():
                        messagebox.showerror("Error", "Please select a backup.")
                        return
                    backup_id = int(selected.get().split(" | ")[0].replace("ID: ", ""))
                    try:
                        cursor.execute("CALL RestoreUserData(%s)", (backup_id,))
                        db.commit()
                        messagebox.showinfo("Success", "Backup restored successfully!")
                        dialog.destroy()
                        load_profile()
                        load_settings()
                    except Exception as e:
                        db.rollback()
                        messagebox.showerror("Error", f"Failed to restore backup: {e}")
                        dialog.destroy()
                tk.Button(dialog, text="Restore", command=confirm_restore, bg=COLORS["primary"],
                          fg=COLORS["dark_fg"], font=FONTS["button"]).pack(pady=10)
                tk.Button(dialog, text="Cancel", command=dialog.destroy, bg=COLORS["secondary"],
                          fg=COLORS["dark_fg"], font=FONTS["button"]).pack(pady=10)
                dialog.transient(app.root)
                dialog.grab_set()
                app.root.wait_window(dialog)
                break
            except Exception as e:
                logging.error(f"Restore backup error (attempt {retry_count + 1}): {e}")
                if 'db' in locals():
                    db.rollback()
                retry_count += 1
                if retry_count == max_retries:
                    messagebox.showerror("Error", "Failed to load backups after retries.")
            finally:
                if 'cursor' in locals():
                    cursor.close()
                if 'db' in locals():
                    db.close()

    # Navbar: User Info
    user_nav_label = tk.Label(navbar, text="User", font=FONTS["body_bold"], fg=COLORS["dark_fg"], bg=COLORS["gradient_start"])
    user_nav_label.pack(side="right", padx=8)
    app.navbar_username_label = user_nav_label

    show_frame("home")
    return dashboard_frame