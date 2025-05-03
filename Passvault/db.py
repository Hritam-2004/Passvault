import mysql.connector
from mysql.connector import pooling
from tkinter import messagebox
import logging
import json

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "hritam2004",
    "database": "user_system",
    "pool_name": "passvault_pool",
    "pool_size": 5
}

class DatabaseConnectionPool:
    def __init__(self):
        self.pool = self.setup_connection_pool()

    def setup_connection_pool(self):
        try:
            connection_pool = pooling.MySQLConnectionPool(**DB_CONFIG)
            logging.info("Database connection pool created successfully.")
            self.setup_database(connection_pool)
            return connection_pool
        except mysql.connector.Error as err:
            logging.error(f"Failed to create connection pool: {err}")
            messagebox.showerror("Database Error", f"Failed to connect to database: {err}")
            raise

    def setup_database(self, connection_pool):
        try:
            db = connection_pool.get_connection()
            cursor = db.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS user_system")
            cursor.execute("USE user_system")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id INT PRIMARY KEY,
                    username VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    phone VARCHAR(20),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INT PRIMARY KEY,
                    dark_mode BOOLEAN DEFAULT FALSE,
                    notifications_enabled BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    user_id INT PRIMARY KEY,
                    password_length INT DEFAULT 16,
                    auto_lock_timeout INT DEFAULT 10,
                    require_uppercase BOOLEAN DEFAULT TRUE,
                    require_numbers BOOLEAN DEFAULT TRUE,
                    require_special_chars BOOLEAN DEFAULT TRUE,
                    default_sharing_method ENUM('qr_code', 'secure_link') DEFAULT 'qr_code',
                    password_check_interval INT DEFAULT 30,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS passwords (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    service VARCHAR(255) NOT NULL,
                    username VARCHAR(255),
                    password VARCHAR(255) NOT NULL,
                    expiration_date DATE,
                    password_strength VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS qr_codes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    service VARCHAR(255) NOT NULL,
                    username VARCHAR(255),
                    qr_code_data VARCHAR(255),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    device_name VARCHAR(255) NOT NULL,
                    ip_address VARCHAR(45),
                    access_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                    location VARCHAR(100),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shared_passwords (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    service VARCHAR(255) NOT NULL,
                    recipient VARCHAR(255),
                    shared_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    share_status VARCHAR(50) DEFAULT 'Pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connected_devices (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    device_name VARCHAR(255) NOT NULL,
                    device_type VARCHAR(50),
                    status VARCHAR(50) DEFAULT 'Active',
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expiration_alerts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    password_id INT,
                    service VARCHAR(255),
                    expiration_date DATE,
                    status VARCHAR(50),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (password_id) REFERENCES passwords(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_name VARCHAR(255) NOT NULL,
                    action ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
                    record_id INT NOT NULL,
                    user_id INT,
                    change_details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backup_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_name VARCHAR(255) NOT NULL,
                    record_id INT NOT NULL,
                    data TEXT NOT NULL,
                    backup_time DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_vault (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    file_name VARCHAR(255) NOT NULL,
                    encrypted_data LONGBLOB NOT NULL,
                    file_size BIGINT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # --- Notifications Table ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # --- Expiration Alert Notification Trigger ---
            cursor.execute("DROP TRIGGER IF EXISTS expiration_alerts_after_insert")
            cursor.execute("""
                DELIMITER //
                CREATE TRIGGER expiration_alerts_after_insert
                AFTER INSERT ON expiration_alerts
                FOR EACH ROW
                BEGIN
                    DECLARE notif_title VARCHAR(255);
                    DECLARE notif_msg TEXT;
                    SET notif_title = CONCAT('Password ', NEW.status);
                    SET notif_msg = CONCAT(
                        "Your password for '", NEW.service, "' is ",
                        LOWER(NEW.status), " (expires on ",
                        DATE_FORMAT(NEW.expiration_date, '%Y-%m-%d'), ")."
                    );
                    INSERT INTO notifications (user_id, title, message)
                    VALUES (NEW.user_id, notif_title, notif_msg);
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP TRIGGER IF EXISTS expiration_alerts_after_update")
            cursor.execute("""
                DELIMITER //
                CREATE TRIGGER expiration_alerts_after_update
                AFTER UPDATE ON expiration_alerts
                FOR EACH ROW
                BEGIN
                    DECLARE notif_title VARCHAR(255);
                    DECLARE notif_msg TEXT;
                    SET notif_title = CONCAT('Password ', NEW.status);
                    SET notif_msg = CONCAT(
                        "Your password for '", NEW.service, "' is ",
                        LOWER(NEW.status), " (expires on ",
                        DATE_FORMAT(NEW.expiration_date, '%Y-%m-%d'), ")."
                    );
                    INSERT INTO notifications (user_id, title, message)
                    VALUES (NEW.user_id, notif_title, notif_msg);
                END //
                DELIMITER ;
            """)

            # Triggers
            cursor.execute("DROP TRIGGER IF EXISTS users_after_insert")
            cursor.execute("""
                DELIMITER //
                CREATE TRIGGER users_after_insert
                AFTER INSERT ON users
                FOR EACH ROW
                BEGIN
                    INSERT INTO user_settings (user_id, dark_mode, notifications_enabled)
                    VALUES (NEW.id, FALSE, TRUE);
                    INSERT INTO user_preferences (
                        user_id, password_length, auto_lock_timeout, require_uppercase,
                        require_numbers, require_special_chars, default_sharing_method, password_check_interval
                    )
                    VALUES (NEW.id, 16, 10, TRUE, TRUE, TRUE, 'qr_code', 30);
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('users', 'INSERT', NEW.id, NEW.id, JSON_OBJECT(
                        'username', NEW.username, 'email', NEW.email
                    ));
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP TRIGGER IF EXISTS user_profiles_before_update")
            cursor.execute("""
                DELIMITER //
                CREATE TRIGGER user_profiles_before_update
                BEFORE UPDATE ON user_profiles
                FOR EACH ROW
                BEGIN
                    INSERT INTO backup_logs (table_name, record_id, data)
                    VALUES ('user_profiles', OLD.user_id, JSON_OBJECT(
                        'username', OLD.username, 'email', OLD.email,
                        'full_name', OLD.full_name, 'phone', OLD.phone
                    ));
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('user_profiles', 'UPDATE', OLD.user_id, OLD.user_id, JSON_OBJECT(
                        'old_username', OLD.username, 'new_username', NEW.username,
                        'old_email', OLD.email, 'new_email', NEW.email,
                        'old_full_name', OLD.full_name, 'new_full_name', NEW.full_name,
                        'old_phone', OLD.phone, 'new_phone', NEW.phone
                    ));
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP TRIGGER IF EXISTS user_settings_before_update")
            cursor.execute("""
                DELIMITER //
                CREATE TRIGGER user_settings_before_update
                BEFORE UPDATE ON user_settings
                FOR EACH ROW
                BEGIN
                    INSERT INTO backup_logs (table_name, record_id, data)
                    VALUES ('user_settings', OLD.user_id, JSON_OBJECT(
                        'dark_mode', OLD.dark_mode, 'notifications_enabled', OLD.notifications_enabled
                    ));
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('user_settings', 'UPDATE', OLD.user_id, OLD.user_id, JSON_OBJECT(
                        'old_dark_mode', OLD.dark_mode, 'new_dark_mode', NEW.dark_mode,
                        'old_notifications_enabled', OLD.notifications_enabled,
                        'new_notifications_enabled', NEW.notifications_enabled
                    ));
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP TRIGGER IF EXISTS user_preferences_before_update")
            cursor.execute("""
                DELIMITER //
                CREATE TRIGGER user_preferences_before_update
                BEFORE UPDATE ON user_preferences
                FOR EACH ROW
                BEGIN
                    INSERT INTO backup_logs (table_name, record_id, data)
                    VALUES ('user_preferences', OLD.user_id, JSON_OBJECT(
                        'password_length', OLD.password_length,
                        'auto_lock_timeout', OLD.auto_lock_timeout,
                        'require_uppercase', OLD.require_uppercase,
                        'require_numbers', OLD.require_numbers,
                        'require_special_chars', OLD.require_special_chars,
                        'default_sharing_method', OLD.default_sharing_method,
                        'password_check_interval', OLD.password_check_interval
                    ));
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('user_preferences', 'UPDATE', OLD.user_id, OLD.user_id, JSON_OBJECT(
                        'old_password_length', OLD.password_length, 'new_password_length', NEW.password_length,
                        'old_auto_lock_timeout', OLD.auto_lock_timeout, 'new_auto_lock_timeout', NEW.auto_lock_timeout,
                        'old_require_uppercase', OLD.require_uppercase, 'new_require_uppercase', NEW.require_uppercase,
                        'old_require_numbers', OLD.require_numbers, 'new_require_numbers', NEW.require_numbers,
                        'old_require_special_chars', OLD.require_special_chars, 'new_require_special_chars', NEW.require_special_chars,
                        'old_default_sharing_method', OLD.default_sharing_method, 'new_default_sharing_method', NEW.default_sharing_method,
                        'old_password_check_interval', OLD.password_check_interval, 'new_password_check_interval', NEW.password_check_interval
                    ));
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP TRIGGER IF EXISTS passwords_after_update")
            cursor.execute("""
                DELIMITER //
                CREATE TRIGGER passwords_after_update
                AFTER UPDATE ON passwords
                FOR EACH ROW
                BEGIN
                    UPDATE passwords SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('passwords', 'UPDATE', NEW.id, NEW.user_id, JSON_OBJECT(
                        'service', NEW.service, 'username', NEW.username,
                        'password_strength', NEW.password_strength
                    ));
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP TRIGGER IF EXISTS file_vault_before_delete")
            cursor.execute("""
                DELIMITER //
                CREATE TRIGGER file_vault_before_delete
                BEFORE DELETE ON file_vault
                FOR EACH ROW
                BEGIN
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('file_vault', 'DELETE', OLD.id, OLD.user_id, JSON_OBJECT(
                        'file_name', OLD.file_name, 'file_size', OLD.file_size
                    ));
                END //
                DELIMITER ;
            """)

            # Stored Procedures
            cursor.execute("DROP PROCEDURE IF EXISTS UpdateUserProfile")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE UpdateUserProfile(
                    IN p_user_id INT,
                    IN p_username VARCHAR(255),
                    IN p_email VARCHAR(255),
                    IN p_full_name VARCHAR(255),
                    IN p_phone VARCHAR(20)
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to update user profile';
                    END;
                    START TRANSACTION;
                    INSERT INTO user_profiles (user_id, username, email, full_name, phone)
                    VALUES (p_user_id, p_username, p_email, p_full_name, p_phone)
                    ON DUPLICATE KEY UPDATE
                        username = p_username,
                        email = p_email,
                        full_name = p_full_name,
                        phone = p_phone;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS UpdateUserSettings")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE UpdateUserSettings(
                    IN p_user_id INT,
                    IN p_dark_mode BOOLEAN,
                    IN p_notifications_enabled BOOLEAN
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to update user settings';
                    END;
                    START TRANSACTION;
                    INSERT INTO user_settings (user_id, dark_mode, notifications_enabled)
                    VALUES (p_user_id, p_dark_mode, p_notifications_enabled)
                    ON DUPLICATE KEY UPDATE
                        dark_mode = p_dark_mode,
                        notifications_enabled = p_notifications_enabled;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS UpdateUserPreferences")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE UpdateUserPreferences(
                    IN p_user_id INT,
                    IN p_password_length INT,
                    IN p_auto_lock_timeout INT,
                    IN p_require_uppercase BOOLEAN,
                    IN p_require_numbers BOOLEAN,
                    IN p_require_special_chars BOOLEAN,
                    IN p_default_sharing_method ENUM('qr_code', 'secure_link'),
                    IN p_password_check_interval INT
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to update user preferences';
                    END;
                    START TRANSACTION;
                    INSERT INTO user_preferences (
                        user_id, password_length, auto_lock_timeout, require_uppercase,
                        require_numbers, require_special_chars, default_sharing_method, password_check_interval
                    )
                    VALUES (
                        p_user_id, p_password_length, p_auto_lock_timeout, p_require_uppercase,
                        p_require_numbers, p_require_special_chars, p_default_sharing_method, p_password_check_interval
                    )
                    ON DUPLICATE KEY UPDATE
                        password_length = p_password_length,
                        auto_lock_timeout = p_auto_lock_timeout,
                        require_uppercase = p_require_uppercase,
                        require_numbers = p_require_numbers,
                        require_special_chars = p_require_special_chars,
                        default_sharing_method = p_default_sharing_method,
                        password_check_interval = p_password_check_interval;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS AddPassword")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE AddPassword(
                    IN p_user_id INT,
                    IN p_service VARCHAR(255),
                    IN p_username VARCHAR(255),
                    IN p_password VARCHAR(255),
                    IN p_expiration_date DATE,
                    IN p_password_strength VARCHAR(50)
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to add password';
                    END;
                    START TRANSACTION;
                    INSERT INTO passwords (user_id, service, username, password, expiration_date, password_strength)
                    VALUES (p_user_id, p_service, p_username, p_password, p_expiration_date, p_password_strength);
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('passwords', 'INSERT', LAST_INSERT_ID(), p_user_id, JSON_OBJECT(
                        'service', p_service, 'username', p_username, 'password_strength', p_password_strength
                    ));
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS DeletePassword")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE DeletePassword(
                    IN p_id INT,
                    IN p_user_id INT
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to delete password';
                    END;
                    START TRANSACTION;
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    SELECT 'passwords', 'DELETE', id, user_id, JSON_OBJECT(
                        'service', service, 'username', username, 'password_strength', password_strength
                    )
                    FROM passwords WHERE id = p_id AND user_id = p_user_id;
                    DELETE FROM passwords WHERE id = p_id AND user_id = p_user_id;
                    IF ROW_COUNT() = 0 THEN
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No password found or unauthorized';
                    END IF;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS AddQRCode")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE AddQRCode(
                    IN p_user_id INT,
                    IN p_service VARCHAR(255),
                    IN p_username VARCHAR(255),
                    IN p_qr_code_data VARCHAR(255)
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to add QR code';
                    END;
                    START TRANSACTION;
                    INSERT INTO qr_codes (user_id, service, username, qr_code_data)
                    VALUES (p_user_id, p_service, p_username, p_qr_code_data);
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('qr_codes', 'INSERT', LAST_INSERT_ID(), p_user_id, JSON_OBJECT(
                        'service', p_service, 'username', p_username
                    ));
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS DeleteQRCode")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE DeleteQRCode(
                    IN p_id INT,
                    IN p_user_id INT
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to delete QR code';
                    END;
                    START TRANSACTION;
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    SELECT 'qr_codes', 'DELETE', id, user_id, JSON_OBJECT(
                        'service', service, 'username', username
                    )
                    FROM qr_codes WHERE id = p_id AND user_id = p_user_id;
                    DELETE FROM qr_codes WHERE id = p_id AND user_id = p_user_id;
                    IF ROW_COUNT() = 0 THEN
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No QR code found or unauthorized';
                    END IF;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS AddAccessLog")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE AddAccessLog(
                    IN p_user_id INT,
                    IN p_device_name VARCHAR(255),
                    IN p_ip_address VARCHAR(45),
                    IN p_location VARCHAR(100)
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to add access log';
                    END;
                    START TRANSACTION;
                    INSERT INTO access_logs (user_id, device_name, ip_address, location)
                    VALUES (p_user_id, p_device_name, p_ip_address, p_location);
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('access_logs', 'INSERT', LAST_INSERT_ID(), p_user_id, JSON_OBJECT(
                        'device_name', p_device_name, 'ip_address', p_ip_address, 'location', p_location
                    ));
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS DeleteAccessLog")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE DeleteAccessLog(
                    IN p_id INT,
                    IN p_user_id INT
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to delete access log';
                    END;
                    START TRANSACTION;
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    SELECT 'access_logs', 'DELETE', id, user_id, JSON_OBJECT(
                        'device_name', device_name, 'ip_address', ip_address, 'location', location
                    )
                    FROM access_logs WHERE id = p_id AND user_id = p_user_id;
                    DELETE FROM access_logs WHERE id = p_id AND user_id = p_user_id;
                    IF ROW_COUNT() = 0 THEN
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No access log found or unauthorized';
                    END IF;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS SharePassword")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE SharePassword(
                    IN p_user_id INT,
                    IN p_service VARCHAR(255),
                    IN p_recipient VARCHAR(255),
                    IN p_share_status VARCHAR(50)
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to share password';
                    END;
                    START TRANSACTION;
                    INSERT INTO shared_passwords (user_id, service, recipient, share_status)
                    VALUES (p_user_id, p_service, p_recipient, p_share_status);
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('shared_passwords', 'INSERT', LAST_INSERT_ID(), p_user_id, JSON_OBJECT(
                        'service', p_service, 'recipient', p_recipient, 'share_status', p_share_status
                    ));
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS DeleteSharedPassword")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE DeleteSharedPassword(
                    IN p_id INT,
                    IN p_user_id INT
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to delete shared password';
                    END;
                    START TRANSACTION;
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    SELECT 'shared_passwords', 'DELETE', id, user_id, JSON_OBJECT(
                        'service', service, 'recipient', recipient, 'share_status', share_status
                    )
                    FROM shared_passwords WHERE id = p_id AND user_id = p_user_id;
                    DELETE FROM shared_passwords WHERE id = p_id AND user_id = p_user_id;
                    IF ROW_COUNT() = 0 THEN
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No shared password found or unauthorized';
                    END IF;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS AddConnectedDevice")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE AddConnectedDevice(
                    IN p_user_id INT,
                    IN p_device_name VARCHAR(255),
                    IN p_device_type VARCHAR(50),
                    IN p_status VARCHAR(50)
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to add connected device';
                    END;
                    START TRANSACTION;
                    INSERT INTO connected_devices (user_id, device_name, device_type, status)
                    VALUES (p_user_id, p_device_name, p_device_type, p_status);
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('connected_devices', 'INSERT', LAST_INSERT_ID(), p_user_id, JSON_OBJECT(
                        'device_name', p_device_name, 'device_type', p_device_type, 'status', p_status
                    ));
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS DeleteConnectedDevice")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE DeleteConnectedDevice(
                    IN p_id INT,
                    IN p_user_id INT
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to delete connected device';
                    END;
                    START TRANSACTION;
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    SELECT 'connected_devices', 'DELETE', id, user_id, JSON_OBJECT(
                        'device_name', device_name, 'device_type', device_type, 'status', status
                    )
                    FROM connected_devices WHERE id = p_id AND user_id = p_user_id;
                    DELETE FROM connected_devices WHERE id = p_id AND user_id = p_user_id;
                    IF ROW_COUNT() = 0 THEN
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No connected device found or unauthorized';
                    END IF;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS SetExpirationAlert")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE SetExpirationAlert(
                    IN p_user_id INT,
                    IN p_password_id INT,
                    IN p_service VARCHAR(255),
                    IN p_expiration_date DATE,
                    IN p_status VARCHAR(50)
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to set expiration alert';
                    END;
                    START TRANSACTION;
                    INSERT INTO expiration_alerts (user_id, password_id, service, expiration_date, status)
                    VALUES (p_user_id, p_password_id, p_service, p_expiration_date, p_status)
                    ON DUPLICATE KEY UPDATE
                        service = p_service,
                        expiration_date = p_expiration_date,
                        status = p_status,
                        updated_at = CURRENT_TIMESTAMP;
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('expiration_alerts', 'INSERT', LAST_INSERT_ID(), p_user_id, JSON_OBJECT(
                        'password_id', p_password_id, 'service', p_service, 'status', p_status
                    ));
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS DeleteExpirationAlert")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE DeleteExpirationAlert(
                    IN p_id INT,
                    IN p_user_id INT
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to delete expiration alert';
                    END;
                    START TRANSACTION;
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    SELECT 'expiration_alerts', 'DELETE', id, user_id, JSON_OBJECT(
                        'password_id', password_id, 'service', service, 'status', status
                    )
                    FROM expiration_alerts WHERE id = p_id AND user_id = p_user_id;
                    DELETE FROM expiration_alerts WHERE id = p_id AND user_id = p_user_id;
                    IF ROW_COUNT() = 0 THEN
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No expiration alert found or unauthorized';
                    END IF;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS AddFile")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE AddFile(
                    IN p_user_id INT,
                    IN p_file_name VARCHAR(255),
                    IN p_encrypted_data LONGBLOB,
                    IN p_file_size BIGINT
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to add file';
                    END;
                    START TRANSACTION;
                    INSERT INTO file_vault (user_id, file_name, encrypted_data, file_size)
                    VALUES (p_user_id, p_file_name, p_encrypted_data, p_file_size);
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    VALUES ('file_vault', 'INSERT', LAST_INSERT_ID(), p_user_id, JSON_OBJECT(
                        'file_name', p_file_name, 'file_size', p_file_size
                    ));
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS DeleteFile")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE DeleteFile(
                    IN p_id INT,
                    IN p_user_id INT
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to delete file';
                    END;
                    START TRANSACTION;
                    INSERT INTO audit_logs (table_name, action, record_id, user_id, change_details)
                    SELECT 'file_vault', 'DELETE', id, user_id, JSON_OBJECT(
                        'file_name', file_name, 'file_size', file_size
                    )
                    FROM file_vault WHERE id = p_id AND user_id = p_user_id;
                    DELETE FROM file_vault WHERE id = p_id AND user_id = p_user_id;
                    IF ROW_COUNT() = 0 THEN
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'No file found or unauthorized';
                    END IF;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS BackupUserData")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE BackupUserData(
                    IN p_user_id INT
                )
                BEGIN
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to backup user data';
                    END;
                    START TRANSACTION;
                    INSERT INTO backup_logs (table_name, record_id, data)
                    SELECT 'user_profiles', user_id, JSON_OBJECT(
                        'username', username, 'email', email,
                        'full_name', full_name, 'phone', phone
                    )
                    FROM user_profiles WHERE user_id = p_user_id;
                    INSERT INTO backup_logs (table_name, record_id, data)
                    SELECT 'user_settings', user_id, JSON_OBJECT(
                        'dark_mode', dark_mode, 'notifications_enabled', notifications_enabled
                    )
                    FROM user_settings WHERE user_id = p_user_id;
                    INSERT INTO backup_logs (table_name, record_id, data)
                    SELECT 'user_preferences', user_id, JSON_OBJECT(
                        'password_length', password_length,
                        'auto_lock_timeout', auto_lock_timeout,
                        'require_uppercase', require_uppercase,
                        'require_numbers', require_numbers,
                        'require_special_chars', require_special_chars,
                        'default_sharing_method', default_sharing_method,
                        'password_check_interval', password_check_interval
                    )
                    FROM user_preferences WHERE user_id = p_user_id;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            cursor.execute("DROP PROCEDURE IF EXISTS RestoreUserData")
            cursor.execute("""
                DELIMITER //
                CREATE PROCEDURE RestoreUserData(
                    IN p_backup_id INT
                )
                BEGIN
                    DECLARE v_table_name VARCHAR(255);
                    DECLARE v_record_id INT;
                    DECLARE v_data JSON;
                    DECLARE EXIT HANDLER FOR SQLEXCEPTION
                    BEGIN
                        ROLLBACK;
                        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Failed to restore user data';
                    END;
                    START TRANSACTION;
                    SELECT table_name, record_id, data
                    INTO v_table_name, v_record_id, v_data
                    FROM backup_logs WHERE id = p_backup_id;
                    IF v_table_name = 'user_profiles' THEN
                        INSERT INTO user_profiles (user_id, username, email, full_name, phone)
                        VALUES (
                            v_record_id,
                            JSON_UNQUOTE(JSON_EXTRACT(v_data, '$.username')),
                            JSON_UNQUOTE(JSON_EXTRACT(v_data, '$.email')),
                            JSON_UNQUOTE(JSON_EXTRACT(v_data, '$.full_name')),
                            JSON_UNQUOTE(JSON_EXTRACT(v_data, '$.phone'))
                        )
                        ON DUPLICATE KEY UPDATE
                            username = JSON_UNQUOTE(JSON_EXTRACT(v_data, '$.username')),
                            email = JSON_UNQUOTE(JSON_EXTRACT(v_data, '$.email')),
                            full_name = JSON_UNQUOTE(JSON_EXTRACT(v_data, '$.full_name')),
                            phone = JSON_UNQUOTE(JSON_EXTRACT(v_data, '$.phone'));
                    ELSEIF v_table_name = 'user_settings' THEN
                        INSERT INTO user_settings (user_id, dark_mode, notifications_enabled)
                        VALUES (
                            v_record_id,
                            JSON_EXTRACT(v_data, '$.dark_mode'),
                            JSON_EXTRACT(v_data, '$.notifications_enabled')
                        )
                        ON DUPLICATE KEY UPDATE
                            dark_mode = JSON_EXTRACT(v_data, '$.dark_mode'),
                            notifications_enabled = JSON_EXTRACT(v_data, '$.notifications_enabled');
                    ELSEIF v_table_name = 'user_preferences' THEN
                        INSERT INTO user_preferences (
                            user_id, password_length, auto_lock_timeout, require_uppercase,
                            require_numbers, require_special_chars, default_sharing_method, password_check_interval
                        )
                        VALUES (
                            v_record_id,
                            JSON_EXTRACT(v_data, '$.password_length'),
                            JSON_EXTRACT(v_data, '$.auto_lock_timeout'),
                            JSON_EXTRACT(v_data, '$.require_uppercase'),
                            JSON_EXTRACT(v_data, '$.require_numbers'),
                            JSON_EXTRACT(v_data, '$.require_special_chars'),
                            JSON_UNQUOTE(JSON_EXTRACT(v_data, '$.default_sharing_method')),
                            JSON_EXTRACT(v_data, '$.password_check_interval')
                        )
                        ON DUPLICATE KEY UPDATE
                            password_length = JSON_EXTRACT(v_data, '$.password_length'),
                            auto_lock_timeout = JSON_EXTRACT(v_data, '$.auto_lock_timeout'),
                            require_uppercase = JSON_EXTRACT(v_data, '$.require_uppercase'),
                            require_numbers = JSON_EXTRACT(v_data, '$.require_numbers'),
                            require_special_chars = JSON_EXTRACT(v_data, '$.require_special_chars'),
                            default_sharing_method = JSON_UNQUOTE(JSON_EXTRACT(v_data, '$.default_sharing_method')),
                            password_check_interval = JSON_EXTRACT(v_data, '$.password_check_interval');
                    END IF;
                    COMMIT;
                END //
                DELIMITER ;
            """)

            db.commit()
            logging.info("Database and tables set up successfully.")
        except mysql.connector.Error as err:
            logging.error(f"MySQL error in setup_database: {err}")
            messagebox.showerror("Database Error", f"Failed to setup database: {err}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error in setup_database: {e}")
            messagebox.showerror("Database Error", f"Unexpected error during setup: {e}")
            raise
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'db' in locals():
                db.close()

    def get_connection(self):
        try:
            return self.pool.get_connection()
        except mysql.connector.Error as err:
            logging.error(f"Failed to get connection from pool: {err}")
            messagebox.showerror("Database Error", f"Failed to get database connection: {err}")
            raise