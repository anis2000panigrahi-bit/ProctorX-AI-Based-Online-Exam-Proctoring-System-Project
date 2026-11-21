from flask import (
    Flask,
    render_template,
    Response,
    request,
    jsonify,
    session,
    redirect,
    url_for
)

from flask_cors import CORS

from backend.db_helper import (
    insert_signup,
    search_login_credentials,
    save_exam_violations,
    get_profile_details,
    update_profile_username,
    verify_current_password,
    update_account_password
)

from exam_data import MCQ_BANK, LONG_BANK

from datetime import datetime, timezone, timedelta
from threading import Lock

import main
import os
import random
import json
import secrets
import hmac
import time
import threading


# -----------------------------------------
# FLASK APPLICATION CONFIGURATION
# -----------------------------------------

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "change-this-secret-before-deployment"
)

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

app.config["SESSION_COOKIE_HTTPONLY"] = True

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["SESSION_REFRESH_EACH_REQUEST"] = True

CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HISTORY_PATH = os.path.join(
    BASE_DIR,
    "exam_submissions.json"
)

DESKTOP_TOKEN_PATH = os.path.join(
    BASE_DIR,
    ".desktop_monitor_token.json"
)

MAX_VIOLATIONS = 10
HEARTBEAT_TIMEOUT = 15

history_lock = Lock()
desktop_lock = Lock()
db_persistence_lock = Lock()

desktop_exam_registry = {}
desktop_token_index = {}

ALLOWED_DESKTOP_APPLICATIONS = {
    "Notepad",
    "Calculator"
}


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------
# DATABASE VIOLATION STORAGE
# -----------------------------------------

def save_violations_to_database(
    exam_id,
    registry,
    ai_violations,
    desktop_violations
):

    if not exam_id or not registry:
        return 0

    saved_total = 0

    with db_persistence_lock:

        ai_saved = registry.get(
            "db_saved_ai_count",
            0
        )

        desktop_saved = registry.get(
            "db_saved_desktop_count",
            0
        )

        new_ai_violations = ai_violations[ai_saved:]

        new_desktop_violations = desktop_violations[desktop_saved:]

        email = registry.get("email", "")

        if not email:
            return 0

        try:

            if new_ai_violations:

                saved_ai = save_exam_violations(
                    exam_id,
                    email,
                    new_ai_violations
                )

                saved_ai = max(
                    0,
                    min(
                        int(saved_ai or 0),
                        len(new_ai_violations)
                    )
                )

                registry["db_saved_ai_count"] = (
                    ai_saved + saved_ai
                )

                saved_total += saved_ai

            if new_desktop_violations:

                saved_desktop = save_exam_violations(
                    exam_id,
                    email,
                    new_desktop_violations
                )

                saved_desktop = max(
                    0,
                    min(
                        int(saved_desktop or 0),
                        len(new_desktop_violations)
                    )
                )

                registry["db_saved_desktop_count"] = (
                    desktop_saved + saved_desktop
                )

                saved_total += saved_desktop

        except Exception:

            app.logger.exception(
                "Could not save violations for examination %s",
                exam_id
            )

    return saved_total


# -----------------------------------------
# HISTORY MANAGEMENT
# -----------------------------------------

def save_exam_record(record):

    try:

        with history_lock:

            if os.path.exists(HISTORY_PATH):

                with open(
                    HISTORY_PATH,
                    "r",
                    encoding="utf-8"
                ) as history_file:

                    history = json.load(history_file)

                    if not isinstance(history, list):
                        history = []

            else:

                history = []

            history.append(record)

            temporary_path = HISTORY_PATH + ".tmp"

            with open(
                temporary_path,
                "w",
                encoding="utf-8"
            ) as history_file:

                json.dump(
                    history,
                    history_file,
                    indent=2
                )

            os.replace(
                temporary_path,
                HISTORY_PATH
            )

        return True

    except (OSError, json.JSONDecodeError):

        app.logger.exception(
            "Could not save examination history."
        )

        return False


