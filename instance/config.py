# Flask secret key
SECRET_KEY = 'b125de2b2405532549f32d0a1e60a64e'

# MySQL Config (adjust according to your setup)
MYSQL_HOST = 'localhost'
MYSQL_USER = 'your_mysql_user'
MYSQL_PASSWORD = 'Prious1234'
MYSQL_DB = 'face_attendance'

# SQLAlchemy connection string
SQLALCHEMY_DATABASE_URI = f"mysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
SQLALCHEMY_TRACK_MODIFICATIONS = False