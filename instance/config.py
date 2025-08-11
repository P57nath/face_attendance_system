import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret')

    # Build the MySQL connection string from parts in .env
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_DB = os.getenv('MYSQL_DB', 'attendance_db')

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
