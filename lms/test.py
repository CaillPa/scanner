import time
import cProfile
import gzip
import signal
import multiprocessing
import lzma
import logging
from structs import scanDataCfg
from LMS5xx import LMS5xx

def handler(signum, frame):
    global KILLSWITCH
    KILLSWITCH = True
    logging.warning('Received stop signal')

def saveTxt(q):
    path = '/media/usb/'+time.strftime('%d%b%Y%H%M%S', time.localtime())+'.txt'
    with open(path, 'wb') as raw:
        raw.write(b''.join(q))
        raw.close()

def saveGz(q):
    path = '/media/usb/'+time.strftime('%d%b%Y%H%M%S', time.localtime())+'.txt.gz'
    with gzip.open(path, 'wb') as gz:
        gz.write(b''.join(q))
        gz.close()

def makeLZMA(q):
    path = '/media/usb/'+time.strftime('%d%b%Y%H%M%S', time.localtime())+'.txt.xz'
    lzc = lzma.LZMACompressor()
    res = b''
    item = q.get()
    while item is not None:
        res = b''.join([res, lzc.compress(item)])
        item = q.get()
    res = b''.join([res, lzc.flush()])

    with lzma.open(path, 'w') as f:
        f.write(res)
    logging.debug('Quitting process')
    return

KILLSWITCH = False

def main():
    ip = '169.254.74.42'
    port = 2111

    #data frame configuration
    datacfg = scanDataCfg()
    datacfg.outputChannel = 0
    datacfg.remission = 0
    datacfg.resolution = 0
    datacfg.encoder = 0
    datacfg.position = 0
    datacfg.deviceName = 0
    datacfg.timestamp = 1
    datacfg.outputinterval = 1

    #scanner setup
    lms = LMS5xx()
    lms.connect(ip, port)
    lms.login()
    lms.setEchoFilter(1)
    lms.setScanDataCfg(datacfg)
    lms.setTime()
    lms.startDevice()

    signal.signal(signal.SIGUSR1, handler)

    #wait for scanner to be ready
    while lms.queryStatus() < 7:
        pass

    #q = deque()
    lms.scanContinous(1)
    while not KILLSWITCH:
        q = multiprocessing.Queue()
        logging.debug('Spawning new process')
        multiprocessing.Process(target=makeLZMA, args=(q,)).start()
        for _ in range(1000):
            dat = lms.getScanData(0.1)
            if dat is not None:
                q.put(dat)
        q.put(None)
        q.close()

    lms.scanContinous(0)
    lms.stopMeas()

    #nb of elements in trames
    #print(max([len(x.split(b' ')) for x in lms.trames]))
    #print(min([len(x.split(b' ')) for x in lms.trames]))

if __name__ == '__main__':
    logging.basicConfig(filename='lms.log', level=logging.DEBUG)
    logging.info('%s starting logging', time.strftime('%d/%m/%Y %I:%M:%S', time.localtime()))
    main()
    #cProfile.run('main()')
    logging.info('%s ending logging', time.strftime('%d/%m/%Y %I:%M:%S', time.localtime()))
    
