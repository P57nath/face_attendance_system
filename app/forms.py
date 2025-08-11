from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms.validators import DataRequired

class StudentRegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    student_id = StringField('Student ID', validators=[DataRequired()])
    photo = FileField('Face Photo', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    submit = SubmitField('Register Student')