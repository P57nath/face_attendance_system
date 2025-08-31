import cv2

PIPELINE = (
    "libcamerasrc ! "
    "video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
    "videoconvert ! appsink"
)

cap = cv2.VideoCapture(PIPELINE, cv2.CAP_GSTREAMER)
print("opened:", cap.isOpened())

if cap.isOpened():
    ret, frame = cap.read()
    print("frame:", ret, "shape:" if ret else None, frame.shape if ret else None)
cap.release()
