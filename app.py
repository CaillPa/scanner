"""
    Application Flask fournissant l'interface web
    voir la doc de Flask et des modules flask_login et flask_wtf
"""


import configparser
import subprocess
import multiprocessing
import time
import os
from collections import deque
import flask_login
from flask import Flask, render_template, redirect, url_for, request
from forms import UsernamePasswordForm, ScannerConfigForm, DataInfoForm

"""
    VARIABLES GLOBALES
"""
app = Flask(__name__)
app.config.from_object('config')
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

# base de donnees d'utilisateurs
user_db = {'admin': {'pw': 'admin'}, 'operateur': {'pw': 'op'}}
# parametres de connexion par defaut
ip = '192.168.1.12'
port = '2111'
# etat de la connexion
status_info = {'connexion_status': '',\
                'status_code': '',\
                'storage': '',
                'recording': False}
events = deque(maxlen=12)

# pour les chemins relatifs quand on lance le script depuis un autre dossier
#PATH = os.path.dirname(__file__)
PATH = '/home/pi/scanner/'

"""
    GESTION DES UTILISATEURS
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
    if form.validate_on_submit(): # si on renvoie le formulaire rempli
        username = form.username.data
        if username not in user_db: # si l'utilisateur est dans la base d'utilisateurs
            return render_template('login.html', form=form, badlogin=True)

        if form.password.data == user_db[username]['pw']: # si le mot de passe est bon
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
    status_info['recording'] = isRecording()
    return render_template('dash.html', connexion_status=status_info['connexion_status'],\
        status_code=status_info['status_code'], ip=ip, events=events,\
        storage=status_info['storage'], rec=status_info['recording'])

@app.route('/config', methods=['GET', 'POST'])
@flask_login.login_required
def config():
    form = ScannerConfigForm()
    if form.validate_on_submit():
        cfg = configparser.ConfigParser()
        # les valeurs codees en dur sont les valeurs qui ne changeront pas (inutiles)
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

        # enregistre la config dans un fichier, elle sera chargee au demarrage du telemetre
        with open(PATH+'/lms/config.ini', 'w') as cfgfile:
            cfg.write(cfgfile)

        return redirect(url_for('dash'))

    return render_template('config.html', form=form)

@app.route('/info', methods=['GET', 'POST'])
@flask_login.login_required
def info():
    """
        Ecriture des infos sur l'enregistrement dans un fichier temporaire
    """
    form = DataInfoForm()
    if form.validate_on_submit():
        with open(PATH+'info.txt', 'w') as infos:
            infos.write(form.project.data+'\n')
            infos.write(form.location.data+'\n')
            infos.write(form.description.data+'\n')
        return redirect(url_for('dash'))
    return render_template('info.html', form=form)

@app.route('/test', methods=['GET', 'POST'])
@flask_login.login_required
def test():
    # lance l'outil scanner et pipe sa sortie sur rep
    rep = subprocess.Popen(['python3', PATH+'/lms/scanner.py', '-i', ip, '-p', port, 'test'],\
        stdout=subprocess.PIPE)
    msg = rep.communicate()[0].decode() # lis le stdout de l'outil scanner dans msg
    status_info['connexion_status'] = msg # met a jour les infos de connexion
    events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) + ' - TEST: ' +\
        msg)
    return redirect(url_for('dash'))

@app.route('/status', methods=['GET', 'POST'])
@flask_login.login_required
def status():
    # lance l'outil scanner et pipe sa sortie sur rep
    rep = subprocess.Popen(['python3', PATH+'/lms/scanner.py', '-i', ip, '-p', port, 'status'],\
        stdout=subprocess.PIPE)
    msg = rep.communicate()[0].decode() # lis le stdout de l'outil scanner dans msg
    status_info['status_code'] = msg # met a jour les infos de connexion
    events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) + ' - STATUS: ' +\
        msg)
    return redirect(url_for('dash'))

@app.route('/start', methods=['GET', 'POST'])
@flask_login.login_required
def start():
    if not scanner_isavailable():
        events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) +\
        ' - START: Telemetre pas encore pret pour acquisition')
    else:
        # lance l'outil scanner sur un procesus separe (start est bloquant)
        multiprocessing.Process(target=pstart).start()
        events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) + ' - START: ')
    return redirect(url_for('dash'))

def pstart():
    subprocess.Popen(['python3', PATH+'/lms/scanner.py', '-i', ip, '-p', port, '-l', 'config.ini', 'start'],\
        stdout=subprocess.PIPE)

@app.route('/stop', methods=['GET', 'POST'])
@flask_login.login_required
def stop():
    # lance l'outil scanner et pipe sa sortie sur rep
    rep = subprocess.Popen(['python3', PATH+'/lms/scanner.py', '-i', ip, '-p', port, 'stop'],\
        stdout=subprocess.PIPE)
    events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) + ' - STOP: ' +\
        rep.communicate()[0].decode()) # lis le stdout de l'outil scan et l'ajoute a la file d'evenements
    return redirect(url_for('dash'))

@app.route('/crash', methods=['GET', 'POST'])
@flask_login.login_required
def crash():
    # lance l'outil scanner et pipe sa sortie sur rep
    rep = subprocess.Popen(['python3', PATH+'/lms/scanner.py', '-i', ip, '-p', port, 'crash'],\
        stdout=subprocess.PIPE)
    events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) + ' - CRASH: ' +\
        rep.communicate()[0].decode()) # lis le stdout de l'outil scan et l'ajoute a la file d'evenements
    return redirect(url_for('dash'))

@app.route('/ping', methods=['GET', 'POST'])
@flask_login.login_required
def ping():
    """
        Ping l'adresse de broadcast de l'interface eth0 et assigne l'IP de la premiere
        reponse a la variable globale ip
    """
    # recupere l'adresse de broadcast d'eth0
    rep = subprocess.Popen('ip addr|grep eth0|grep brd', shell=True, stdout=subprocess.PIPE)
    brd = rep.communicate()[0].decode()
    if brd == '':
        events.append(time.strftime('%d/%m/%Y %H:%M:%S', time.localtime()) +\
            " - PING: Interface eth0 non connectée")
        return redirect(url_for('dash'))
    brd = brd.split(' ')[7]

    # ping l'adresse de broadcast
    rep = subprocess.Popen(['ping', '-b', brd, '-I', 'eth0', '-c', '1'],\
        shell=False, stdout=subprocess.PIPE)
    rep = rep.communicate()[0].decode()

    # recupere l'adresse IP de la reponse
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

@app.route('/_date', methods=['GET', 'POST'])
def _date():
    """
        Met a jour l'horloge du serveur selon l'heure du client
    """
    date = request.args.get('a', 0)
    cmd = "sudo date --set='"+date+"'"
    subprocess.Popen(cmd, shell=True, stdout=None)
    return redirect(url_for('dash'))

def scanner_isavailable():
    """
        verifie que le telemetre est pret a enregistrer
    """
    if 'OK' not in status_info['connexion_status']:
        return False
    if '6' not in status_info['status_code']:
        if '7' not in status_info['status_code']:
            return False
    if status_info['recording'] is True:
        return False

    return True

def check_storage():
    """
        Verifie l'etat du stockage de /dev/sda1 et affiche le pourcentage utilise
    """
    rep = subprocess.Popen('df -kh /dev/sda1', shell=True, stdout=subprocess.PIPE)
    rep = rep.communicate()[0].decode().split(' ')
    for elt in reversed(rep):
        if elt.endswith('%'):
            global status_info
            status_info['storage'] = elt[0:-1]
            break

def isRecording():
    """
        Verifie si un enregistrement est en cours
    """
    rep = subprocess.Popen('ps -ef|grep scanner.py', shell=True, stdout=subprocess.PIPE)
    rep = rep.communicate()[0].decode()
    if 'python3' in rep.split():
        return 'yes'
    else:
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0')
