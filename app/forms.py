from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from wtforms.fields.html5 import DateField, TimeField
import datetime

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class DateForm(FlaskForm):
    date = DateField(default=datetime.date.today)
    time = TimeField(default=datetime.time(00,00))
    date2 = DateField(default=datetime.date.today)
    time2 = TimeField(default=datetime.time(00,00))
    submit = SubmitField()