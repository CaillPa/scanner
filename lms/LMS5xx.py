import socket
import select
import time
import logging
from structs import scanCfg

class LMS5xx:
    """
        Classe permettant de communiquer avec le LMS 5xx
    """
    def __init__(self):
        self.sock = None # tcp socket
        self.__connected = False # active connection flag

    def connect(self, host, port):
        """
            Connection au LMS 5xx
            @param host: adresse IP du telemetre
            @param port: port d'écoute du LMS (2111)
        """
        if not self.__connected:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1)
            try:
                self.sock.connect((host, port))
                self.__connected = True
                logging.info('LMS connecte avec succes')
            except socket.timeout:
                logging.error('Impossible de se connecter au LMS')
                self.__connected = False

    def disconnect(self):
        """
            Deconnection du telemetre (fermeture du socket)
        """
        if self.__connected:
            self.sock.close()
            self.__connected = False
            logging.info('Deconnecte du LMS')

    def isConnected(self):
        """
            Retourne l'etat de la connection (conencte/deconnecte)
            @return: Etat de la connection (True = connecte)
        """
        return self.__connected

    def setTime(self):
        """
            Synchronise l'horloge du telemetre sur celle de l'hote
        """
        tps = time.localtime()
        # conversion de l'heure en hexa
        year = bytes(hex(tps.tm_year)[2:].upper(), encoding='utf8')
        month = bytes(hex(tps.tm_mon)[2:].upper(), encoding='utf8')
        day = bytes(hex(tps.tm_mday)[2:].upper(), encoding='utf8')
        hour = bytes(hex(tps.tm_hour)[2:].upper(), encoding='utf8')
        minute = bytes(hex(tps.tm_min)[2:].upper(), encoding='utf8')
        seconde = bytes(hex(tps.tm_sec)[2:].upper(), encoding='utf8')

        buf = b'\x02sMN LSPsetdatetime '+year+b' '+month+b' '+day+\
            b' '+hour+b' '+minute+b' '+seconde+b' 0000\x03'

        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("setTime(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('setTime(): Trame recue non valide')

        logging.debug('setTime() envoye: %s', buf)
        logging.debug('setTime() recu: %s', rec)

    def setEchoFilter(self, code):
        """
            Change le parametre du filtre d'echo du telemetre
            @param code: code du filtre d'echo
                0 : premier echo
                1 : tous les echos
                2 : dernier echo
        """
        code = bytes(hex(code)[2:].upper(), encoding='utf8')
        buf = b'\x02sWN FREchoFilter '+code+b'\x03'

        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("setEchoFilter(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('setTime(): Trame recue non valide')

        logging.debug('setEchoFilter() envoye: %s', buf)
        logging.debug('setEchoFilter() recu: %s', rec)

    def startMeas(self):
        """
            Apres avoir recu cette commande, le telemetre fait tourner le laser
            et commence a mesurer
        """
        buf = b'\x02sMN LMCstartmeas\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("startMeas(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('startMeas(): Trame recue non valide')

        logging.debug('startMeas() envoye: %s', buf)
        logging.debug('startMeas() recu: %s', rec)

    def stopMeas(self):
        """
            Apres avoir recu cette commande, le telemetre arrete de faire tourner
            le laser et arrete de mesurer
        """
        buf = b'\x02sMN LMCstopmeas\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("stopMeas(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('stopMeas(): Trame recue non valide')

        logging.debug('stopMeas() envoye: %s', buf)
        logging.debug('stopMeas() recu: %s', rec)

    def queryStatus(self):
        """
            Retourne le code d'etat actuel tu telemetre
            @return: code d'etat du LMS 5xx
                0: indefini
                1: initialisation
                2: configuration
                3: ?
                4: tourne
                5: en preparation
                6: pret
                7: en mesure
        """
        buf = b'\x02sRN STlms\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("queryStatus(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('queryStatus(): Trame recue non valide')

        logging.debug('queryStatus() envoye: %s', buf)
        logging.debug('queryStatus() recu: %s', rec)

        return int(rec.split(b'\x20')[2].decode())

    def login(self):
        """
            Authentification. Augmente le niveau d'acces, permet de changer la configuration
        """
        buf = b'\x02sMN SetAccessMode 03 F4724744\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("login(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('login(): Trame recue non valide')

        logging.debug('login() envoye: %s', buf)
        logging.debug('login() recu: %s', rec)

    def getScanCfg(self):
        """
            Retourne la configuration actuelle du scanner
            @rtype: structure scanCfg
            @return: frequence de scan
            @return: resolution du scan
            @return: angle de depart
            @return: angle d'arret
        """
        buf = b'\x02sRN LMPscancfg\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("getScanCfg(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('getScanCfg(): Trame recue non valide')

        logging.debug('getScanCfg() envoye: %s', buf)
        logging.debug('getScanCfg() recu: %s', rec)

        data = rec.split(b'\x20')
        cfg = scanCfg()
        cfg.scaningFrequency = int.from_bytes(data[2], 'big', signed=True)
        cfg.angleResolution = int.from_bytes(data[4], 'big', signed=True)
        cfg.startAngle = int.from_bytes(data[5], 'big', signed=True)
        cfg.stopAngle = int.from_bytes(data[6][0:-1], 'big', signed=True)
        return cfg

    def setScanCfg(self, cfg):
        """
            Change la configuration du scan
            @param cfg: structure scanCfg contenant les parametres
        """
        scaningFrequency = bytes(hex(cfg.scaningFrequency & 0xFFFFFFFF)[2:].upper(), encoding='utf8')
        angleResolution = bytes(hex(cfg.angleResolution & 0xFFFFFFFF)[2:].upper(), encoding='utf8')
        startAngle = bytes(hex(cfg.startAngle & 0xFFFFFFFF)[2:].upper(), encoding='utf8')
        stopAngle = bytes(hex(cfg.stopAngle & 0xFFFFFFFF)[2:].upper(), encoding='utf8')

        buf = b'\x02sMN mLMPsetscancfg '+scaningFrequency+b' 1 '+\
                        angleResolution+b' '+startAngle+b' '+stopAngle+b'\x03'

        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("setScanCfg(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('setScanCfg(): Trame recue non valide')

        logging.debug('setScanCfg() envoye: %s', buf)
        logging.debug('setScanCfg() recu: %s', rec)
        
    def setScanDataCfg(self, cfg):
        """
            Change la configuration d'acquisition des donnees
            @param cfg: structure scanDataCfg contenant les parametres
        """
        remission = bytes(hex(cfg.remission & 0xFF)[2:].upper(), encoding='utf8')
        resolution = bytes(hex(cfg.resolution & 0xFF)[2:].upper(), encoding='utf8')
        encoder = bytes(hex(cfg.encoder & 0xFFFF)[2:].upper(), encoding='utf8')
        position = bytes(hex(cfg.position & 0xFF)[2:].upper(), encoding='utf8')
        deviceName = bytes(hex(cfg.deviceName & 0xFF)[2:].upper(), encoding='utf8')
        timestamp = bytes(hex(cfg.timestamp & 0xFF)[2:].upper(), encoding='utf8')
        outputinterval = bytes(hex(cfg.outputinterval & 0xFFFF)[2:].upper(), encoding='utf8')

        buf = b'\x02sWN LMDscandatacfg 0 0 '+remission+b' '+resolution+b' 0 '+b'0 0 '+\
            position+b' '+deviceName+b' 0 '+timestamp+b' '+outputinterval+b'\x03'

        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("setScanDataCfg(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('setScanDataCfg(): Trame recue non valide')

        logging.info('setScanDataCfg() envoye: %s', buf)
        logging.info('setScanDataCfg() recu: %s', rec)

    def scanContinous(self, start):
        """
            Demarre ou arrete l'acquisition continue de donnees
            (le telemetre envoie des donnees en continu)
            @param start: 1 pour demarrer, 0 pour arreter
        """
        start = bytes(hex(start)[2:].upper(), encoding='utf8')
        buf = b'\x02sEN LMDscandata '+start+b'\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("scanContinous(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('scanContinous(): Trame recue non valide')

        logging.debug('scanContinous() envoye: %s', buf)
        logging.debug('scanContinous() recu: %s', rec)

    def getScanData(self, timeout):
        """
            Retourne une trame de donnees
            @param timeout: temps d'attente max d'une trame
            @return: Trame recue ou None si rien recu avant le timeout
            @rtype: bytes ou None
        """
        try:
            read, _, _ = select.select((self.sock,), (), (), timeout)
            if read:
                rec = self.sock.recv(2048)
                return rec
            else:
                return None
        except InterruptedError:
            return None

    def saveConfig(self):
        """
            Enregistre les parametres dans la memeoire du telemetre
            Les reglages seront gardes apres un redemarrage
        """
        buf = b'\x02sMN mEEwriteall\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("saveConfig(): Tous les octets n'ont pas ete envoyes")

        time.sleep(1)   #writing to EEPROM takes some time
        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('saveConfig(): Trame recue non valide')

        logging.debug('saveConfig() envoye: %s', buf)
        logging.debug('saveConfig() recu: %s', rec)

    def startDevice(self):
        """
            Remet l'appareil en mode mesure apres la configuration
        """
        buf = b'\x02sMN Run\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error("startDevice(): Tous les octets n'ont pas ete envoyes")

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('startDevice(): Trame recue non valide')

        logging.debug('startDevice() envoye: %s', buf)
        logging.debug('startDevice() recu: %s', rec)
