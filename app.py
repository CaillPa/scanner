import configparser
import subprocess
import multiprocessing
import time
from collections import deque
import flask_login
from flask import Flask, render_template, redirect, url_for
from forms import UsernamePasswordForm, ScannerConfigForm

"""
    GLOBALS
"""
app = Flask(__name__)
app.config.from_object('config')
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

# user database
user_db = {'admin': {'pw': 'admin'}, 'operateur': {'pw': 'op'}}
# default connection properties
ip = '192.168.1.12'
port = '2111'

status_info = {'connexion_status': '',\
    'status_code': '',\
    'storage': ''}
events = deque(maxlen=12)

"""
    USER MANAGEMENT
"""
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

"""
    ROUTES
"""

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/index')
def index():
    return redirect(url_for('login'))

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

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    flask_login.logout_user()
    return redirect(url_for('index'))

@app.route('/dash')
@flask_login.login_required
def dash():
    check_storage()
    return render_template('dash.html', connexion_status=status_info['connexion_status'],\
        status_code=status_info['status_code'], ip=ip, events=events,\
        storage=status_info['storage'])

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

        with open('lms/config.ini', 'w') as cfgfile:
            cfg.write(cfgfile)

        return redirect(url_for('dash'))

    return render_template('config.html', form=form)

@app.route('/test', methods=['GET', 'POST'])
@flask_login.login_required
def test():
    """
        Test connection to LMS
    """
    print('test')
    rep = subprocess.Popen(['python3', 'lms/scanner.py', '-i', ip, '-p', port, 'test'],\
        stdout=subprocess.PIPE)
    msg = rep.communicate()[0].decode()
    status_info['connexion_status'] = msg
    events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) + ' - TEST: ' +\
        msg)
    return redirect(url_for('dash'))

@app.route('/status', methods=['GET', 'POST'])
@flask_login.login_required
def status():
    """
        Query LMS' status
    """
    print('status')
    rep = subprocess.Popen(['python3', 'lms/scanner.py', '-i', ip, '-p', port, 'status'],\
        stdout=subprocess.PIPE)
    msg = rep.communicate()[0].decode()
    status_info['status_code'] = msg
    events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) + ' - STATUS: ' +\
        msg)
    return redirect(url_for('dash'))

@app.route('/start', methods=['GET', 'POST'])
@flask_login.login_required
def start():
    print('start')
    multiprocessing.Process(target=pstart).start()
    events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) + ' - START: ')
    return redirect(url_for('dash'))

def pstart():
    subprocess.Popen(['python3', 'lms/scanner.py', '-i', ip, '-p', port, 'start'],\
        stdout=subprocess.PIPE)

@app.route('/stop', methods=['GET', 'POST'])
@flask_login.login_required
def stop():
    print('stop')
    rep = subprocess.Popen(['python3', 'lms/scanner.py', '-i', ip, '-p', port, 'stop'],\
        stdout=subprocess.PIPE)
    events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) + ' - STOP: ' +\
        rep.communicate()[0].decode())
    return redirect(url_for('dash'))

@app.route('/crash', methods=['GET', 'POST'])
@flask_login.login_required
def crash():
    print('crash')
    rep = subprocess.Popen(['python3', 'lms/scanner.py', '-i', ip, '-p', port, 'crash'],\
        stdout=subprocess.PIPE)
    events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) + ' - CRASH: ' +\
        rep.communicate()[0].decode())
    return redirect(url_for('dash'))

@app.route('/ping', methods=['GET', 'POST'])
@flask_login.login_required
def ping():
    """
        Pings eth0's broadcast IP and assigns responding IP to ip global
    """
    print('ping')
    # get eth0's broadcast IP address
    rep = subprocess.Popen('ip addr|grep eth0|grep brd', shell=True, stdout=subprocess.PIPE)
    brd = rep.communicate()[0].decode()
    if brd == '':
        events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) +\
            " - PING: Interface eth0 non connectée")
        return redirect(url_for('dash'))
    brd = brd.split(' ')[7]

    # ping broadcast address
    rep = subprocess.Popen(['ping', '-b', brd, '-I', 'eth0', '-c', '1'],\
        shell=False, stdout=subprocess.PIPE)
    rep = rep.communicate()[0].decode()

    # retrieves response's IP
    if rep.find('ttl') < 0:
        events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) +\
            ' - PING: Aucune réponse, vérifiez la connexion')
        return redirect(url_for('dash'))
    for line in rep.split('\n'):
        if line.startswith('64'):
            global ip
            ip = line.split(' ')[3][0:-1]
            break
    events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) +\
            ' - PING: Réponse reçue de ' + ip)
    return redirect(url_for('dash'))

def check_storage():
    """
        Checks /dev/sda1 storage state, updates status_info with fill percentage
    """
    rep = subprocess.Popen('df -kh /dev/sda1', shell=True, stdout=subprocess.PIPE)
    rep = rep.communicate()[0].decode().split(' ')
    for elt in reversed(rep):
        if elt.endswith('%'):
            global status_info
            status_info['storage'] = elt[0:-1]
            break


if __name__ == '__main__':
    app.run(host='0.0.0.0')
