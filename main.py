import cv2
import time
import winsound
import threading

from pathlib import Path
from datetime import datetime

from facial_detections import detectFace, analyze_face_quality
from blink_detection import isBlinking
from mouth_tracking import mouthTrack
from object_detection import detectObject
from eye_tracker import gazeDetection
from head_pose_estimation import head_pose_detection


data_record = []

running = False
cam = None

MAX_VIOLATIONS = 10
VIOLATION_COOLDOWN = 60

NO_FACE_FRAMES = 120
MULTIPLE_FACE_FRAMES = 90
GAZE_FRAMES = 120
HEAD_FRAMES = 150

BLUR_FRAMES = 90
LIGHTING_FRAMES = 90
FACE_DISTANCE_FRAMES = 90

PHONE_FRAMES = 90
BOOK_FRAMES = 90
NOTEBOOK_FRAMES = 90
BOTTLE_FRAMES = 90
GLASS_FRAMES = 90

PHONE_CONFIDENCE = 0.75
BOOK_CONFIDENCE = 0.65
NOTEBOOK_CONFIDENCE = 0.65
BOTTLE_CONFIDENCE = 0.65
GLASS_CONFIDENCE = 0.65

frequency = 2500
duration = 150

violation_count = 0
violation_events = []
last_violation_time = {}
condition_frames = {}

latest_frame = None
frame_number = 0

proctoring_lock = threading.Lock()
camera_lock = threading.Lock()
frame_lock = threading.Lock()
worker_lock = threading.Lock()

stop_event = threading.Event()

capture_thread = None
detection_thread = None


def faceCount_detection(faceCount):

    if faceCount > 1:
        return "Multiple faces detected."

    elif faceCount == 0:
        return "No face detected."

    return "Face detected properly."


def register_violation(reason, details=None):

    global violation_count

    current_time = time.time()

    with proctoring_lock:

        previous_time = last_violation_time.get(reason, 0)

        if current_time - previous_time < VIOLATION_COOLDOWN:
            return

        last_violation_time[reason] = current_time

        violation_count += 1

        event = {
            "number": violation_count,
            "reason": reason,
            "time": datetime.now().strftime("%H:%M:%S")
        }

        if details:
            event.update(details)

        violation_events.append(event)

        data_record.append([
            event["time"],
            "VIOLATION",
            reason,
            violation_count,
            details or {}
        ])

        print(
            f"VIOLATION {violation_count}: {reason}"
        )

        try:
            winsound.Beep(frequency, duration)
        except Exception:
            pass


def get_proctoring_status():

    with proctoring_lock:

        return {
            "violation_count": violation_count,
            "max_violations": MAX_VIOLATIONS,
            "violations": list(violation_events),
            "cancelled": False,
            "limit_reached": violation_count >= MAX_VIOLATIONS
        }


def reset_proctoring():

    global violation_count
    global violation_events
    global last_violation_time
    global condition_frames
    global running
    global latest_frame
    global frame_number

    stop_proctoring()

    with proctoring_lock:

        violation_count = 0
        violation_events = []
        last_violation_time = {}
        condition_frames = {}

        data_record.clear()

    with frame_lock:

        latest_frame = None
        frame_number = 0

    running = True
    stop_event.clear()


def check_sustained_condition(
    condition,
    detected,
    reason,
    required_frames
):

    if detected:

        condition_frames[condition] = (
            condition_frames.get(condition, 0) + 1
        )

        if condition_frames[condition] >= required_frames:

            register_violation(reason)

            condition_frames[condition] = 0

    else:

        condition_frames[condition] = 0


def get_camera():

    global cam

    with camera_lock:

        if cam is None or not cam.isOpened():

            cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)

            if not cam.isOpened():

                cam.release()

                cam = cv2.VideoCapture(0)

            if not cam.isOpened():

                cam.release()
                cam = None

                raise RuntimeError(
                    "Unable to open webcam. Check camera connection."
                )

            cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cam.set(cv2.CAP_PROP_FPS, 30)
            cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        return cam


