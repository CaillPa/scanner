import configparser
import os
import multiprocessing
import flask_login
from flask import Flask, render_template, redirect, url_for
from forms import UsernamePasswordForm, ScannerConfigForm


app = Flask(__name__)
app.config.from_object('config')

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

user_db = {'admin': {'pw': 'admin'}, 'operateur': {'pw': 'op'}}

class User(flask_login.UserMixin):
    def __init__(self):
        self.id = ''

@login_manager.user_loader
def user_loader(username):
    if username not in user_db:
        return None

    user = User()
    user.id = username
    return user

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    if username not in user_db:
        return None
    user = User()
    user.id = username
    user.is_authenticated = request.form['pw'] == user_db[username]['pw']
    return user

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/index')
def index():
    return redirect(url_for('login'))

@app.route('/dash')
@flask_login.login_required
def dash():
    return render_template('dash.html')

@app.route('/config', methods=['GET', 'POST'])
@flask_login.login_required
def config():
    form = ScannerConfigForm()
    if form.validate_on_submit():
        cfg = configparser.ConfigParser()
        cfg['DEFAULT'] = {'scaningFrequency': form.frequency.data,\
            'angleResolution': form.resolution.data,\
            'startAngle': -50000,\
            'stopAngle': 1850000,\
            'remission': 1 if form.remission.data else 0,\
            'resolution': 1,\
            'encoder': 0,\
            'position': 0,\
            'deviceName': 0,\
            'timestamp': 1,\
            'outputinterval': form.interval.data,\
            'echoFilter': form.echo.data,\
            'event': 1 if form.event.data else 0}

        with open('config.ini', 'w') as cfgfile:
            cfg.write(cfgfile)

        return redirect(url_for('dash'))

    return render_template('config.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = UsernamePasswordForm()
    if form.validate_on_submit():
        username = form.username.data
        if username not in user_db:
            return render_template('login.html', form=form, badlogin=True)

        if form.password.data == user_db[username]['pw']:
            user = User()
            user.id = username
            flask_login.login_user(user)
            return redirect(url_for('dash'))
    return render_template('login.html', form=form, badlogin=False)

@app.route('/test', methods=['GET', 'POST'])
def test():
    print('test')
    os.system('python3 lms/scanner.py -i 192.168.1.12 -p 2111 test')
    return redirect(url_for('dash'))

@app.route('/start', methods=['GET', 'POST'])
def start():
    print('start')
    multiprocessing.Process(target=pstart).start()
    return redirect(url_for('dash'))

def pstart():
    os.system('python3 lms/scanner.py -i 192.168.1.12 -p 2111 start')

@app.route('/stop', methods=['GET', 'POST'])
def stop():
    print('stop')
    os.system('python3 lms/scanner.py -i 192.168.1.12 -p 2111 stop')
    return redirect(url_for('dash'))

@app.route('/crash', methods=['GET', 'POST'])
def crash():
    print('crash')
    os.system('python3 lms/scanner.py -i 192.168.1.12 -p 2111 crash')
    return redirect(url_for('dash'))

if __name__ == '__main__':
    app.run(host='0.0.0.0')
