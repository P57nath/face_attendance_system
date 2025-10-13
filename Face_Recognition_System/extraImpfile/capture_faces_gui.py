# capture_faces_gui.py
import cv2, os, time

person_name = "tasin"  # change if needed
out_dir = os.path.join("dataset", person_name)
os.makedirs(out_dir, exist_ok=True)

CASCADE_PATH = os.path.join(os.path.dirname(__file__), "cascades",
                            "haarcascade_frontalface_default.xml")
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
assert not face_cascade.empty(), f"Failed to load cascade at {CASCADE_PATH}"

# Camera via GStreamer (libcamera). We request RGB and convert to BGR for OpenCV display/saving.
PIPELINE = ("libcamerasrc ! video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
            "videoconvert ! appsink")
cap = cv2.VideoCapture(PIPELINE, cv2.CAP_GSTREAMER)
assert cap.isOpened(), "Camera not available"

# ---- SETTINGS ----
TARGET = 60                 # total images to save
AUTO_MODE = True            # True: auto-save on a timer when a face is seen; False: press 's' to save
MIN_INTERVAL = 0.7          # seconds between auto-saves (slows things down)
SAVE_FULL_FRAME_TOO = False # set True to also save the full color frame for reference
# -------------------

saved = 0
last_save = 0.0

cv2.namedWindow("Face Capture", cv2.WINDOW_AUTOSIZE)
print("Controls: [q]=quit  [s]=save (manual mode)")

while saved < TARGET:
    ok, frame_rgb = cap.read()
    if not ok:
        continue

    # Convert to BGR for OpenCV drawing & correct-color saving
    frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(80,80))

    # Draw detections
    for (x,y,w,h) in faces[:1]:  # just the first face
        cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)

    # HUD text
    cv2.putText(frame, f"{person_name}  saved:{saved}/{TARGET}",
                (10,25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30,220,30), 2)
    mode_text = "AUTO" if AUTO_MODE else "MANUAL: press 's' to save"
    cv2.putText(frame, mode_text, (10,50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)

    # Show preview
    cv2.imshow("Face Capture", frame)

    # Save logic
    now = time.time()
    want_save = False
    if len(faces) > 0:
        if AUTO_MODE and (now - last_save) >= MIN_INTERVAL:
            want_save = True

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    if not AUTO_MODE and key == ord('s') and len(faces) > 0:
        want_save = True

    if want_save and saved < TARGET:
        x,y,w,h = faces[0]
        # Color face crop at 200x200
        face_color = cv2.resize(frame[y:y+h, x:x+w], (200,200))
        fname = os.path.join(out_dir, f"{person_name}_{saved:03d}.png")
        cv2.imwrite(fname, face_color)
        if SAVE_FULL_FRAME_TOO:
            full_name = os.path.join(out_dir, f"{person_name}_{saved:03d}_full.png")
            cv2.imwrite(full_name, frame)
        saved += 1
        last_save = now

cap.release()
cv2.destroyAllWindows()
print(f"Done. Saved {saved} images to {out_dir}")
