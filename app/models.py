from . import db
from datetime import datetime

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    face_encoding = db.Column(db.PickleType, nullable=True)  # We'll store face encodings as pickled numpy arrays
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendances = db.relationship('Attendance', backref='student', lazy=True)

    def __repr__(self):
        return f"<Student {self.student_id} - {self.name}>"

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    room = db.Column(db.String(50), nullable=True)  # You can change to room_id if you want a Room model

    def __repr__(self):
        return f"<Attendance {self.student_id} @ {self.timestamp}>"