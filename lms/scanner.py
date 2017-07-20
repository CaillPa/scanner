import argparse
import logging
import time
import configparser
import lzma
import gzip
import os
import signal
import multiprocessing
from collections import deque
from LMS5xx import LMS5xx
from structs import scanCfg, scanDataCfg

# global running flag
STOP = False

# chemin d'enregistrement des donnees
PATH = '/media/usb/'

def loadConfig(filename):
    """
        Charge la config stockee dans filename et retourne les structures adequates
        Si pas de parametre, prend la config dans defaults.ini
        @param filename: fichier contenant les parametres
        @return structure scanCfg, structure scanDataCfg, entier
    """
    config = configparser.ConfigParser()
    config.read(filename)
    config = config['DEFAULT']
    defaults = configparser.ConfigParser()
    defaults.read(os.path.join(os.path.dirname(__file__), 'defaults.ini'))
    defaults = defaults['DEFAULT']

    cfg = scanCfg()
    cfg.scaningFrequency = int(config.get('scaningFrequency', defaults['scaningFrequency']))
    cfg.angleResolution = int(config.get('angleResolution', defaults['angleResolution']))
    cfg.startAngle = int(config.get('startAngle', defaults['startAngle']))
    cfg.stopAngle = int(config.get('stopAngle', defaults['stopAngle']))

    datacfg = scanDataCfg()
    datacfg.remission = int(config.get('remission', defaults['remission']))
    datacfg.resolution = int(config.get('resolution', defaults['resolution']))
    datacfg.encoder = int(config.get('encoder', defaults['encoder']))
    datacfg.position = int(config.get('position', defaults['position']))
    datacfg.deviceName = int(config.get('deviceName', defaults['deviceName']))
    datacfg.timestamp = int(config.get('timestamp', defaults['timestamp']))
    datacfg.outputinterval = int(config.get('outputinterval', defaults['outputinterval']))

    echo = int(config.get('echoFilter', defaults['echoFilter']))

    return cfg, datacfg, echo

def saveConfig(lms, cfg, datacfg, echo):
    """
        Ecris la config des structures en parametre dans la memoire du telemetre
        Enregistre la config dans la memoire EEPROM et redemarre le telemetre
        @param lms: classe LMS5xx
        @param cfg: structure scanCfg
        @param datacfg: structure scanDataCfg
        @param echo: entier
    """
    lms.login()
    lms.setTime()
    lms.setScanCfg(cfg)
    lms.setScanDataCfg(datacfg)
    lms.setEchoFilter(echo)
    lms.saveConfig()
    lms.startDevice()

def saveTxt(q):
    """
        Enregistre le contenu de q en texte brut non compresse
        @param q: iterable contenant des bytes a enregistrer
    """
    path = PATH+time.strftime('%d%b%Y%H%M%S', time.localtime())+'.txt'
    with open(path, 'wb') as raw:
        raw.write(b''.join(q))
        raw.close()

def saveGz(q):
    """
        Enregistre le contenu de q en texte compresse (gzip)
        @param q: iterable contenant des bytes a enregistrer
    """
    path = PATH+time.strftime('%d%b%Y%H%M%S', time.localtime())+'.txt.gz'
    with gzip.open(path, 'wb') as gz:
        gz.write(b''.join(q))
        gz.close()

def makeLZMA(q):
    """
        Compresse les elements dans q jusqu'a rencontrer None puis enregistre le resultat
        Le nom du fichier correspond a la date de debut du processus
        Cette fonction est faite pour etre executee dans un processus separe
        (des elements peuvent arriver dans q au fil du temps)
        Ce processus s'arrete si son processus pere s'arrete
        @param q: iterable contenant les trames a compresser
    """
    path = PATH+time.strftime('%Y%m%d%H%M%S', time.localtime())+'.txt.xz'
    lzc = lzma.LZMACompressor()
    res = deque() # file contenant les objects compresses
    item = q.get() # objet courant lu dans q
    parent = os.getppid()
    while item is not None: # None signifie qu'aucune autre donnee arrive
        res.append(lzc.compress(item))
        item = q.get()
        if os.getppid() != parent: # si ce processus est orphelin (crash du process pere)
            logging.debug('Arret du processus orphelin avec le PID %s', os.getpid())
            os._exit(0) # arret direct du processus
    res.append(lzc.flush()) # fini la compression des donnees

    # enregistrement dans le fichier
    with lzma.open(path, 'wb') as f:
        f.write(b''.join(res))
    logging.info('Fin du processus avec le PID %s', os.getpid())
    return

def signalHandler(a, b):
    """
        A la reception d'un signal cette fonction change l'etat du flag global STOP
        Cela arrete l'acquisition de donnees continue proprement depuis un autre processus
    """
    global STOP
    STOP = True
    logging.info("Signal d'arret recu")