# -----------------------------------------
# DESKTOP TOKEN MANAGEMENT
# -----------------------------------------

def create_desktop_exam(exam_id, email):

    token = secrets.token_urlsafe(32)

    exam_data = {
        "token": token,
        "email": email,
        "events": [],
        "last_event": {},
        "last_heartbeat": time.time(),
        "pattern": None,
        "db_saved_ai_count": 0,
        "db_saved_desktop_count": 0
    }

    with desktop_lock:

        desktop_exam_registry[exam_id] = exam_data

        desktop_token_index[token] = exam_id

    token_data = {
        "token": token,
        "exam_id": exam_id,
        "server_url": "http://127.0.0.1:5000"
    }

    temporary_path = DESKTOP_TOKEN_PATH + ".tmp"

    try:

        with open(
            temporary_path,
            "w",
            encoding="utf-8"
        ) as token_file:

            json.dump(
                token_data,
                token_file,
                indent=2
            )

        os.replace(
            temporary_path,
            DESKTOP_TOKEN_PATH
        )

    except OSError:

        with desktop_lock:

            desktop_exam_registry.pop(
                exam_id,
                None
            )

            desktop_token_index.pop(
                token,
                None
            )

        raise

    return token


def revoke_desktop_exam(exam):

    if not exam:
        return

    exam_id = exam.get("exam_id")

    if not exam_id:
        return

    with desktop_lock:

        registry = desktop_exam_registry.pop(
            exam_id,
            None
        )

        if registry:

            desktop_token_index.pop(
                registry.get("token"),
                None
            )

    try:

        if os.path.exists(DESKTOP_TOKEN_PATH):

            with open(
                DESKTOP_TOKEN_PATH,
                "r",
                encoding="utf-8"
            ) as token_file:

                token_data = json.load(token_file)

            if token_data.get("exam_id") == exam_id:

                os.remove(DESKTOP_TOKEN_PATH)

    except (OSError, json.JSONDecodeError):

        app.logger.warning(
            "Could not remove the desktop monitor token file."
        )


# -----------------------------------------
# DESKTOP VIOLATION SYNCHRONIZATION
# -----------------------------------------

def sync_desktop_violations(exam):

    if not exam:
        return exam

    exam_id = exam.get("exam_id")

    if not exam_id:
        return exam

    synced_count = exam.get(
        "desktop_synced_count",
        0
    )

    with desktop_lock:

        registry = desktop_exam_registry.get(exam_id)

        if not registry:
            return exam

        events = registry["events"][synced_count:]

        for event in events:

            exam.setdefault(
                "violations",
                []
            ).append({
                "source": "Desktop",
                "reason": event["reason"],
                "application": event["application"],
                "time": event["time"]
            })

        exam["desktop_synced_count"] = (
            synced_count + len(events)
        )

    session["exam"] = exam
    session.modified = True

    return exam


# -----------------------------------------
# COMBINED PROCTORING STATUS
# -----------------------------------------

def get_combined_proctor_status(exam):

    exam = sync_desktop_violations(exam)

    ai_status = main.get_proctoring_status()

    ai_violations = ai_status.get(
        "violations",
        []
    )

    desktop_violations = exam.get(
        "violations",
        []
    )

    combined_violations = (
        list(ai_violations) +
        list(desktop_violations)
    )

    exam_id = exam.get("exam_id")

    with desktop_lock:

        registry = desktop_exam_registry.get(exam_id)

    if registry:

        save_violations_to_database(
            exam_id,
            registry,
            ai_violations,
            desktop_violations
        )

    combined_count = (
        ai_status.get("violation_count", 0) +
        len(desktop_violations)
    )

    return {
        "violation_count": combined_count,
        "max_violations": MAX_VIOLATIONS,
        "violations": combined_violations,
        "cancelled": False,
        "limit_reached": combined_count >= MAX_VIOLATIONS
    }


# -----------------------------------------
# SIGNUP
# -----------------------------------------

