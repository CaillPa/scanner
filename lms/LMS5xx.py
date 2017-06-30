import socket
import select
import time
import logging
from structs import scanCfg

class LMS5xx:
    """
        Class responsible for communicating with LMS5xx device
    """
    def __init__(self):
        self.sock = None
        self.__connected = False

    def connect(self, host, port):
        """
            Connect to the LMS5xx
            :param host: host name or ip address
            :param port: port number
        """
        if not self.__connected:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(1)
            try:
                self.sock.connect((host, port))
                self.__connected = True
                logging.info('LMS connection successful')
            except socket.timeout:
                logging.error('Unable to connect to LMS')
                self.__connected = False

    def disconnect(self):
        """
            Disconnect from the LMS5xx
        """
        if self.__connected:
            self.sock.close()
            self.__connected = False
            logging.info('Disconnected from LMS')

    def isConnected(self):
        """
            Get status of connection
            :return: Status of connection
            :rtype: boolean
        """
        return self.__connected

    def setTime(self):
        """
            Set scanner's internal clock to local time
        """
        tps = time.localtime()
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
            logging.error('setTime(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('setTime(): Invalid packet received')

        logging.debug('setTime() sent: %s', buf)
        logging.debug('setTime() received: %s', rec)

    def setEchoFilter(self, code):
        """
            Set Scanner's echo filter mode
            :param code: echo filter code (integer)
                0 : first echo
                1 : all echos
                2 : last echo
        """
        code = bytes(hex(code)[2:].upper(), encoding='utf8')
        buf = b'\x02sWN FREchoFilter '+code+b'\x03'

        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('setEchoFilter(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('setTime(): Invalid packet received')

        logging.debug('setEchoFilter() sent: %s', buf)
        logging.debug('setEchoFilter() received: %s', rec)

    def startMeas(self):
        """
            After receiving this command LMS5XX unit starts spinning laser and measuring
        """
        buf = b'\x02sMN LMCstartmeas\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('startMeas(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('startMeas(): Invalid packet received')

        logging.debug('startMeas() sent: %s', buf)
        logging.debug('startMeas() received: %s', rec)

    def stopMeas(self):
        """
            After receiving this command LMS5XX unit stop spinning laser and measuring
        """
        buf = b'\x02sMN LMCstopmeas\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('stopMeas(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('stopMeas(): Invalid packet received')

        logging.debug('stopMeas() sent: %s', buf)
        logging.debug('stopMeas() received: %s', rec)

    def queryStatus(self):
        """
            Get current status of LMS5xx device
            :return: status of LMS5xx device
            :rtype: integer
        """
        buf = b'\x02sRN STlms\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('queryStatus(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('queryStatus(): Invalid packet received')

        logging.debug('queryStatus() sent: %s', buf)
        logging.debug('queryStatus() received: %s', rec)

        return int(rec.split(b'\x20')[2].decode())

    def login(self):
        """
            Log into LMS5xx unit
            Increase privilege level, giving ability to change device configuration
        """
        buf = b'\x02sMN SetAccessMode 03 F4724744\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('login(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('login(): Invalid packet received')

        logging.debug('login() sent: %s', buf)
        logging.debug('login() received: %s', rec)

    def getScanCfg(self):
        """
            Get current scan configuration
            :return: scanning frequency
            :return: scanning resolution
            :return: start angle
            :return: stop angle
            :rtype: scanCfg class
        """
        buf = b'\x02sRN LMPscancfg\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('getScanCfg(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('getScanCfg(): Invalid packet received')

        logging.debug('getScanCfg() sent: %s', buf)
        logging.debug('getScanCfg() received: %s', rec)

        data = rec.split(b'\x20')
        cfg = scanCfg()
        cfg.scaningFrequency = int.from_bytes(data[2], 'big', signed=True)
        cfg.angleResolution = int.from_bytes(data[4], 'big', signed=True)
        cfg.startAngle = int.from_bytes(data[5], 'big', signed=True)
        cfg.stopAngle = int.from_bytes(data[6][0:-1], 'big', signed=True)
        return cfg

    def setScanCfg(self, cfg):
        """
            Set scan configuration
            :param cfg: scanCfg class containing scan configuration
        """
        scaningFrequency = bytes(hex(cfg.scaningFrequency & 0xFFFFFFFF)[2:].upper(), encoding='utf8')
        angleResolution = bytes(hex(cfg.angleResolution & 0xFFFFFFFF)[2:].upper(), encoding='utf8')
        startAngle = bytes(hex(cfg.startAngle & 0xFFFFFFFF)[2:].upper(), encoding='utf8')
        stopAngle = bytes(hex(cfg.stopAngle & 0xFFFFFFFF)[2:].upper(), encoding='utf8')

        buf = b'\x02sMN mLMPsetscancfg '+scaningFrequency+b' 1 '+\
                        angleResolution+b' '+startAngle+b' '+stopAngle+b'\x03'

        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('setScanCfg(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('setScanCfg(): Invalid packet received')

        logging.debug('setScanCfg() sent: %s', buf)
        logging.debug('setScanCfg() received: %s', rec)

    def setScanDataCfg(self, cfg):
        """
            Set scan data configuration
            :param cfg: scanDataCfg class containing scan data configuration
        """
        remission = bytes(hex(cfg.remission & 0xFF)[2:].upper(), encoding='utf8')
        resolution = bytes(hex(cfg.resolution & 0xFF)[2:].upper(), encoding='utf8')
        encoder = bytes(hex(cfg.encoder & 0xFFFF)[2:].upper(), encoding='utf8')
        position = bytes(hex(cfg.position & 0xFF)[2:].upper(), encoding='utf8')
        deviceName = bytes(hex(cfg.deviceName & 0xFF)[2:].upper(), encoding='utf8')
        timestamp = bytes(hex(cfg.timestamp & 0xFF)[2:].upper(), encoding='utf8')
        outputinterval = bytes(hex(cfg.outputinterval & 0xFFFF)[2:].upper(), encoding='utf8')

        buf = b'\x02sWN LMDscandatacfg 00 '+remission+b' '+resolution+b' 0 '+\
            encoder+position+b' '+deviceName+b' 0 0 0 0 '+timestamp+b' '+\
            outputinterval+b'\x03'

        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('setScanDataCfg(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('setScanDataCfg(): Invalid packet received')

        logging.debug('setScanDataCfg() sent: %s', buf)
        logging.debug('setScanDataCfg() received: %s', rec)

    def scanContinous(self, start):
        """
            Start or stop continous data acquisition
            :param start: 1 to start, 0 to stop
        """
        start = bytes(hex(start)[2:].upper(), encoding='utf8')
        buf = b'\x02sEN LMDscandata '+start+b'\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('scanContinous(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('scanContinous(): Invalid packet received')

        logging.debug('scanContinous() sent: %s', buf)
        logging.debug('scanContinous() received: %s', rec)

    def getScanData(self, timeout):
        """
            Return single scan message
            :param timeout: max blocking time in second of select() function
            :return: Scan message or None if nothing received within timeout
            :rtype: bytes or None
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
            Parameters are saved in the EEPROM of the LMS and will be available after reboot
        """
        buf = b'\x02sMN mEEwriteall\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('saveConfig(): Not all bytes sent')

        time.sleep(1)   #writing to EEPROM takes some time
        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('saveConfig(): Invalid packet received')

        logging.debug('saveConfig() sent: %s', buf)
        logging.debug('saveConfig() received: %s', rec)

    def startDevice(self):
        """
            The device is returned to measurement mode after configuration
        """
        buf = b'\x02sMN Run\x03'
        sent = self.sock.send(buf)
        if sent < len(buf):
            logging.error('startDevice(): Not all bytes sent')

        rec = self.sock.recv(128)
        if bytes([rec[0]]) != b'\x02':
            logging.warning('startDevice(): Invalid packet received')

        logging.debug('startDevice() sent: %s', buf)
        logging.debug('startDevice() received: %s', rec)

    def extractData(self):
        """
            Reads items in queue and separate them in telegrams
            Telegrams starts with b'\x02' and ends with b'\x03'
            Stores valid telegrams in self.trames
        """
        logging.debug('Entering parsing loop')
        while not self.q.empty() or self.__running:
            while self._parseTelegram():
                pass
            try:
                self.buff = self.buff+bytearray(self.q.get_nowait())
                self.q.task_done()
            except queue.Empty:
                pass
        logging.debug('Leaving parsing loop')


    def _parseTelegram(self):
        """
            Private method used to parse items read from the queue
            Returns true upon parsing a datagram, else False
        """
        minsize = 20
        firstETX = self.buff.find(b'\x03')
        lastSTX = self.buff[:firstETX].rfind(b'\x02')
        if firstETX == -1 or lastSTX == -1:
            return False
        if firstETX - lastSTX < minsize:
            return False

        self.trames.append(self.buff[lastSTX:firstETX+1])
        self.buff = self.buff[firstETX+1:]
        return True
