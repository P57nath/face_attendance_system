import numpy as np
import face_recognition
from werkzeug.utils import secure_filename
import os
from flask import current_app

def save_and_encode_face(photo_storage, upload_folder="app/static/uploads"):
    # Ensure upload folder exists
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(photo_storage.filename)
    filepath = os.path.join(upload_folder, filename)
    photo_storage.save(filepath)

    # Load image and get face encodings
    image = face_recognition.load_image_file(filepath)
    encodings = face_recognition.face_encodings(image)
    if not encodings:
        os.remove(filepath)
        raise ValueError("No face detected in the uploaded image.")
    return encodings[0], filepath  # Return the encoding and where the image was saved