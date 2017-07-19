"""
    Enregistrement des donnees d'utilisation CPU, utilisation memoire et temperature
    Lancer en tache de fond, envoyer SIGUSR1 pour arreter proprement
"""

import subprocess
import signal
import time

STOP = False

def signalHandler(a, b):
    global STOP
    STOP = True

def main():
    fic = open('telemetry.log', 'w')
    signal.signal(signal.SIGUSR1, signalHandler)
    while not STOP:
        cpu = subprocess.Popen('uptime', shell=True, stdout=subprocess.PIPE)
        cpu = cpu.communicate()[0].decode()
        fic.write('##### CPU #####\n')
        fic.write(cpu)
        fic.write('##### /CPU #####\n')

        mem = subprocess.Popen('free -oh', shell=True, stdout=subprocess.PIPE)
        mem = mem.communicate()[0].decode()
        fic.write('##### MEM #####\n')
        fic.write(mem)
        fic.write('##### /MEM #####\n')

        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as tmp:
            fic.write('##### TMP #####\n')
            fic.write(tmp.read())
            fic.write('##### /TMP #####\n')

        time.sleep(60)

    fic.close()

if __name__ == '__main__':
    main()