@app.route("/signup_data", methods=["POST"])
def signup_data():

    data = request.get_json(silent=True) or {}

    email = (
        data.get("signupEmail") or ""
    ).strip().lower()

    username = (
        data.get("username") or ""
    ).strip()

    password = data.get("signupPassword") or ""

    if not email or not username or not password:

        return jsonify({
            "success": False,
            "message": "Please complete all fields."
        }), 400

    try:

        result = insert_signup(
            email,
            username,
            password
        )

        if result == 1:

            return jsonify({
                "success": True,
                "message": "Account created. Please sign in."
            })

        return jsonify({
            "success": False,
            "message": "Could not create account. The email may already exist."
        }), 400

    except Exception:

        app.logger.exception("Signup error.")

        return jsonify({
            "success": False,
            "message": "Unable to create your account. Check the database connection."
        }), 500


# -----------------------------------------
# LOGIN
# -----------------------------------------

@app.route("/login_data", methods=["POST"])
def login_data():

    data = request.get_json(silent=True) or {}

    email = (
        data.get("loginEmail")
        or data.get("email")
        or ""
    ).strip().lower()

    password = (
        data.get("loginPassword")
        or data.get("password")
        or ""
    )

    if not email or not password:

        return jsonify({
            "success": False,
            "message": "Please enter your email and password."
        }), 400

    try:

        valid = search_login_credentials(
            email,
            password
        )

        if not valid:

            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        profile = get_profile_details(email)

        session.clear()

        session.permanent = True

        session["user_email"] = email

        session["username"] = (
            profile["username"]
            if profile
            else email.split("@")[0]
        )

        session.modified = True

        return jsonify({
            "success": True,
            "message": "Login successful.",
            "username": session["username"]
        })

    except Exception:

        app.logger.exception("Login error.")

        return jsonify({
            "success": False,
            "message": "Unable to log in. Please check your database connection."
        }), 500


# -----------------------------------------
# HOME PAGE
# -----------------------------------------

@app.route("/")
def index_page():

    if "user_email" in session:

        return redirect(
            url_for("dashboard")
        )

    return render_template("index.html")


# -----------------------------------------
# DASHBOARD
# -----------------------------------------

@app.route("/dashboard")
def dashboard():

    if "user_email" not in session:

        return redirect(
            url_for("index_page")
        )

    return render_template(
        "quiz.html",
        user_email=session["user_email"]
    )
# -----------------------------------------
# EXAMINATION PAGE
# -----------------------------------------

@app.route("/quiz_html")
def quiz_page():

    if "user_email" not in session:

        return redirect(
            url_for("index_page")
        )

    return render_template(
        "quiz.html",
        user_email=session["user_email"]
    )


# -----------------------------------------
# LOGOUT
# -----------------------------------------

@app.route("/logout")
def logout():

    exam = session.get("exam")

    if exam:

        get_combined_proctor_status(exam)

        revoke_desktop_exam(exam)

        main.stop_proctoring()

    session.clear()

    return redirect(
        url_for("index_page")
    )


# -----------------------------------------
# START EXAMINATION
# -----------------------------------------

