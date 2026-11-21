
import cv2
import dlib

from pathlib import Path
from imutils import face_utils


MODEL_PATH = (
    Path(__file__).resolve().parent /
    "shape_predictor_model" /
    "shape_predictor_68_face_landmarks.dat"
)

if not MODEL_PATH.exists():
    raise FileNotFoundError(
        f"Facial landmark model not found: {MODEL_PATH}"
    )

shapePredictor = dlib.shape_predictor(str(MODEL_PATH))

faceDetector = dlib.get_frontal_face_detector()


def detectFace(frame):

    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    faces = faceDetector(gray, 0)

    faceCount = len(faces)

    for face in faces:

        x = max(0, face.left())
        y = max(0, face.top())

        w = min(frame.shape[1] - x, face.width())
        h = min(frame.shape[0] - y, face.height())

        if w <= 0 or h <= 0:
            continue

        # Top-left corner

        cv2.line(
            frame,
            (x, y),
            (x + 20, y),
            (0, 255, 255),
            2
        )

        cv2.line(
            frame,
            (x, y),
            (x, y + 20),
            (0, 255, 255),
            2
        )

        # Top-right corner

        cv2.line(
            frame,
            (x + w, y),
            (x + w - 20, y),
            (0, 255, 255),
            2
        )

        cv2.line(
            frame,
            (x + w, y),
            (x + w, y + 20),
            (0, 255, 255),
            2
        )

        # Bottom-left corner

        cv2.line(
            frame,
            (x, y + h),
            (x + 20, y + h),
            (0, 255, 255),
            2
        )

        cv2.line(
            frame,
            (x, y + h),
            (x, y + h - 20),
            (0, 255, 255),
            2
        )

        # Bottom-right corner

        cv2.line(
            frame,
            (x + w, y + h),
            (x + w - 20, y + h),
            (0, 255, 255),
            2
        )

        cv2.line(
            frame,
            (x + w, y + h),
            (x + w, y + h - 20),
            (0, 255, 255),
            2
        )

        # Facial landmarks

        facialLandmarks = shapePredictor(
            gray,
            face
        )

        facialLandmarks = face_utils.shape_to_np(
            facialLandmarks
        )

        for (a, b) in facialLandmarks:

            cv2.circle(
                frame,
                (a, b),
                2,
                (255, 255, 0),
                -1
            )

    return faceCount, faces


def analyze_face_quality(frame, faces):

    height, width = frame.shape[:2]

    if not faces:

        return {
            "blurry": False,
            "poor_lighting": False,
            "face_too_small": False,
            "sharpness": 0.0,
            "brightness": 0.0
        }

    face = faces[0]

    x1 = max(0, face.left())
    y1 = max(0, face.top())

    x2 = min(width, face.right())
    y2 = min(height, face.bottom())

    face_width = x2 - x1
    face_height = y2 - y1

    if face_width <= 0 or face_height <= 0:

        return {
            "blurry": True,
            "poor_lighting": True,
            "face_too_small": True,
            "sharpness": 0.0,
            "brightness": 0.0
        }

    face_roi = frame[y1:y2, x1:x2]

    gray_face = cv2.cvtColor(
        face_roi,
        cv2.COLOR_BGR2GRAY
    )

    # Face sharpness

    sharpness = cv2.Laplacian(
        gray_face,
        cv2.CV_64F
    ).var()

    # Face brightness

    brightness = float(
        gray_face.mean()
    )

    # Conservative thresholds.
    # These may need calibration for different webcams.

    blurry = sharpness < 35

    poor_lighting = (
        brightness < 45 or
        brightness > 220
    )

    face_too_small = (
        face_width < 90 or
        face_height < 90
    )

    return {
        "blurry": blurry,
        "poor_lighting": poor_lighting,
        "face_too_small": face_too_small,
        "sharpness": float(sharpness),
        "brightness": brightness
    }
