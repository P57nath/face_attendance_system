import cv2, os, csv, time

# --- settings ---
THRESH = 65                 # 60–90 typical; higher = stricter
LOG_TO_CSV = True           # write recognized events to CSV
CSV_PATH = "recognitions.csv"
CASCADE_PATH = os.path.join("cascades", "haarcascade_frontalface_default.xml")
PIPELINE = ("libcamerasrc ! video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
            "videoconvert ! appsink")
# ---------------

# Load cascade
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
assert not face_cascade.empty(), f"Failed to load cascade at {CASCADE_PATH}"

# Load recognizer + labels
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("models/lbph.yml")
labels = {int(i): n for i, n in (l.strip().split(",", 1) for l in open("models/labels.txt"))}

# Camera
cap = cv2.VideoCapture(PIPELINE, cv2.CAP_GSTREAMER)
assert cap.isOpened(), "Camera not available"

# CSV
csv_file = None
csv_writer = None
if LOG_TO_CSV:
    newfile = not os.path.exists(CSV_PATH)
    csv_file = open(CSV_PATH, "a", newline="")
    csv_writer = csv.writer(csv_file)
    if newfile:
        csv_writer.writerow(["timestamp", "name", "score"])

cv2.namedWindow("Recognize", cv2.WINDOW_AUTOSIZE)
print("Controls: [q]=quit")

try:
    while True:
        ok, frame_rgb = cap.read()
        if not ok:
            continue
        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(80,80))
        for (x,y,w,h) in faces:
            face = cv2.resize(gray[y:y+h, x:x+w], (200,200))
            label_id, dist = recognizer.predict(face)
            score = max(0, min(100, 100 - dist))  # friendlier 0..100
            name = labels.get(label_id, "Unknown")
            display = name if score >= THRESH else "Unknown"

            # draw
            cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)
            cv2.putText(frame, f"{display} ({score:.0f})", (x, y-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

            # log recognized (only if above threshold)
            if LOG_TO_CSV and display != "Unknown":
                csv_writer.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), display, f"{score:.0f}"])
                csv_file.flush()

        cv2.imshow("Recognize", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()
    if csv_file: csv_file.close()
