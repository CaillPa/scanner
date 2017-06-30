from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, BooleanField, IntegerField
from wtforms.validators import DataRequired, NumberRange

class UsernamePasswordForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class ScannerConfigForm(FlaskForm):
    frequency = SelectField('Scaning Frequency', choices=[(2500, '25 Hz'), (3500, '35 Hz'),\
        (5000, '50 Hz'), (7500, '75 Hz'), (10000, '100 Hz')], coerce=int)
    resolution = SelectField('Angular Resolution', choices=[(1667, '0.1667°'),\
        (2500, '0.25°'), (3333, '0.3333°'), (5000, '0.5°'), (6667, '0.6667°'),\
        (10000, '1°')], coerce=int)
    echo = SelectField('Echo', choices=[(0, 'Premier echo'), (1, 'Tous les echo'),\
        (2, 'Dernier echo')], coerce=int)
    event = BooleanField('Event', default='checked')
    remission = BooleanField('Remission', default='checked')
    interval = IntegerField('Output Interval', validators=[DataRequired(),\
        NumberRange(min=1, max=50000)])