@app.route("/api/start_exam", methods=["POST"])
def start_exam():

    if "user_email" not in session:

        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401

    if session.get("exam"):

        return jsonify({
            "success": False,
            "message": "An examination is already active."
        }), 400

    data = request.get_json(silent=True) or {}

    pattern = data.get("pattern")

    if pattern == "short":

        if not MCQ_BANK:

            return jsonify({
                "success": False,
                "message": "No multiple-choice questions are available."
            }), 500

        chosen = random.sample(
            MCQ_BANK,
            k=min(10, len(MCQ_BANK))
        )

        questions = [
            {
                "id": q["id"],
                "question": q["question"],
                "options": q["options"]
            }
            for q in chosen
        ]

        exam = {
            "pattern": "short",
            "questions": questions,
            "answer_key": {
                q["id"]: q["answer"]
                for q in chosen
            }
        }

    elif pattern == "long":

        if not LONG_BANK:

            return jsonify({
                "success": False,
                "message": "No descriptive questions are available."
            }), 500

        chosen = random.sample(
            LONG_BANK,
            k=min(5, len(LONG_BANK))
        )

        exam = {
            "pattern": "long",
            "questions": chosen
        }

    else:

        return jsonify({
            "success": False,
            "message": "Choose a valid exam pattern."
        }), 400

    exam_id = secrets.token_urlsafe(18)

    exam.update({
        "exam_id": exam_id,
        "desktop_synced_count": 0,
        "db_saved_ai_count": 0,
        "db_saved_desktop_count": 0,
        "violations": []
    })

    try:

        create_desktop_exam(
            exam_id,
            session["user_email"]
        )

        with desktop_lock:

            desktop_exam_registry[exam_id]["pattern"] = pattern

    except OSError:

        app.logger.exception(
            "Could not create desktop monitor token."
        )

        return jsonify({
            "success": False,
            "message": "Could not initialize desktop monitoring."
        }), 500

    session["exam"] = exam

    session.modified = True

    main.reset_proctoring()

    return jsonify({
        "success": True,
        "pattern": pattern,
        "questions": exam["questions"],
        "total": len(exam["questions"])
    })


# -----------------------------------------
# DESKTOP MONITOR EVENT ENDPOINT
# -----------------------------------------

@app.route("/api/desktop_event", methods=["POST"])
def desktop_event():

    authorization = request.headers.get(
        "Authorization",
        ""
    )

    if not authorization.startswith("Bearer "):

        return jsonify({
            "success": False,
            "message": "Missing authentication token."
        }), 401

    token = authorization[7:].strip()

    if not token:

        return jsonify({
            "success": False,
            "message": "Invalid authentication token."
        }), 401

    data = request.get_json(silent=True) or {}

    application = data.get("application")

    if application not in ALLOWED_DESKTOP_APPLICATIONS:

        return jsonify({
            "success": False,
            "message": "Application is not allowed."
        }), 400

    with desktop_lock:

        exam_id = desktop_token_index.get(token)

        if not exam_id:

            return jsonify({
                "success": False,
                "message": "Invalid or expired examination token."
            }), 401

        registry = desktop_exam_registry.get(exam_id)

        if not registry:

            return jsonify({
                "success": False,
                "message": "Examination is no longer active."
            }), 401

        if not hmac.compare_digest(
            registry["token"],
            token
        ):

            return jsonify({
                "success": False,
                "message": "Authentication failed."
            }), 401

        now = datetime.now(timezone.utc)

        previous_time = registry["last_event"].get(
            application
        )

        if previous_time:

            elapsed = (
                now - previous_time
            ).total_seconds()

            if elapsed < 10:

                return jsonify({
                    "success": True,
                    "duplicate": True,
                    "message": "Event already recorded recently."
                })

        registry["last_event"][application] = now

        registry["events"].append({
            "application": application,
            "reason": (
                f"Prohibited application detected: {application}"
            ),
            "time": now.isoformat()
        })

    return jsonify({
        "success": True,
        "message": "Desktop event received."
    })


# -----------------------------------------
# REPORT BROWSER VIOLATIONS
# -----------------------------------------

@app.route("/api/report_violation", methods=["POST"])
def report_violation():

    if "user_email" not in session:

        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401

    exam = session.get("exam")

    if not exam:

        return jsonify({
            "success": False,
            "message": "No active examination."
        }), 400

    data = request.get_json(silent=True) or {}

    reason = str(
        data.get("reason", "Browser violation")
    ).strip()[:200]

    if not reason:
        reason = "Browser violation"

    main.register_violation(reason)

    status = get_combined_proctor_status(exam)

    return jsonify({
        "success": True,
        "reason": reason,
        "violation_count": status["violation_count"],
        "max_violations": status["max_violations"],
        "violations": status["violations"],
        "cancelled": False
    })


