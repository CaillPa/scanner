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

def loadConfig(filename):
    """
        Loads config stored in filename and returns appropriate data structures
        defaults to config in 'defaults.ini'
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
        Write config stored in data structures to LMS device
        Saves config to EEPROM and restarts the device
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
        Saves content of arg q as plaintext
    """
    path = '/media/usb/'+time.strftime('%d%b%Y%H%M%S', time.localtime())+'.txt'
    with open(path, 'wb') as raw:
        raw.write(b''.join(q))
        raw.close()

def saveGz(q):
    """
        Saves content of arg q as gzip compressed plaintext
    """
    path = '/media/usb/'+time.strftime('%d%b%Y%H%M%S', time.localtime())+'.txt.gz'
    with gzip.open(path, 'wb') as gz:
        gz.write(b''.join(q))
        gz.close()

def makeLZMA(q):
    """
        Compress elements in q until None is detected then saves result in file
        Filename corresponds to the process' start date
        Meant to be run as a separate process
        Will stop if process is orphaned, hopefuly
    """
    path = '/media/usb/'+time.strftime('%Y%m%d%H%M%S', time.localtime())+'.txt.xz'
    lzc = lzma.LZMACompressor()
    res = deque()
    item = q.get()
    parent = os.getppid()
    while item is not None: # Receiving None means no more data is coming
        res.append(lzc.compress(item))
        item = q.get()
        if os.getppid() != parent: # detect if this process is orphaned (parent crash)
            logging.debug('Stopping Orphaned process with pid %s', os.getpid())
            os._exit(0)
    res.append(lzc.flush())

    with lzma.open(path, 'wb') as f:
        f.write(b''.join(res))
    logging.info('Quitting process with pid %s', os.getpid())
    return

def signalHandler(a, b):
    """
        handle received signal to tell the main process to stop via global flag
    """
    global STOP
    STOP = True
    logging.info('Stop signal received')

def main():
    # --- ARGUMENT PARSING ---
    parser = argparse.ArgumentParser(description='LMS5xx CLI tool')
    parser.add_argument('-i', '--ip', default='192.168.1.12', help='Adresse IP du telemetre')
    parser.add_argument('-p', '--port', default='2111', type=int, help='Port du telemetre')
    parser.add_argument('-s', '--size', default='10000', type=int, help='Nombre de trames par bloc')
    parser.add_argument('-l', '--load', default='defaults.ini',\
        help='Charge les reglages depuis un fichier', )
    parser.add_argument('commande', choices=['test', 'start', 'stop', 'save', 'status', 'crash'],\
        help='Commande effectuee par le telemetre')

    args = parser.parse_args()
    logging.info('Command : %s', args.commande)
    signal.signal(signal.SIGUSR1, signalHandler) # attach SIGUSR1 to signalHandler()

    if args.commande == 'crash':
        """
            Stops continous data aquisition NOW (loses some data)
        """
        try:
            with open('pid', 'r') as pidfile:
                pid = int(pidfile.read())
        except FileNotFoundError:
            print('PID file not found, aborting')
            logging.warning('PID file not found, aborting')
            return
        try:
            # REGARDE ICI SI CA MERDE
            os.kill(pid, signal.SIGUSR1)
        except ProcessLookupError:
            pass
        return

    if args.commande == 'stop':
        """
            Stops continous data aquisition properly
            Waits for compression process to finish
        """
        try:
            with open('pid', 'r') as pidfile:
                pid = int(pidfile.read())
        except FileNotFoundError:
            print('PID file not found, aborting')
            logging.warning('PID file not found, aborting')
            return
        try:
            os.kill(pid, signal.SIGUSR1)
        except ProcessLookupError:
            pass
        # waits for child processes to finish
        while len(multiprocessing.active_children()) > 0:
            pass
        return

    lms = LMS5xx()
    logging.debug('Connecting to LMS')
    lms.connect(args.ip, args.port)
    if not lms.isConnected():
        print('Impossible de se connecter au telemetre')
        logging.critical('Aborting ...')
        return

    cfg, datacfg, echo = loadConfig(args.load)

    if args.commande == 'test':
        """
            Connectivity test
        """
        lms.disconnect()
        print('OK')
        return

    if args.commande == 'status':
        """
            Cutputs status of scanner
        """
        status = lms.queryStatus()
        print(status)
        return

    if args.commande == 'save':
        """
            Save config to EEPROM so it doesn't change upon powering off the device
        """
        saveConfig(lms, cfg, datacfg, echo)
        return

    if args.commande == 'start':
        """
            Starts continous data aquisition with real-time compression on multiple processes
            Stops properly when receiving SIGUSR1
        """
        # load config to device
        saveConfig(lms, cfg, datacfg, echo)
        # saves process pid to file
        with open('pid', 'w') as fic:
            fic.write(str(os.getpid()))
            fic.close()

        # wait for scanner to be ready
        while lms.queryStatus() < 7:
            time.sleep(0.5)

        lms.scanContinous(1) # starts LMS continous data acquisition
        while not STOP: # global running flag
            q = multiprocessing.Queue()
            p = multiprocessing.Process(target=makeLZMA, args=(q,))
            p.start()
            logging.debug('Spawning new process with pid %s', p.pid)
            for _ in range(args.size): # will send size elements to compression process
                dat = lms.getScanData(0.1)
                if dat is not None:
                    q.put(dat)
            q.put(None) # tell compression process that no more data is coming
            q.close()
            multiprocessing.active_children() # force close terminated processes

        lms.scanContinous(0) # stops LMS continous data acquisition
        lms.stopMeas()
        logging.info('Main process terminated')
        return

if __name__ == '__main__':
    logging.basicConfig(filename=os.path.join(os.path.dirname(__file__),\
        'lms.log'), level=logging.DEBUG)
    logging.info('%s starting logging', time.strftime('%d/%m/%Y %I:%M:%S', time.localtime()))
    main()
    logging.info('%s ending logging', time.strftime('%d/%m/%Y %I:%M:%S', time.localtime()))
