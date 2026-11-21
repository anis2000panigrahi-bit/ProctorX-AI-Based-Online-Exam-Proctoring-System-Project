import cv2
import dlib
import numpy as np

from pathlib import Path


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


# 3D model points

model_points = np.array([
    (0.0, 0.0, 0.0),
    (0.0, -330.0, -65.0),
    (-255.0, 170.0, -135.0),
    (225.0, 170.0, -135.0),
    (-150.0, -150.0, -125.0),
    (150.0, -150.0, -125.0)
], dtype=np.float64)


def get_camera_matrix(img):

    height, width = img.shape[:2]

    focal_length = width

    center = (
        width / 2,
        height / 2
    )

    camera_matrix = np.array(
        [
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ],
        dtype=np.float64
    )

    return camera_matrix


def head_pose_detection(faces, img):

    font = cv2.FONT_HERSHEY_PLAIN

    if not faces:

        return "No face detected"

    for face in faces:

        marks = shapePredictor(
            img,
            face
        )

        image_points = np.array([
            [marks.part(30).x, marks.part(30).y],
            [marks.part(8).x, marks.part(8).y],
            [marks.part(36).x, marks.part(36).y],
            [marks.part(45).x, marks.part(45).y],
            [marks.part(48).x, marks.part(48).y],
            [marks.part(54).x, marks.part(54).y]
        ], dtype=np.float64)

        camera_matrix = get_camera_matrix(img)

        dist_coeffs = np.zeros(
            (4, 1),
            dtype=np.float64
        )

        success, rotation_vector, translation_vector = cv2.solvePnP(
            model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:

            return "Head pose unavailable"

        rotation_matrix, _ = cv2.Rodrigues(
            rotation_vector
        )

        angles = cv2.RQDecomp3x3(
            rotation_matrix
        )[0]

        pitch = float(angles[0])

        yaw = float(angles[1])

        # Display estimated angles

        cv2.putText(
            img,
            f"Pitch: {pitch:.1f}",
            (50, 150),
            font,
            1.5,
            (255, 255, 128),
            2
        )

        cv2.putText(
            img,
            f"Yaw: {yaw:.1f}",
            (50, 180),
            font,
            1.5,
            (255, 255, 128),
            2
        )

        # Head movement thresholds

        if pitch >= 25:

            status = "Head Down"

        elif pitch <= -25:

            status = "Head Up"

        elif yaw >= 25:

            status = "Head Right"

        elif yaw <= -25:

            status = "Head Left"

        else:

            status = "Normal"

        cv2.putText(
            img,
            status,
            (50, 50),
            font,
            2,
            (0, 255, 255),
            2
        )

        if status != "Normal":

            return status

        return -1

    return -1