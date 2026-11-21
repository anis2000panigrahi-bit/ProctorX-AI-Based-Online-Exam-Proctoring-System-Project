import cv2
import numpy as np
from pathlib import Path
from threading import Lock


BASE_DIR = Path(__file__).resolve().parent

WEIGHTS_PATH = (
    BASE_DIR
    / "object_detection_model"
    / "weights"
    / "yolov3-tiny.weights"
)

CONFIG_PATH = (
    BASE_DIR
    / "object_detection_model"
    / "config"
    / "yolov3-tiny.cfg"
)

LABELS_PATH = (
    BASE_DIR
    / "object_detection_model"
    / "objectLabels"
    / "coco.names"
)

CONFIDENCE_THRESHOLD = 0.50
NMS_THRESHOLD = 0.40
INPUT_SIZE = (416, 416)

if not WEIGHTS_PATH.exists():
    raise FileNotFoundError(f"YOLO weights not found: {WEIGHTS_PATH}")

if not CONFIG_PATH.exists():
    raise FileNotFoundError(f"YOLO configuration not found: {CONFIG_PATH}")

if not LABELS_PATH.exists():
    raise FileNotFoundError(f"COCO labels not found: {LABELS_PATH}")


with open(LABELS_PATH, "r", encoding="utf-8") as file:
    label_classes = [name.strip() for name in file.readlines()]

net = cv2.dnn.readNet(
    str(WEIGHTS_PATH),
    str(CONFIG_PATH)
)

layer_names = net.getLayerNames()

output_layers = [
    layer_names[int(layer) - 1]
    for layer in np.array(net.getUnconnectedOutLayers()).flatten()
]

colors = np.random.default_rng(42).integers(
    0, 255,
    size=(len(label_classes), 3)
)

detection_lock = Lock()


def detectObject(frame):

    labels_this_frame = []

    if frame is None or frame.size == 0:
        return labels_this_frame

    height, width = frame.shape[:2]

    blob = cv2.dnn.blobFromImage(
        frame,
        scalefactor=1 / 255.0,
        size=INPUT_SIZE,
        mean=(0, 0, 0),
        swapRB=True,
        crop=False
    )

    with detection_lock:

        net.setInput(blob)
        outs = net.forward(output_layers)

    boxes = []
    confidences = []
    class_ids = []

    for output in outs:

        for detection in output:

            scores = detection[5:]

            if len(scores) == 0:
                continue

            class_id = int(np.argmax(scores))

            confidence = float(detection[4] * scores[class_id])

            if confidence < CONFIDENCE_THRESHOLD:
                continue

            center_x = int(detection[0] * width)
            center_y = int(detection[1] * height)

            box_width = int(detection[2] * width)
            box_height = int(detection[3] * height)

            x = max(0, int(center_x - box_width / 2))
            y = max(0, int(center_y - box_height / 2))

            box_width = min(box_width, width - x)
            box_height = min(box_height, height - y)

            if box_width <= 0 or box_height <= 0:
                continue

            boxes.append([
                x,
                y,
                box_width,
                box_height
            ])

            confidences.append(confidence)
            class_ids.append(class_id)

    if not boxes:
        return labels_this_frame

    indexes = cv2.dnn.NMSBoxes(
        boxes,
        confidences,
        CONFIDENCE_THRESHOLD,
        NMS_THRESHOLD
    )

    if len(indexes) == 0:
        return labels_this_frame

    indexes = np.array(indexes).flatten()

    for i in indexes:

        x, y, box_width, box_height = boxes[i]

        class_id = class_ids[i]
        confidence = confidences[i]

        if class_id >= len(label_classes):
            continue

        label = label_classes[class_id]

        color = tuple(
            int(value)
            for value in colors[class_id]
        )

        cv2.rectangle(
            frame,
            (x, y),
            (x + box_width, y + box_height),
            color,
            2
        )

        display_text = f"{label}: {confidence * 100:.1f}%"

        cv2.putText(
            frame,
            display_text,
            (x, max(y - 10, 20)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2
        )

        labels_this_frame.append(
            (label, confidence)
        )

    return labels_this_frame