# -----------------------------------------
# PROCTORING STATUS
# -----------------------------------------

@app.route("/api/proctor_status", methods=["GET"])
def proctor_status():

    if "user_email" not in session:

        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401

    exam = session.get("exam")

    if not exam:

        return jsonify({
            "success": False,
            "message": "No active examination."
        }), 400

    status = get_combined_proctor_status(exam)

    return jsonify({
        "success": True,
        "violation_count": status["violation_count"],
        "max_violations": status["max_violations"],
        "violations": status["violations"],
        "cancelled": False,
        "limit_reached": status["limit_reached"]
    })


# -----------------------------------------
# SUBMIT EXAMINATION
# -----------------------------------------

@app.route("/api/submit_exam", methods=["POST"])
def submit_exam():

    if "user_email" not in session:

        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401

    exam = session.get("exam")

    if not exam:

        return jsonify({
            "success": False,
            "message": "No active exam found. Start a new exam."
        }), 400

    proctor_status = get_combined_proctor_status(exam)

    data = request.get_json(silent=True) or {}

    answers = data.get("answers", {})

    if not isinstance(answers, dict):
        answers = {}

    questions = exam["questions"]

    if exam["pattern"] == "short":

        answer_key = exam["answer_key"]

        correct = sum(
            1
            for qid, answer in answer_key.items()
            if answers.get(qid) == answer
        )

        total = len(answer_key)

        answered = sum(
            1
            for qid in answer_key
            if qid in answers and str(answers[qid]).strip()
        )

        result = {
            "success": True,
            "pattern": "short",
            "total": total,
            "correct": correct,
            "incorrect": total - correct,
            "unanswered": total - answered,
            "percentage": round(
                (correct / total) * 100,
                2
            ) if total else 0,
            "status": (
                "Passed"
                if correct >= (total * 0.4)
                else "Needs improvement"
            )
        }

    else:

        submitted = sum(
            1
            for q in questions
            if str(answers.get(q["id"], "")).strip()
        )

        result = {
            "success": True,
            "pattern": "long",
            "total": len(questions),
            "submitted": submitted,
            "unanswered": len(questions) - submitted,
            "status": "Submitted — awaiting descriptive evaluation"
        }

    record = {
        "exam_id": exam.get("exam_id"),
        "email": session["user_email"],
        "pattern": exam["pattern"],
        "submitted_at": current_timestamp(),
        "answers": answers,
        "exam_status": "Submitted",
        "violation_count": proctor_status["violation_count"],
        "violations": proctor_status["violations"],
        "result": result
    }

    if not save_exam_record(record):

        return jsonify({
            "success": False,
            "message": "Your submission could not be saved. Please try again."
        }), 500

    revoke_desktop_exam(exam)

    session.pop("exam", None)

    main.stop_proctoring()

    return jsonify(result)


# -----------------------------------------
# CANCEL EXAMINATION - MANUAL ONLY
# -----------------------------------------

@app.route("/api/cancel_exam", methods=["POST"])
def cancel_exam():

    if "user_email" not in session:

        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401

    exam = session.get("exam")

    if not exam:

        return jsonify({
            "success": False,
            "message": "No active examination found."
        }), 400

    data = request.get_json(silent=True) or {}

    if data.get("manual") is not True:

        return jsonify({
            "success": False,
            "message": "Only manual cancellation is enabled."
        }), 400

    status = get_combined_proctor_status(exam)

    result = {
        "success": True,
        "pattern": exam["pattern"],
        "status": "Cancelled",
        "violation_count": status["violation_count"],
        "max_violations": MAX_VIOLATIONS
    }

    record = {
        "exam_id": exam.get("exam_id"),
        "email": session["user_email"],
        "pattern": exam["pattern"],
        "submitted_at": current_timestamp(),
        "answers": {},
        "exam_status": "Cancelled",
        "cancellation_reason": "Manually cancelled by candidate",
        "violation_count": status["violation_count"],
        "violations": status["violations"],
        "result": result
    }

    if not save_exam_record(record):

        return jsonify({
            "success": False,
            "message": "Cancellation could not be saved."
        }), 500

    revoke_desktop_exam(exam)

    session.pop("exam", None)

    main.stop_proctoring()

    return jsonify(result)


