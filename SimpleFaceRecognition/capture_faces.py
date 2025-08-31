import os, time, re, cv2
from datetime import datetime
from dotenv import load_dotenv

# ---- DB driver (mysql-connector or PyMySQL) ----
try:
    import mysql.connector as _mysql_driver
    def DB_CONNECT(**cfg): return _mysql_driver.connect(**cfg)
except ImportError:
    import pymysql as _mysql_driver
    def DB_CONNECT(**cfg):
        return _mysql_driver.connect(
            host=cfg["host"], user=cfg["user"], password=cfg["password"],
            database=cfg["database"], autocommit=True, charset="utf8mb4")
# ------------------------------------------------

# ---- GUI (Tk) with image display ----
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ====== Config ======
DB_CFG = dict(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "facelogger"),
    password=os.getenv("DB_PASSWORD", "Prious1234"),
    database=os.getenv("DB_NAME", "facelog"),
)
WIDTH, HEIGHT, FPS = 640, 480, 30          # preview/capture size
TARGET_SAMPLES = 60                         # number of crops to save
MIN_INTERVAL   = 0.8                        # seconds between saves
SAVE_FULL_FRAME_TOO = False                 # set True to also save full frames
CASCADE_PATH = os.path.join(BASE_DIR, "cascades", "haarcascade_frontalface_default.xml")
DATASET_ROOT = os.path.join(BASE_DIR, "dataset")
os.makedirs(DATASET_ROOT, exist_ok=True)
# ====================