def main():
    logging.basicConfig(filename=os.path.join(os.path.dirname(__file__), 'log.txt'),\
        level=logging.DEBUG)
    logging.info('===== %s Debut du log', time.strftime('%d/%m/%Y %I:%M:%S', time.localtime()))
    
    # --- PARSING DES ARGUMENTS ---
    parser = argparse.ArgumentParser(description='LMS5xx CLI tool')
    parser.add_argument('-i', '--ip', default='192.168.1.12', help='Adresse IP du telemetre')
    parser.add_argument('-p', '--port', default='2111', type=int, help='Port du telemetre')
    parser.add_argument('-s', '--size', default='50000', type=int, help='Nombre de trames par bloc')
    parser.add_argument('-l', '--load', default='defaults.ini',\
        help='Charge les reglages depuis un fichier', )
    parser.add_argument('commande', choices=['test', 'start', 'stop', 'save', 'status', 'crash'],\
        help='Commande effectuee par le telemetre')

    args = parser.parse_args() # parse les arguments
    logging.info('Commande : %s', args.commande)
    signal.signal(signal.SIGUSR1, signalHandler) # attache SIGUSR1 a signalHandler()

    # --- CRASH ---
    if args.commande == 'crash':
        """
            Arrete l'acquisition de donnees continue immediatement mais perd des donnees
        """
        try:
            with open(os.path.join(os.path.dirname(__file__), 'pid'), 'r') as pidfile:
                pid = int(pidfile.read())
        except FileNotFoundError:
            print('Fichier PID introuvable, abandon')
            logging.warning('Fichier PID introuvable, abandon')
            return
        try:
            # tue le processus, brutalement
            os.kill(pid, signal.SIGKILL)
            os.remove(os.path.join(os.path.dirname(__file__), 'pid'))
        except ProcessLookupError:
            pass
        return

    # --- STOP ---
    if args.commande == 'stop':
        """
            Arrete l'acquisition de donnees continue sans perte de donnees
            Attend que les processus de compression soient termines
        """
        try:
            with open(os.path.join(os.path.dirname(__file__), 'pid'), 'r') as pidfile:
                pid = int(pidfile.read())
        except FileNotFoundError:
            print('Fichier PID introuvable, abandon')
            logging.warning('Fichier PID introuvable, abandon')
            return
        try:
            # change l'etat du flag STOP via signalHandler()
            os.kill(pid, signal.SIGUSR1)
        except ProcessLookupError:
            pass

        return

    # toutes les autres commandes necessitent de se connecter au telemetre
    lms = LMS5xx()
    logging.debug('Connexion au LMS 5xx')
    lms.connect(args.ip, args.port)
    if not lms.isConnected():
        print('Impossible de se connecter au telemetre')
        logging.critical('Abandon ...')
        # quitte directement le programme si on ne peut pas se connecter au telemetre
        return

    # chargement des config depuis le fichier
    cfg, datacfg, echo = loadConfig(args.load)

    # --- TEST ---
    if args.commande == 'test':
        """
            Test de connexion
        """
        lms.disconnect()
        print('OK')
        return

    # --- STATUS ---
    if args.commande == 'status':
        """
            Affiche le code d'etat du telemetre
        """
        status = lms.queryStatus()
        print(status)
        return

    # --- SAVE ---
    if args.commande == 'save':
        """
            Enregistre la config dans la memoire du telemetre, elle sera accessible
            apres redemarrage
        """
        saveConfig(lms, cfg, datacfg, echo)
        return

    # --- START ---
    if args.commande == 'start':
        """
            Demarre l'acquisiton de donnees avec compression en temps reel
            Le processus s'arrete proprement en recevant un signal SIGUSR1
        """
        # charge la config dans le telemetre
        saveConfig(lms, cfg, datacfg, echo)
        # Enregistre le pid de ce processus dans un fichier pour l'arreter plus tard
        # avec les commandes start et stop
        with open(os.path.join(os.path.dirname(__file__), 'pid'), 'w') as fic:
            fic.write(str(os.getpid()))
            fic.close()

        # attend que le telemetre soit pret a mesurer
        while lms.queryStatus() < 7:
            time.sleep(0.5)

        # les mesures sont enregistrees dans un dossier separe
        global PATH
        PATH = PATH + time.strftime('%Y%m%d%H%M%S', time.localtime())+'/'
        os.mkdir(PATH)

        lms.scanContinous(1) # demarre l'acquisition de donnees continue
        while not STOP: # le flag STOP permet d'arreter proprement l'acquisition
            q = multiprocessing.Queue() # dans q seront ajoutees les trames recues
            p = multiprocessing.Process(target=makeLZMA, args=(q,)) # processus de compression
            p.start()
            logging.debug("Demarrage d'un nouveau processus avec le PID %s", p.pid)
            for _ in range(args.size): # le processus de compression recevra size elements
                dat = lms.getScanData(0.1) # lis une trame
                if dat is not None:
                    q.put(dat) # ajoute la trame dans la file partagee avec le processus de compression
            q.put(None) # indique au processus de compression qu'aucune donnee supplementaire n'arrivera
            q.close() # ferme le tube de communication
            multiprocessing.active_children() # force l'arret des processus fils termines

        # indique au dernier processus de s'arreter
        try:
            q.put(None)
        except:
            pass
        lms.scanContinous(0) # arrete l'acquisition continue de donnees
        lms.stopMeas()
        # attend que les processus fils aient termine
        while len(multiprocessing.active_children()) > 0:
            pass
        logging.info('Processus principal termine')

        logging.info('===== %s Fin du log', time.strftime('%d/%m/%Y %I:%M:%S', time.localtime()))

        # deplace les logs dans le dossier contenant les mesures
        with open(os.path.join(os.path.dirname(__file__), 'log.txt'), 'r') as logs:
            with open(os.path.join(PATH, 'log.txt'), 'w') as dstlog:
                dstlog.write(logs.read())
                os.remove(os.path.join(os.path.dirname(__file__), 'log.txt'))

        os.remove(os.path.join(os.path.dirname(__file__), 'pid'))
        return

if __name__ == '__main__':
    main()