def normalize_object_results(objects):

    results = []

    if not objects:
        return results

    for item in objects:

        if isinstance(item, (tuple, list)):

            label = str(item[0]).strip().lower()

            confidence = 1.0

            if len(item) > 1:

                try:
                    confidence = float(item[1])
                except (ValueError, TypeError):
                    confidence = 1.0

        else:

            label = str(item).strip().lower()
            confidence = 1.0

        results.append((label, confidence))

    return results


def process_object_detections(objects):

    object_rules = {
        "mobile_phone": {
            "labels": ["cell phone", "mobile phone", "phone"],
            "confidence": PHONE_CONFIDENCE,
            "frames": PHONE_FRAMES,
            "reason": "Mobile phone continuously detected."
        },

        "book": {
            "labels": ["book"],
            "confidence": BOOK_CONFIDENCE,
            "frames": BOOK_FRAMES,
            "reason": "Book detected near the candidate."
        },

        "notebook": {
            "labels": ["book"],
            "confidence": NOTEBOOK_CONFIDENCE,
            "frames": NOTEBOOK_FRAMES,
            "reason": "Possible notebook detected near the candidate."
        },

        "water_bottle": {
            "labels": ["bottle"],
            "confidence": BOTTLE_CONFIDENCE,
            "frames": BOTTLE_FRAMES,
            "reason": "Bottle detected near the candidate."
        },

        "glass": {
            "labels": ["wine glass", "cup"],
            "confidence": GLASS_CONFIDENCE,
            "frames": GLASS_FRAMES,
            "reason": "Glass or cup detected near the candidate."
        }
    }

    normalized_objects = normalize_object_results(objects)

    detected_objects = {}

    for label, confidence in normalized_objects:

        for object_key, rule in object_rules.items():

            if (
                label in rule["labels"]
                and confidence >= rule["confidence"]
            ):

                detected_objects[object_key] = max(
                    detected_objects.get(object_key, 0),
                    confidence
                )

    for object_key, rule in object_rules.items():

        confidence = detected_objects.get(object_key)

        detected = confidence is not None

        condition = f"object_{object_key}"

        if detected:

            reason = rule["reason"]

            condition_frames[condition] = (
                condition_frames.get(condition, 0) + 1
            )

            if condition_frames[condition] >= rule["frames"]:

                register_violation(
                    reason,
                    {
                        "object": object_key,
                        "confidence": round(confidence, 3)
                    }
                )

                condition_frames[condition] = 0

        else:

            condition_frames[condition] = 0


def camera_capture_worker():

    global cam
    global latest_frame
    global frame_number

    camera = None

    try:

        camera = get_camera()

        print("Camera started successfully.")

        while not stop_event.is_set() and running:

            ret, frame = camera.read()

            if not ret or frame is None:

                time.sleep(0.05)
                continue

            frame = cv2.resize(
                frame,
                (640, 480)
            )

            with frame_lock:

                latest_frame = frame.copy()
                frame_number += 1

    except Exception as error:

        print("Camera capture error:", error)

    finally:

        with camera_lock:

            if cam is camera and cam is not None:

                cam.release()
                cam = None

        print("Camera capture stopped.")


