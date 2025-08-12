from flask import Blueprint, render_template, redirect, url_for, flash, request
from .forms import StudentRegistrationForm
from . import db
from .models import Student
from .face_utils import save_and_encode_face

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    form = StudentRegistrationForm()
    if form.validate_on_submit():
        try:
            encoding, image_path = save_and_encode_face(form.photo.data)
            student = Student(
                name=form.name.data,
                student_id=form.student_id.data,
                face_encoding=encoding
            )
            db.session.add(student)
            db.session.commit()
            flash('Student registered successfully!', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            flash(f"Error: {e}", 'danger')
    return render_template('register.html', form=form)