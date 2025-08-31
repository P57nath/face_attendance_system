import cv2, os

person_name = "22_46180_1Meraz"  # change as needed
out_dir = os.path.join("dataset", person_name)
os.makedirs(out_dir, exist_ok=True)

CASCADE_PATH = os.path.join(os.path.dirname(__file__), "cascades",
                            "haarcascade_frontalface_default.xml")
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
assert not face_cascade.empty(), "Failed to load Haar cascade"

PIPELINE = ("libcamerasrc ! video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
            "videoconvert ! appsink")
cap = cv2.VideoCapture(PIPELINE, cv2.CAP_GSTREAMER)
assert cap.isOpened(), "Camera not available"

count, target = 0, 60
print("Capturing face samples. Press 'q' to quit.")
while count < target:
    ret, frame = cap.read()
    if not ret: continue
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(80,80))
    for (x,y,w,h) in faces:
        face = cv2.resize(gray[y:y+h, x:x+w], (200,200))
        cv2.imwrite(os.path.join(out_dir, f"{person_name}_{count:03d}.png"), face)
        count += 1
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
print("Saved:", out_dir)