# -----------------------------------------
# BROWSER HEARTBEAT
# -----------------------------------------

@app.route("/api/exam_heartbeat", methods=["POST"])
def exam_heartbeat():

    exam = session.get("exam")

    if not exam:

        return jsonify({
            "success": False
        }), 400

    exam_id = exam.get("exam_id")

    with desktop_lock:

        registry = desktop_exam_registry.get(exam_id)

        if registry:

            registry["last_heartbeat"] = time.time()

    return jsonify({
        "success": True
    })


# -----------------------------------------
# END EXAMINATION - ABANDONED
# -----------------------------------------

@app.route("/api/end_exam", methods=["POST"])
def end_exam():

    exam = session.get("exam")

    if not exam:

        return jsonify({
            "success": True,
            "message": "No active examination."
        })

    status = get_combined_proctor_status(exam)

    record = {
        "exam_id": exam.get("exam_id"),
        "email": session.get("user_email", ""),
        "pattern": exam.get("pattern", ""),
        "submitted_at": current_timestamp(),
        "answers": {},
        "exam_status": "Abandoned",
        "cancellation_reason": "Examination page closed before submission",
        "violation_count": status["violation_count"],
        "violations": status["violations"],
        "result": {
            "success": True,
            "status": "Abandoned",
            "violation_count": status["violation_count"]
        }
    }

    if not save_exam_record(record):

        return jsonify({
            "success": False,
            "message": "Could not save the abandoned examination."
        }), 500

    revoke_desktop_exam(exam)

    session.pop("exam", None)

    main.stop_proctoring()

    return jsonify({
        "success": True,
        "message": "Examination marked as abandoned."
    })


# -----------------------------------------
# DESKTOP HEARTBEAT WATCHDOG
# -----------------------------------------

def desktop_heartbeat_watchdog():

    while True:

        time.sleep(3)

        expired_exam_ids = []

        with desktop_lock:

            current_time = time.time()

            for exam_id, registry in list(
                desktop_exam_registry.items()
            ):

                last_heartbeat = registry.get(
                    "last_heartbeat",
                    current_time
                )

                if current_time - last_heartbeat > HEARTBEAT_TIMEOUT:

                    expired_exam_ids.append(exam_id)

        for exam_id in expired_exam_ids:

            with desktop_lock:

                registry = desktop_exam_registry.pop(
                    exam_id,
                    None
                )

                if not registry:
                    continue

                desktop_token_index.pop(
                    registry.get("token"),
                    None
                )

            try:

                if os.path.exists(DESKTOP_TOKEN_PATH):

                    with open(
                        DESKTOP_TOKEN_PATH,
                        "r",
                        encoding="utf-8"
                    ) as token_file:

                        token_data = json.load(token_file)

                    if token_data.get("exam_id") == exam_id:

                        os.remove(DESKTOP_TOKEN_PATH)

            except (OSError, json.JSONDecodeError):

                app.logger.warning(
                    "Could not remove expired desktop token."
                )

            ai_status = main.get_proctoring_status()

            ai_violations = ai_status.get(
                "violations",
                []
            )

            desktop_violations = [
                {
                    "source": "Desktop",
                    "reason": event["reason"],
                    "application": event["application"],
                    "time": event["time"]
                }
                for event in registry.get("events", [])
            ]

            all_violations = (
                list(ai_violations) +
                desktop_violations
            )

            save_violations_to_database(
                exam_id,
                registry,
                ai_violations,
                desktop_violations
            )

            abandoned_record = {
                "exam_id": exam_id,
                "email": registry.get("email", ""),
                "pattern": registry.get("pattern", ""),
                "submitted_at": current_timestamp(),
                "answers": {},
                "exam_status": "Abandoned",
                "cancellation_reason": "Browser heartbeat expired",
                "violation_count": (
                    ai_status.get("violation_count", 0) +
                    len(desktop_violations)
                ),
                "violations": all_violations,
                "result": {
                    "success": True,
                    "status": "Abandoned"
                }
            }

            save_exam_record(abandoned_record)

            main.stop_proctoring()

            app.logger.info(
                "Desktop examination session expired: %s",
                exam_id
            )


