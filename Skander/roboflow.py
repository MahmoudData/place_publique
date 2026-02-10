import cv2
import numpy as np
import csv
from datetime import datetime
from collections import defaultdict
import matplotlib.pyplot as plt
import os
import sys
import subprocess

from inference_sdk import InferenceHTTPClient

# ==============================
# CONFIGURATION GÉNÉRALE
# ==============================

ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
WORKSPACE_NAME = "detectedmove"
WORKFLOW_ID = "find-trucks-and-cars"

YOUTUBE_URL = "https://www.youtube.com/watch?v=z545k7Tcb5o"
FRAME_SKIP = 5  # 1 frame sur 5 envoyée à Roboflow

# ==============================
# OUTILS
# ==============================

def get_youtube_stream_url(youtube_url: str) -> str:
    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f",
        "best",
        "-g",
        youtube_url
    ]
    return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()


# ==============================
# CLIENT ROBOFLOW
# ==============================

client = InferenceHTTPClient(
    api_url="https://serverless.roboflow.com",
    api_key=ROBOFLOW_API_KEY
)

# ==============================
# IOU & TRACKING
# ==============================

def calculate_iou(box1, box2) -> float:
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2

    inter_xmin = max(x1_min, x2_min)
    inter_ymin = max(y1_min, y2_min)
    inter_xmax = min(x1_max, x2_max)
    inter_ymax = min(y1_max, y2_max)

    if inter_xmax <= inter_xmin or inter_ymax <= inter_ymin:
        return 0.0

    inter_area = (inter_xmax - inter_xmin) * (inter_ymax - inter_ymin)
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)

    return inter_area / float(area1 + area2 - inter_area)

def is_same_object(det1, det2, iou_threshold=0.5) -> bool:
    if det1["class"] != det2["class"]:
        return False
    return calculate_iou(det1["bbox"], det2["bbox"]) > iou_threshold

# ==============================
# CAPTURE + INFERENCE
# ==============================

def start_video_capture():
    print("🔄 Récupération du flux YouTube...")
    video_url = get_youtube_stream_url(YOUTUBE_URL)

    cap = cv2.VideoCapture(video_url, cv2.CAP_FFMPEG)

    if not cap.isOpened():
        print("❌ Impossible d’ouvrir le flux vidéo")
        return

    csv_filename = f"detections_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    csv_file = open(csv_filename, "w", newline="", encoding="utf-8")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow([
        "Frame", "Timestamp", "Classe", "Confiance",
        "X1", "Y1", "X2", "Y2"
    ])

    frame_count = 0
    previous_detections = []
    class_stats = defaultdict(lambda: {"count": 0, "total_conf": 0})
    all_confidences = []

    print("📡 Flux vidéo connecté — ESC pour quitter")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Fin ou perte du flux")
            break

        frame_count += 1
        frame = cv2.resize(frame, (640, 480))
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

        # Skip de frames pour limiter les appels API
        if frame_count % FRAME_SKIP != 0:
            cv2.imshow("Roboflow Detection", frame)
            if cv2.waitKey(1) == 27:
                break
            continue

        # Encodage JPEG pour Roboflow
        
        result = client.run_workflow(
            workspace_name=WORKSPACE_NAME,
            workflow_id=WORKFLOW_ID,
            images={"image":frame}
        )

        predictions = []
        for output in result.get("outputs", {}).values():
            if "predictions" in output:
                predictions = output["predictions"]
                break

        detections = []

        for pred in predictions:
            x = int(pred["x"])
            y = int(pred["y"])
            w = int(pred["width"])
            h = int(pred["height"])

            x1, y1 = x - w // 2, y - h // 2
            x2, y2 = x + w // 2, y + h // 2

            class_name = pred["class"]
            conf = float(pred["confidence"])

            det = {
                "class": class_name,
                "confidence": conf,
                "bbox": (x1, y1, x2, y2)
            }
            detections.append(det)

            class_stats[class_name]["count"] += 1
            class_stats[class_name]["total_conf"] += conf
            all_confidences.append(conf)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"{class_name} {conf:.2f}",
                (x1, y1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

        # Tracking simple + CSV
        for det in detections:
            if not any(is_same_object(det, prev) for prev in previous_detections):
                x1, y1, x2, y2 = det["bbox"]
                csv_writer.writerow([
                    frame_count, timestamp,
                    det["class"], f"{det['confidence']:.4f}",
                    x1, y1, x2, y2
                ])

        previous_detections = detections

        cv2.imshow("Roboflow Detection", frame)
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    csv_file.close()

    generate_graphs(all_confidences, class_stats)

# ==============================
# GRAPHIQUES
# ==============================

def generate_graphs(all_confidences, class_stats):
    if not all_confidences:
        print("ℹ️ Aucune détection, pas de graphique")
        return

    class_names = list(class_stats.keys())
    scores = [
        (class_stats[c]["total_conf"] / class_stats[c]["count"]) * 100
        for c in class_names
    ]

    plt.figure(figsize=(10, 5))
    plt.bar(class_names, scores)
    plt.ylabel("Confiance moyenne (%)")
    plt.title("Performance Roboflow par classe")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    start_video_capture()
