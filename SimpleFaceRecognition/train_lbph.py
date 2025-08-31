import cv2, os, numpy as np

data_root = "dataset"
people = sorted([d for d in os.listdir(data_root)
                 if os.path.isdir(os.path.join(data_root, d))])
if not people: raise SystemExit("No dataset found. Run capture first.")

if not hasattr(cv2, "face"):
    raise SystemExit("cv2.face missing. Install contrib: pip install opencv-contrib-python")

recognizer = cv2.face.LBPHFaceRecognizer_create(radius=1, neighbors=8, grid_x=8, grid_y=8)

X, y = [], []
for label, person in enumerate(people):
    folder = os.path.join(data_root, person)
    for f in os.listdir(folder):
        if f.lower().endswith((".png",".jpg",".jpeg")):
            img = cv2.imread(os.path.join(folder, f), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                X.append(img); y.append(label)

if not X: raise SystemExit("No images found in dataset.")
recognizer.train(X, np.array(y))

os.makedirs("models", exist_ok=True)
recognizer.write("models/lbph.yml")
with open("models/labels.txt","w") as f:
    for i, p in enumerate(people): f.write(f"{i},{p}\n")

print("Trained on:", people)