# -----------------------------------------
# EXAMINATION HISTORY
# -----------------------------------------

@app.route("/api/history", methods=["GET"])
def api_history():

    if "user_email" not in session:

        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401

    try:

        with history_lock:

            if os.path.exists(HISTORY_PATH):

                with open(
                    HISTORY_PATH,
                    "r",
                    encoding="utf-8"
                ) as history_file:

                    records = json.load(history_file)

            else:

                records = []

            if not isinstance(records, list):
                records = []

    except (OSError, json.JSONDecodeError):

        app.logger.exception(
            "Could not read examination history."
        )

        records = []

    user_email = session["user_email"].strip().lower()

    mine = [
        record
        for record in records
        if isinstance(record, dict)
        and record.get("email", "").strip().lower() == user_email
    ]

    mine.sort(
        key=lambda record: record.get("submitted_at", ""),
        reverse=True
    )

    return jsonify({
        "success": True,
        "history": mine
    })


# -----------------------------------------
# CLEAR EXAM HISTORY AND RESULT HISTORY
# -----------------------------------------

@app.route("/api/clear-history", methods=["POST"])
def clear_history():

    if "user_email" not in session:

        return jsonify({
            "success": False,
            "message": "Please log in first."
        }), 401

    data = request.get_json(silent=True) or {}

    clear_type = data.get("type")

    if clear_type not in ["history", "results"]:

        return jsonify({
            "success": False,
            "message": "Invalid clear request."
        }), 400

    user_email = session["user_email"].strip().lower()

    try:

        with history_lock:

            if os.path.exists(HISTORY_PATH):

                with open(
                    HISTORY_PATH,
                    "r",
                    encoding="utf-8"
                ) as history_file:

                    records = json.load(history_file)

            else:

                records = []

            if not isinstance(records, list):

                return jsonify({
                    "success": False,
                    "message": "Invalid history file format."
                }), 500

            if clear_type == "history":

                records = [
                    record
                    for record in records
                    if not isinstance(record, dict)
                    or record.get("email", "").strip().lower() != user_email
                ]

                message = (
                    "Your exam history has been cleared successfully."
                )

            else:

                updated_records = []

                for record in records:

                    if not isinstance(record, dict):

                        updated_records.append(record)
                        continue

                    if (
                        record.get("email", "").strip().lower()
                        == user_email
                    ):

                        record = record.copy()
                        record.pop("result", None)

                    updated_records.append(record)

                records = updated_records

                message = (
                    "Your result history has been cleared successfully."
                )

            temporary_path = HISTORY_PATH + ".tmp"

            with open(
                temporary_path,
                "w",
                encoding="utf-8"
            ) as history_file:

                json.dump(
                    records,
                    history_file,
                    indent=2
                )

            os.replace(
                temporary_path,
                HISTORY_PATH
            )

        return jsonify({
            "success": True,
            "message": message
        })

    except (OSError, json.JSONDecodeError):

        app.logger.exception(
            "Could not clear examination history."
        )

        return jsonify({
            "success": False,
            "message": "Unable to clear records. Please try again."
        }), 500


# -----------------------------------------
# STUDENT PROFILE
# -----------------------------------------