def ensure_students_table(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS students (
      student_id VARCHAR(32) PRIMARY KEY,
      name       VARCHAR(100) NOT NULL,
      class      VARCHAR(50)  NULL,
      roll       VARCHAR(50)  NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    cur.close()

def upsert_student(conn, student_id, name, sclass, roll):
    sql = """
    INSERT INTO students (student_id, name, class, roll)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      name=VALUES(name), class=VALUES(class), roll=VALUES(roll)
    """
    cur = conn.cursor()
    cur.execute(sql, (student_id, name, sclass or None, roll or None))
    cur.close()

def safe_dirname(s):
    s = s.strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^A-Za-z0-9_\-.]", "", s)
    return s

class CaptureApp:
    def __init__(self, root):
        self.root = root
        root.title("Student Registration + Face Capture")

        # Left: camera preview
        self.preview = tk.Label(root, bd=2, relief="sunken")
        self.preview.grid(row=0, column=0, rowspan=8, padx=8, pady=8)

        # Right: form
        ttk.Label(root, text="Student Name").grid(row=0, column=1, sticky="w", padx=6, pady=(12,2))
        self.name_var = tk.StringVar()
        ttk.Entry(root, textvariable=self.name_var, width=28).grid(row=1, column=1, sticky="ew", padx=6)

        ttk.Label(root, text="Student ID (Primary Key)").grid(row=2, column=1, sticky="w", padx=6, pady=(12,2))
        self.id_var = tk.StringVar()
        ttk.Entry(root, textvariable=self.id_var, width=28).grid(row=3, column=1, sticky="ew", padx=6)

        ttk.Label(root, text="Class").grid(row=4, column=1, sticky="w", padx=6, pady=(12,2))
        self.class_var = tk.StringVar()
        ttk.Entry(root, textvariable=self.class_var, width=28).grid(row=5, column=1, sticky="ew", padx=6)

        ttk.Label(root, text="Roll").grid(row=6, column=1, sticky="w", padx=6, pady=(12,2))
        self.roll_var = tk.StringVar()
        ttk.Entry(root, textvariable=self.roll_var, width=28).grid(row=7, column=1, sticky="ew", padx=6)

        btns = ttk.Frame(root)
        btns.grid(row=8, column=0, columnspan=2, pady=8)
        self.start_btn = ttk.Button(btns, text="Start Capture", command=self.start_capture)
        self.start_btn.pack(side="left", padx=6)
        self.stop_btn = ttk.Button(btns, text="Stop", command=self.stop_capture, state="disabled")
        self.stop_btn.pack(side="left", padx=6)

        self.status = tk.StringVar(value="Idle.")
        ttk.Label(root, textvariable=self.status).grid(row=9, column=0, columnspan=2, sticky="w", padx=8, pady=(0,8))

        # OpenCV: cascade
        self.face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
        if self.face_cascade.empty():
            messagebox.showerror("Error", f"Cannot load Haar cascade at:\n{CASCADE_PATH}")
            root.destroy(); return

        # Camera via libcamera (BGR direct)
        self.PIPELINE = (
            f"libcamerasrc ! video/x-raw,width={WIDTH},height={HEIGHT},framerate={FPS}/1 ! "
            "videoconvert ! video/x-raw,format=BGR ! appsink"
        )
        self.cap = cv2.VideoCapture(self.PIPELINE, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            messagebox.showerror("Camera error", "Could not open camera via libcamera pipeline.")
            root.destroy(); return

        # DB
        try:
            self.conn = DB_CONNECT(**DB_CFG)
            try: self.conn.autocommit = True
            except: pass
            ensure_students_table(self.conn)
        except Exception as e:
            self.conn = None
            messagebox.showwarning("DB warning", f"DB connection failed; continuing without DB.\n{e}")

        # runtime state
        self.running = True
        self.capturing = False
        self.saved = 0
        self.last_save = 0.0
        self.person_dir = None
        self.folder_base = None

        # start loop
        self.update_video()

    def start_capture(self):
        name = self.name_var.get().strip()
        sid  = self.id_var.get().strip()
        scls = self.class_var.get().strip()
        srol = self.roll_var.get().strip()

        if not name or not sid:
            messagebox.showerror("Missing info", "Please enter both Student Name and Student ID.")
            return

        # Upsert student into DB
        if self.conn:
            try:
                upsert_student(self.conn, sid, name, scls, srol)
            except Exception as e:
                messagebox.showwarning("DB warning", f"Could not upsert student:\n{e}")

        # Dataset folder: Name_ID
        folder_name = safe_dirname(f"{name}_{sid}")
        self.person_dir = os.path.join(DATASET_ROOT, folder_name)
        os.makedirs(self.person_dir, exist_ok=True)
        self.folder_base = folder_name

        # reset counters
        self.saved = 0
        self.last_save = 0.0
        self.capturing = True
        self.status.set(f"Capturing for {name} ({sid}) → {self.person_dir}")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

    def stop_capture(self):
        self.capturing = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status.set("Stopped. You can edit info and start again.")

    def update_video(self):
        if not self.running:
            return

        ok, frame = self.cap.read()
        if ok:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(80,80))

            # draw first face
            if len(faces) > 0:
                (x,y,w,h) = faces[0]
                cv2.rectangle(frame, (x,y), (x+w,y+h), (0,255,0), 2)

                # save one every MIN_INTERVAL while capturing
                now = time.time()
                if self.capturing and self.person_dir and (now - self.last_save) >= MIN_INTERVAL and self.saved < TARGET_SAMPLES:
                    face_color = cv2.resize(frame[y:y+h, x:x+w], (200,200))  # COLOR crop
                    fname = os.path.join(self.person_dir, f"{self.folder_base}_{self.saved:03d}.png")
                    cv2.imwrite(fname, face_color)
                    if SAVE_FULL_FRAME_TOO:
                        base = os.path.join(self.person_dir, f"{self.folder_base}_{self.saved:03d}_full.png")
                        cv2.imwrite(base, frame)
                    self.saved += 1
                    self.last_save = now
                    self.status.set(f"Saved {self.saved}/{TARGET_SAMPLES} → {self.person_dir}")
                    if self.saved >= TARGET_SAMPLES:
                        # show short message, then quit cleanly
                        self.capturing = False
                        self.start_btn.config(state="disabled")
                        self.stop_btn.config(state="disabled")
                        self.status.set(f"Done. Saved {self.saved} images. Closing...")
                        # let the GUI paint the status, then close (releases camera/DB in on_close)
                        self.root.after(400, self.on_close)


            # HUD
            cv2.putText(frame, f"{WIDTH}x{HEIGHT}@{FPS}  Capturing:{self.capturing}  Saved:{self.saved}/{TARGET_SAMPLES}",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

            # Convert BGR -> RGB for Tk
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            self.preview.imgtk = imgtk
            self.preview.configure(image=imgtk)

        # loop
        self.root.after(10, self.update_video)

    def on_close(self):
        self.running = False
        try: self.cap.release()
        except: pass
        try: self.conn.close()
        except: pass
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CaptureApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=0)
    root.mainloop()
