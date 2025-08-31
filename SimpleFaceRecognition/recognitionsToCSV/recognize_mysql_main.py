import os, time, cv2
from datetime import datetime, date
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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

DB_CFG = dict(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.getenv("DB_USER", "facelogger"),
    password=os.getenv("DB_PASSWORD", "Prious1234"),
    database=os.getenv("DB_NAME", "facelog"),
)

THRESH = int(os.getenv("THRESH", "65"))
W = int(os.getenv("WIDTH", "1024"))
H = int(os.getenv("HEIGHT", "768"))
FPS = int(os.getenv("FRAMERATE", "30"))
FULLSCREEN_ENV = os.getenv("FULLSCREEN", "0").lower() in ("1","true","yes","y")
MIRROR = os.getenv("MIRROR", "1").lower() in ("1","true","yes","y")
SCALE = float(os.getenv("DISPLAY_SCALE", "1.25"))  # 25% bigger window

CASCADE_PATH = os.path.join(BASE_DIR, "cascades", "haarcascade_frontalface_default.xml")
LABELS_PATH  = os.path.join(BASE_DIR, "models", "labels.txt")
MODEL_PATH   = os.path.join(BASE_DIR, "models", "lbph.yml")
SNAP_DIR     = os.path.join(BASE_DIR, "snapshots")
os.makedirs(SNAP_DIR, exist_ok=True)

def open_db():
    while True:
        try:
            conn = DB_CONNECT(**DB_CFG)
            try: conn.autocommit = True
            except: pass
            return conn
        except Exception as e:
            print("[DB] connect failed, retry in 5s:", e)
            time.sleep(5)

def ensure_table(conn):
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_best (
      id INT AUTO_INCREMENT PRIMARY KEY,
      person_name VARCHAR(100) NOT NULL,
      day_date DATE NOT NULL,
      best_score TINYINT UNSIGNED NOT NULL,
      best_at DATETIME NOT NULL,
      snapshot_path VARCHAR(255) DEFAULT NULL,
      UNIQUE KEY uniq_person_day (person_name, day_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)
    cur.close()

def upsert_best(conn, person_name, day_date, score, ts, snapshot_path):
    sql = """
    INSERT INTO daily_best (person_name, day_date, best_score, best_at, snapshot_path)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
      best_at = IF(VALUES(best_score) > best_score, VALUES(best_at), best_at),
      snapshot_path = IF(VALUES(best_score) > best_score, VALUES(snapshot_path), snapshot_path),
      best_score = GREATEST(best_score, VALUES(best_score));
    """
    cur = conn.cursor()
    cur.execute(sql, (person_name, day_date, int(score), ts, snapshot_path))
    cur.close()

def load_labels(path):
    labels = {}
    with open(path, "r") as f:
        for line in f:
            i, name = line.strip().split(",", 1)
            labels[int(i)] = name
    return labels

def main():
    print(f"[CFG] {W}x{H}@{FPS}  THRESH={THRESH}  FULLSCREEN={FULLSCREEN_ENV}  MIRROR={MIRROR}")

    # Models
    face_cascade = cv2.CascadeClassifier(CASCADE_PATH)
    assert not face_cascade.empty(), f"Failed to load cascade {CASCADE_PATH}"
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)
    labels = load_labels(LABELS_PATH)

    # Camera pipeline: output BGR directly so colors look normal in OpenCV
    PIPELINE = (
        f"libcamerasrc ! "
        f"video/x-raw,width={W},height={H},framerate={FPS}/1 ! "
        "videoconvert ! video/x-raw,format=BGR ! appsink"
    )
    cap = cv2.VideoCapture(PIPELINE, cv2.CAP_GSTREAMER)
    assert cap.isOpened(), "Camera not available"

    # DB
    conn = open_db()
    ensure_table(conn)

    best_today = {}
    current_day = date.today()

    # GUI
    win_w = int(W * SCALE)
    win_h = int(H * SCALE)

    cv2.namedWindow("Attendance", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Attendance", win_w, win_h)
    if FULLSCREEN_ENV:
        cv2.setWindowProperty("Attendance", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    print("Controls: q=quit  f=toggle fullscreen")
    t0, frames = time.time(), 0
    fullscreen = FULLSCREEN_ENV

    while True:
        ok, frame = cap.read()   # already BGR from pipeline
        if not ok:
            continue

        # Optional mirror for user-friendly preview
        if MIRROR:
            frame = cv2.flip(frame, 1)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # day rollover
        today = date.today()
        if today != current_day:
            best_today.clear()
            current_day = today

        faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(80,80))
        for (x,y,w,h) in faces:
            face = cv2.resize(gray[y:y+h, x:x+w], (200,200))
            label_id, dist = recognizer.predict(face)
            score = max(0, min(100, 100 - dist))
            name = labels.get(label_id, "Unknown")

            ok_recog = (name != "Unknown" and score >= THRESH)
            color = (0,255,0) if ok_recog else (0,0,255)
            cv2.rectangle(frame, (x,y), (x+w,y+h), color, 2)
            cv2.putText(frame, f"{name if ok_recog else 'Unknown'} ({score:.0f})",
                        (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            if ok_recog:
                prev = best_today.get(name, -1)
                if score > prev:
                    ts = datetime.now()
                    snap_name = f"{name}_{ts.strftime('%Y%m%d_%H%M%S')}.jpg"
                    snap_path = os.path.join(SNAP_DIR, snap_name)
                    face_color = cv2.resize(frame[y:y+h, x:x+w], (200,200))
                    cv2.imwrite(snap_path, face_color)
                    best_today[name] = score
                    try:
                        upsert_best(conn, name, today, score, ts.strftime("%Y-%m-%d %H:%M:%S"), snap_path)
                        print(f"[DB] {name} {today} score={score} -> upserted")
                    except Exception as e:
                        print("[DB] upsert failed:", e)
                        try: conn.close()
                        except: pass
                        conn = open_db()
                        ensure_table(conn)

        # HUD
        frames += 1
        dt = time.time() - t0
        if dt >= 1.0:
            fps = frames / dt
            t0 = time.time()
            frames = 0
        else:
            fps = 0.0
        cv2.putText(frame, f"{W}x{H}@{FPS}  THRESH={THRESH}  FPS={fps:.1f}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

        display = cv2.resize(frame, (win_w, win_h), interpolation=cv2.INTER_NEAREST)
        cv2.imshow("Attendance", display)
        k = cv2.waitKey(1) & 0xFF
        if k == ord('q'):
            break
        if k == ord('f'):
            fullscreen = not fullscreen
            mode = cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL
            cv2.setWindowProperty("Attendance", cv2.WND_PROP_FULLSCREEN, mode)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