@app.route("/api/profile", methods=["GET", "POST"])
def api_profile():

    if "user_email" not in session:

        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401

    email = session["user_email"]

    if request.method == "GET":

        try:

            profile = get_profile_details(email)

            if not profile:

                return jsonify({
                    "success": False,
                    "message": "Profile not found."
                }), 404

            return jsonify({
                "success": True,
                "email": profile["email"],
                "name": profile["username"]
            })

        except Exception:

            app.logger.exception(
                "Could not load student profile."
            )

            return jsonify({
                "success": False,
                "message": "Could not load profile."
            }), 500

    data = request.get_json(silent=True) or {}

    username = str(
        data.get("username", "")
    ).strip()

    if not username or len(username) > 100:

        return jsonify({
            "success": False,
            "message": "Enter a valid username (1–100 characters)."
        }), 400

    try:

        updated = update_profile_username(
            email,
            username
        )

        if not updated:

            return jsonify({
                "success": False,
                "message": "Profile could not be updated."
            }), 400

        session["username"] = username
        session.modified = True

        return jsonify({
            "success": True,
            "message": "Profile updated successfully.",
            "username": username
        })

    except Exception:

        app.logger.exception(
            "Could not update student profile."
        )

        return jsonify({
            "success": False,
            "message": "Could not update profile."
        }), 500


# -----------------------------------------
# CHANGE ACCOUNT PASSWORD
# -----------------------------------------

@app.route("/api/change-password", methods=["POST"])
def change_password():

    if "user_email" not in session:

        return jsonify({
            "success": False,
            "message": "Please sign in again."
        }), 401

    data = request.get_json(silent=True) or {}

    current_password = data.get(
        "current_password",
        ""
    )

    new_password = data.get(
        "new_password",
        ""
    )

    confirm_password = data.get(
        "confirm_password",
        ""
    )

    if (
        not isinstance(current_password, str)
        or not isinstance(new_password, str)
        or not isinstance(confirm_password, str)
        or not current_password
        or not new_password
        or not confirm_password
    ):

        return jsonify({
            "success": False,
            "message": "Please complete all password fields."
        }), 400

    if len(new_password) < 8:

        return jsonify({
            "success": False,
            "message": "New password must contain at least 8 characters."
        }), 400

    if new_password != confirm_password:

        return jsonify({
            "success": False,
            "message": "New password and confirm password do not match."
        }), 400

    if current_password == new_password:

        return jsonify({
            "success": False,
            "message": "Your new password must be different from your current password."
        }), 400

    email = session["user_email"]

    try:

        valid_password = verify_current_password(
            email,
            current_password
        )

        if not valid_password:

            return jsonify({
                "success": False,
                "message": "Your current password is incorrect."
            }), 401

        updated = update_account_password(
            email,
            new_password
        )

        if not updated:

            return jsonify({
                "success": False,
                "message": "Unable to update your password."
            }), 500

        return jsonify({
            "success": True,
            "message": "Your password has been changed successfully."
        })

    except Exception:

        app.logger.exception(
            "Password change error."
        )

        return jsonify({
            "success": False,
            "message": "Something went wrong while changing your password."
        }), 500


# -----------------------------------------
# WEBCAM VIDEO FEED
# -----------------------------------------

@app.route("/video_feed")
def video_feed():

    if "user_email" not in session:
        return ("", 401)

    if not session.get("exam"):
        return ("", 403)

    return Response(
        main.proctoringAlgo(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


# -----------------------------------------
# STOP CAMERA
# -----------------------------------------

@app.route("/stop_camera")
def stop_camera():

    try:

        main.stop_proctoring()

    except Exception as exc:

        app.logger.warning(
            "Camera stop issue: %s",
            exc
        )

    return jsonify({
        "success": True
    })


# -----------------------------------------
# RUN FLASK SERVER
# -----------------------------------------

if __name__ == "__main__":

    watchdog_thread = threading.Thread(
        target=desktop_heartbeat_watchdog,
        daemon=True
    )

    watchdog_thread.start()

    print("\nREGISTERED FLASK ROUTES:")

    for rule in app.url_map.iter_rules():
        print(rule, rule.methods)

    print("\nStarting the Python Flask Server.....")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
        threaded=True,
        use_reloader=False
    )