def process_detection(frame):

    current_time = datetime.now().strftime("%H:%M:%S")

    record = [current_time]

    try:

        faceCount, faces = detectFace(frame)

        face_remark = faceCount_detection(faceCount)

        record.append(face_remark)

        check_sustained_condition(
            "no_face",
            faceCount == 0,
            "Face not visible for an extended period.",
            NO_FACE_FRAMES
        )

        check_sustained_condition(
            "multiple_faces",
            faceCount > 1,
            "Multiple faces continuously detected.",
            MULTIPLE_FACE_FRAMES
        )

        object_results = detectObject(frame)

        record.append(
            f"Detected objects: {object_results}"
        )

        process_object_detections(object_results)

        if faceCount == 1:

            quality = analyze_face_quality(frame, faces)

            record.append(
                f"Face sharpness: {quality['sharpness']:.2f}"
            )

            record.append(
                f"Face brightness: {quality['brightness']:.2f}"
            )

            check_sustained_condition(
                "blurry_face",
                quality["blurry"],
                "Face is not clearly visible or appears blurry.",
                BLUR_FRAMES
            )

            check_sustained_condition(
                "poor_lighting",
                quality["poor_lighting"],
                "Poor lighting detected. Face visibility is reduced.",
                LIGHTING_FRAMES
            )

            check_sustained_condition(
                "face_too_small",
                quality["face_too_small"],
                "Face is too far from the camera.",
                FACE_DISTANCE_FRAMES
            )

            blinkStatus = isBlinking(faces, frame)

            if blinkStatus and len(blinkStatus) > 2:

                if blinkStatus[2] == "Blink":
                    record.append("Blink detected")

                record.append(
                    f"Blink status: {blinkStatus[2]}"
                )

            eyeStatus = gazeDetection(faces, frame)

            record.append(str(eyeStatus))

            gaze_text = str(eyeStatus).lower()

            unusual_gaze = (
                "left" in gaze_text or
                "right" in gaze_text
            )

            check_sustained_condition(
                "eye_gaze",
                unusual_gaze,
                "Prolonged unusual eye gaze detected.",
                GAZE_FRAMES
            )

            mouthStatus = mouthTrack(faces, frame)

            record.append(str(mouthStatus))

            headStatus = head_pose_detection(
                faces,
                frame
            )

            record.append(str(headStatus))

            head_text = str(headStatus).lower()

            unusual_head = any(
                direction in head_text
                for direction in [
                    "head up",
                    "head down",
                    "head left",
                    "head right"
                ]
            )

            check_sustained_condition(
                "head_pose",
                unusual_head,
                "Prolonged unusual head position detected.",
                HEAD_FRAMES
            )

        else:

            condition_frames["blurry_face"] = 0
            condition_frames["poor_lighting"] = 0
            condition_frames["face_too_small"] = 0

            condition_frames["eye_gaze"] = 0
            condition_frames["head_pose"] = 0

        with proctoring_lock:
            data_record.append(record)

    except Exception as detection_error:

        print(
            "Detection error:",
            detection_error
        )


def ai_detection_worker():

    last_processed_frame = -1

    print("AI detection worker started.")

    while not stop_event.is_set() and running:

        with frame_lock:

            if latest_frame is None:

                frame = None
                current_number = -1

            else:

                frame = latest_frame.copy()
                current_number = frame_number

        if frame is None:

            time.sleep(0.05)
            continue

        if current_number == last_processed_frame:

            time.sleep(0.01)
            continue

        last_processed_frame = current_number

        process_detection(frame)

    print("AI detection worker stopped.")


def start_proctoring_workers():

    global capture_thread
    global detection_thread

    with worker_lock:

        if not running:
            return

        if capture_thread is not None and capture_thread.is_alive():
            return

        stop_event.clear()

        capture_thread = threading.Thread(
            target=camera_capture_worker,
            daemon=True
        )

        detection_thread = threading.Thread(
            target=ai_detection_worker,
            daemon=True
        )

        capture_thread.start()
        detection_thread.start()


def proctoringAlgo():

    while not running:
        time.sleep(0.1)

    start_proctoring_workers()

    while running and not stop_event.is_set():

        with frame_lock:

            if latest_frame is None:
                frame = None

            else:
                frame = latest_frame.copy()

        if frame is None:

            time.sleep(0.05)
            continue

        success, buffer = cv2.imencode(
            ".jpg",
            frame,
            [cv2.IMWRITE_JPEG_QUALITY, 80]
        )

        if not success:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )

        time.sleep(0.03)


def generate_frames():

    return proctoringAlgo()


def main_app():

    with proctoring_lock:

        activityVal = "\n".join(
            map(str, data_record)
        )

    file_path = (
        Path(__file__).resolve().parent /
        "activity.txt"
    )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(activityVal)


def stop_proctoring():

    global running
    global cam

    running = False

    stop_event.set()

    with camera_lock:

        if cam is not None:

            cam.release()
            cam = None

    main_app()

    print("Proctoring stopped.")
