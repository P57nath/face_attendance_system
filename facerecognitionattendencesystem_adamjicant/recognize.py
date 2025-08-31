import cv2

recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("models/lbph.yml")
labels = {int(i): n for i, n in (l.strip().split(",", 1) for l in open("models/labels.txt"))}

CASCADE_PATH = "cascades/haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

PIPELINE = ("libcamerasrc ! video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
            "videoconvert ! appsink")
cap = cv2.VideoCapture(PIPELINE, cv2.CAP_GSTREAMER)
assert cap.isOpened(), "Camera not available"

THRESH = 60  # 60–90 typical
while True:
    ok, frame = cap.read()
    if not ok: continue
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    for (x,y,w,h) in face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(80,80)):
        face = cv2.resize(gray[y:y+h, x:x+w], (200,200))
        label_id, dist = recognizer.predict(face)
        score = max(0, min(100, 100 - dist))
        name = labels.get(label_id, "Unknown")
        text = name if score >= THRESH else "Unknown"
        cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
        cv2.putText(frame,f"{text} ({score:.0f})",(x,y-10),
                    cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,255,0),2)
    cv2.imshow("Face Recognition", frame)
    if cv2.waitKey(1) & 0xFF == 'q': break
cap.release(); cv2.destroyAllWindows()
