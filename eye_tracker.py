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


def createMask(frame):

    height, width = frame.shape[:2]

    mask = np.zeros(
        (height, width),
        np.uint8
    )

    return mask


def extractEye(mask, region, frame):

    cv2.polylines(
        mask,
        region,
        True,
        255,
        2
    )

    cv2.fillPoly(
        mask,
        region,
        255
    )

    eyes = cv2.bitwise_and(
        frame,
        frame,
        mask=mask
    )

    return eyes


def eyeSegmentationAndReturnWhite(img, side):

    height, width = img.shape

    if side == 'left':

        img = img[
            0:height,
            0:int(width / 2)
        ]

    else:

        img = img[
            0:height,
            int(width / 2):width
        ]

    return cv2.countNonZero(img)


def gazeDetection(faces, frame):

    font = cv2.FONT_HERSHEY_DUPLEX

    thickness = 2

    TrialRation = 1.2

    result = ""

    leftEye = [36, 37, 38, 39, 40, 41]

    rightEye = [42, 43, 44, 45, 46, 47]

    height, width = frame.shape[:2]

    for face in faces:

        facialLandmarks = shapePredictor(
            frame,
            face
        )

        leftEyeRegion = np.array(
            [
                (
                    facialLandmarks.part(i).x,
                    facialLandmarks.part(i).y
                )
                for i in leftEye
            ],
            np.int32
        )

        rightEyeRegion = np.array(
            [
                (
                    facialLandmarks.part(i).x,
                    facialLandmarks.part(i).y
                )
                for i in rightEye
            ],
            np.int32
        )

        mask = createMask(frame)

        eyes = extractEye(
            mask,
            [
                leftEyeRegion,
                rightEyeRegion
            ],
            frame
        )

        # Left eye coordinates

        lmin_x = max(0, np.min(leftEyeRegion[:, 0]))
        lmax_x = min(width, np.max(leftEyeRegion[:, 0]))

        lmin_y = max(0, np.min(leftEyeRegion[:, 1]))
        lmax_y = min(height, np.max(leftEyeRegion[:, 1]))

        # Right eye coordinates

        rmin_x = max(0, np.min(rightEyeRegion[:, 0]))
        rmax_x = min(width, np.max(rightEyeRegion[:, 0]))

        rmin_y = max(0, np.min(rightEyeRegion[:, 1]))
        rmax_y = min(height, np.max(rightEyeRegion[:, 1]))

        left = eyes[
            lmin_y:lmax_y,
            lmin_x:lmax_x
        ]

        right = eyes[
            rmin_y:rmax_y,
            rmin_x:rmax_x
        ]

        if left.size == 0 or right.size == 0:

            result = "unknown"

            continue

        leftGrayEye = cv2.cvtColor(
            left,
            cv2.COLOR_BGR2GRAY
        )

        rightGrayEye = cv2.cvtColor(
            right,
            cv2.COLOR_BGR2GRAY
        )

        # Adaptive threshold

        if (
            leftGrayEye.shape[0] < 11 or
            leftGrayEye.shape[1] < 11 or
            rightGrayEye.shape[0] < 11 or
            rightGrayEye.shape[1] < 11
        ):

            result = "unknown"

            continue

        leftTh = cv2.adaptiveThreshold(
            leftGrayEye,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        rightTh = cv2.adaptiveThreshold(
            rightGrayEye,
            255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            11,
            2
        )

        leftSideOfLeftEye = eyeSegmentationAndReturnWhite(
            leftTh,
            'right'
        )

        rightSideOfLeftEye = eyeSegmentationAndReturnWhite(
            leftTh,
            'left'
        )

        leftSideOfRightEye = eyeSegmentationAndReturnWhite(
            rightTh,
            'right'
        )

        rightSideOfRightEye = eyeSegmentationAndReturnWhite(
            rightTh,
            'left'
        )

        if (
            rightSideOfRightEye >=
            TrialRation * leftSideOfRightEye
        ):

            result = "left"

        elif (
            leftSideOfLeftEye >=
            TrialRation * rightSideOfLeftEye
        ):

            result = "right"

        else:

            result = "center"

        cv2.putText(
            frame,
            result,
            (50, 110),
            font,
            1,
            (255, 0, 255),
            thickness
        )

    return result