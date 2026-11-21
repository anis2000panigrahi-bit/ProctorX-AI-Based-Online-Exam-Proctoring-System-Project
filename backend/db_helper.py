import os
import mysql.connector

from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        connection_timeout=5
    )


def verify_and_upgrade_password(connection, cursor, email, password, stored_password):
    if stored_password.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored_password, password)

    if stored_password == password:
        hashed_password = generate_password_hash(password)

        cursor.execute(
            """
            UPDATE sign_up
            SET password = %s
            WHERE email = %s
            """,
            (hashed_password, email)
        )

        connection.commit()
        return True

    return False


def initialize_phase5_tables():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exam_violations (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                exam_id VARCHAR(100) NOT NULL,
                candidate_email VARCHAR(255) NOT NULL,
                violation_source VARCHAR(50) NOT NULL,
                violation_type VARCHAR(100),
                reason TEXT NOT NULL,
                application VARCHAR(100),
                occurred_at DATETIME(6) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                INDEX idx_exam_id (exam_id),
                INDEX idx_candidate_email (candidate_email)
            )
        """)

        connection.commit()
        print("Phase 5 database tables initialized successfully.")

    finally:
        cursor.close()
        connection.close()


def get_all_details():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            SELECT email, username
            FROM sign_up
        """)

        rows = cursor.fetchall()

        for row in rows:
            print(row)

    finally:
        cursor.close()
        connection.close()


def insert_signup(email, username, password):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        hashed_password = generate_password_hash(password)

        query = """
            INSERT INTO sign_up (email, username, password)
            VALUES (%s, %s, %s)
        """

        cursor.execute(query, (email, username, hashed_password))
        connection.commit()

        print("Sign-Up data inserted successfully!")
        return 1

    except mysql.connector.Error as err:
        print("Database error:", err)
        connection.rollback()
        return -1

    finally:
        cursor.close()
        connection.close()


def search_login_credentials(email, password):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT password
            FROM sign_up
            WHERE email = %s
            """,
            (email,)
        )

        result = cursor.fetchone()

        if result is None:
            return False

        stored_password = result[0]

        return verify_and_upgrade_password(
            connection,
            cursor,
            email,
            password,
            stored_password
        )

    finally:
        cursor.close()
        connection.close()


def get_profile_details(email):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT email, username
            FROM sign_up
            WHERE email = %s
        """

        cursor.execute(query, (email,))
        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


def update_profile_username(email, username):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        query = """
            UPDATE sign_up
            SET username = %s
            WHERE email = %s
        """

        cursor.execute(query, (username, email))
        connection.commit()

        return cursor.rowcount > 0

    except mysql.connector.Error as err:
        print("Profile update database error:", err)
        connection.rollback()
        return False

    finally:
        cursor.close()
        connection.close()


def verify_current_password(email, current_password):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT password
            FROM sign_up
            WHERE email = %s
            """,
            (email,)
        )

        result = cursor.fetchone()

        if result is None:
            return False

        stored_password = result[0]

        return verify_and_upgrade_password(
            connection,
            cursor,
            email,
            current_password,
            stored_password
        )

    finally:
        cursor.close()
        connection.close()


def update_account_password(email, new_password):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        hashed_password = generate_password_hash(new_password)

        query = """
            UPDATE sign_up
            SET password = %s
            WHERE email = %s
        """

        cursor.execute(query, (hashed_password, email))
        connection.commit()

        return cursor.rowcount > 0

    except mysql.connector.Error as err:
        print("Password update database error:", err)
        connection.rollback()
        return False

    finally:
        cursor.close()
        connection.close()


def save_exam_violation(
    exam_id,
    candidate_email,
    violation_source,
    violation_type,
    reason,
    application=None,
    occurred_at=None
):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        if isinstance(occurred_at, str):
            occurred_at = datetime.fromisoformat(
                occurred_at.replace("Z", "+00:00")
            )

        if occurred_at is None:
            occurred_at = datetime.now(timezone.utc)

        if occurred_at.tzinfo is not None:
            occurred_at = occurred_at.astimezone(timezone.utc).replace(
                tzinfo=None
            )

        query = """
            INSERT INTO exam_violations (
                exam_id,
                candidate_email,
                violation_source,
                violation_type,
                reason,
                application,
                occurred_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (
                exam_id,
                candidate_email,
                violation_source,
                violation_type,
                reason,
                application,
                occurred_at
            )
        )

        connection.commit()
        return cursor.lastrowid

    except Exception as err:
        print("Violation storage error:", err)
        connection.rollback()
        return None

    finally:
        cursor.close()
        connection.close()


def save_exam_violations(exam_id, candidate_email, violations):
    saved_count = 0

    for violation in violations:
        violation_id = save_exam_violation(
            exam_id=exam_id,
            candidate_email=candidate_email,
            violation_source=violation.get("source", "AI"),
            violation_type=violation.get("type", "General"),
            reason=violation.get("reason", "Unspecified violation"),
            application=violation.get("application"),
            occurred_at=violation.get(
                "time",
                violation.get("timestamp")
            )
        )

        if violation_id is not None:
            saved_count += 1

    return saved_count


def get_exam_violations(exam_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT *
            FROM exam_violations
            WHERE exam_id = %s
            ORDER BY occurred_at ASC
        """

        cursor.execute(query, (exam_id,))
        return cursor.fetchall()

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    initialize_phase5_tables()
    get_all_details()