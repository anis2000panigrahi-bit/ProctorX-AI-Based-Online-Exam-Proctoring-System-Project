
import os
import json
import time
import urllib.request
import urllib.error

import psutil
import win32gui
import win32process


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TOKEN_FILE = os.path.join(
    BASE_DIR,
    ".desktop_monitor_token.json"
)

PROHIBITED_APPS = {
    "notepad.exe": "Notepad"
}

PROHIBITED_WINDOW_TITLES = {
    "calculator": "Calculator"
}


def load_exam_token():
    if not os.path.exists(TOKEN_FILE):
        return None

    try:
        with open(
            TOKEN_FILE,
            "r",
            encoding="utf-8"
        ) as token_file:
            data = json.load(token_file)

        if not data.get("token"):
            return None

        if not data.get("server_url"):
            return None

        return data

    except (OSError, json.JSONDecodeError):
        return None


def get_active_application():
    try:
        window_handle = win32gui.GetForegroundWindow()

        if not window_handle:
            return None

        window_title = win32gui.GetWindowText(
            window_handle
        )

        _, process_id = win32process.GetWindowThreadProcessId(
            window_handle
        )

        try:
            process_name = psutil.Process(
                process_id
            ).name()

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied
        ):
            process_name = "Unknown"

        return {
            "window_title": window_title,
            "process_name": process_name
        }

    except Exception as error:
        print("Detection error:", error)
        return None


def get_prohibited_application(application):
    process_name = application[
        "process_name"
    ].lower()

    window_title = application[
        "window_title"
    ].lower().strip()

    if process_name in PROHIBITED_APPS:
        return PROHIBITED_APPS[process_name]

    if window_title in PROHIBITED_WINDOW_TITLES:
        return PROHIBITED_WINDOW_TITLES[window_title]

    return None


def send_desktop_event(token_data, application_name):
    url = (
        token_data["server_url"].rstrip("/")
        + "/api/desktop_event"
    )

    payload = json.dumps({
        "application": application_name
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": (
                "Bearer " + token_data["token"]
            )
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=5
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

            if result.get("success"):
                if not result.get("duplicate"):
                    print(
                        "[SENT] Desktop violation:",
                        application_name
                    )

                return True

            print(
                "[SERVER WARNING]",
                result.get("message", "Unknown error")
            )

            return False

    except urllib.error.HTTPError as error:
        if error.code == 401:
            print(
                "Exam token expired. Stop the desktop monitor."
            )
            return False

        print(
            "Server HTTP error:",
            error.code
        )

    except urllib.error.URLError:
        print(
            "Could not connect to Flask server."
        )

    except Exception as error:
        print(
            "Event sending error:",
            error
        )

    return False


def monitor_applications():
    print("\nProctorX Desktop Monitor Started")

    token_data = load_exam_token()

    if not token_data:
        print(
            "No active examination token found."
        )
        print(
            "Start an examination in the browser first."
        )
        return

    print(
        "Connected to the local examination session."
    )

    print(
        "Monitoring Notepad and Calculator."
    )

    print(
        "Press Ctrl+C to stop.\n"
    )

    previous_application = None
    currently_prohibited = None

    try:
        while True:
            if not os.path.exists(TOKEN_FILE):
                print(
                    "\nExamination ended. Monitor stopped."
                )
                break

            application = get_active_application()

            if application:
                process_name = application[
                    "process_name"
                ]

                if process_name != previous_application:
                    print(
                        "Active application:",
                        process_name
                    )

                    previous_application = process_name

                prohibited_name = (
                    get_prohibited_application(application)
                )

                if prohibited_name:
                    if prohibited_name != currently_prohibited:
                        print(
                            "\nWARNING: Prohibited application:",
                            prohibited_name
                        )

                        send_desktop_event(
                            token_data,
                            prohibited_name
                        )

                        currently_prohibited = prohibited_name

                else:
                    currently_prohibited = None

            time.sleep(1)

    except KeyboardInterrupt:
        print(
            "\nProctorX Desktop Monitor Stopped."
        )


if __name__ == "__main__":
    monitor_applications()
