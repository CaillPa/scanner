import argparse
import os
import re
import csv
import cProfile
#import multiprocessing
#import sys
#from itertools import repeat
from collections import deque
import pandas as pd

def fileList(path):
    """
        Retourne la liste triée par date croissante des fichiers valides
        contenus dans le chemin path
    """
    def isValid(filename):
        """
            Cette fonction teste si le nom d'un fichier est valide
        """
        if filename.startswith('.'):
            return False
        if filename.startswith('_'):
            return False
        if not filename.endswith('.txt'):
            return False
        # TODO rajouter d'autres tests
        return True

    def alphanum_key(s):
        """
            Fonction pour le tri des fichiers (pas important)
        """
        def tryint(s):
            try:
                return int(s)
            except:
                return s
        return [tryint(c) for c in re.split('([0-9]+)', s)]

    # liste des fichiers dans path
    files = os.listdir(os.path.join(os.path.dirname(__file__), path))
    # filtre les fichiers non valides
    valid = list(filter(isValid, files))
    return sorted(valid, key=alphanum_key)

def convert(element):
    """
        Convertis un element d'une trame depuis sa representation hexa vers
        sa representation decimale. Les string ne sont pas modifiees
    """
    try:
        return int(element, 16)
    except ValueError:
        return element

def convertIter(elements):
    """
        Convertis une liste d'element d'une trame depuis sa representation hexa
        vers sa representation decimale. Les string ne sont pas modifiees
    """
    res = deque()
    for elem in elements:
        try:
            res.append(int(elem, 16))
        except ValueError:
            res.append(elem)
    return res

def makeDate(year, month, day, hour, minute, second=0, usec=0):
    """
        Retourne une chaine formattee correspondant aux elements en argument
        (annee, mois, jour, heure, minute, seconde, microseconde)
    """
    try:
        date = pd.Timestamp(year, month, day, hour, minute, second, usec)
    except ValueError:
        print(year, month, day, hour, minute)
        return ''
    return date.strftime('%Y-%m-%d %H:%M:%S.%f')

def getIndices(trame, echo, rssi):
    """
        Retourne un dict contenant les positions de chaque balise DIST et RSSI
        L'index vaut -1 si une balise est manquante
    """
    res = {}
    for i in range(echo):
        key = 'DIST'+str(i+1)
        res[key] = trame.index(key)

    if rssi is False:
        return res

    for i in range(echo):
        key = 'RSSI'+str(i+1)
        res[key] = trame.index(key)
    return res

def convertFile(filename, srcdir, dstdir, used, flag_date):
    """
        Converti le fichier filename present dans srcdir contenant les trames brutes
        en fichier csv stocke dans dstdir
    """
    with open(os.path.join(srcdir, filename), 'r') as fil:
        data = [x.split() for x in fil.read().split('\n')] # liste de trames lues
        if flag_date is True: # si on veut la date
            dates = [[convert(y) for y in x[-8:-1]] for x in data] # conversion en int
            dates = [makeDate(*x) for x in dates] # representation de la date
            data = [[convert(element) for element in [line[i] for i in used]] for line in data] # filtrage + conversion en int
            with open(os.path.join(dstdir, filename.split('.txt')[0]+'.csv'), 'w') as outfile:
                csvwriter = csv.writer(outfile, delimiter=',')
                csvwriter.writerows([[dates[i]]+data[i] for i in range(len(dates))]) # concat de la date et des donnes + ecriture
                # force le ramasse-miettes pour eco de la memoire
                del data
                del dates
        else: # si on veut pas la date
            data = [[convert(element) for element in [line[i] for i in used]] for line in data] # filtrage + conversion en int
            with open(os.path.join(dstdir, filename.split('.txt')[0]+'.csv'), 'w') as outfile:
                csvwriter = csv.writer(outfile, delimiter=',')
                csvwriter.writerows(data)
                del data
        print(filename)
    return

def convertFile2(filename, srcdir, dstdir, used, flag_date):
    """
        Converti le fichier filename present dans srcdir contenant les trames brutes
        en fichier csv stocke dans dstdir
    """
    with open(os.path.join(srcdir, filename), 'r') as fil:
        print('convert entree')
        data = deque()
        if flag_date is True: # si on veut la date
            for line in fil:
                tok = line.split()
                del line
                date = convertIter(tok[-8:-1])
                data.append(date+convertIter([tok[i] for i in used]))

        else: # si on veut pas la date
            for line in fil:
                tok = line.split()
                del line
                data.append(convertIter([tok[i] for i in used]))

        print('convert fin boucle')
        with open(os.path.join(dstdir, filename.split('.txt')[0]+'.csv'), 'w') as outfile:
            csvwriter = csv.writer(outfile, delimiter=',')
            csvwriter.writerows(data)
            del data
        print(filename)
    return

def main():
    parser = argparse.ArgumentParser(description="Outil d'extraction des donnees")
    parser.add_argument('-c', '--count', default='0', type=int,\
        help='Nombre de fichiers a decompresser')
    parser.add_argument('-o', '--offset', default='0', type=int,\
        help='Nombre de fichiers a sauter')
    parser.add_argument('-e', '--echo', default='1', type=int,\
        help="Nombre d'echos a garder")
    parser.add_argument('--RSSI', default='False', action='store_true',\
        help='Inclure les donnees de remission')
    parser.add_argument('--date', default='False', action='store_true',\
        help='Inclure la date de la mesure')
    parser.add_argument('srcdir', nargs=1,\
        help='Dossier source')
    parser.add_argument('dstdir', nargs=1,\
        help='Dossier destination')

    args = parser.parse_args()
    del parser
    srcdir = args.srcdir[0]
    dstdir = args.dstdir[0]
    # teste si les chemins sont valides
    if not os.path.isdir(srcdir) or not os.path.isdir(dstdir):
        print('Veuillez rentrer des chemins de dossier valide')
        return

    # genere la liste des fichiers correspondant aux arguments
    files = fileList(srcdir)
    if args.offset > min(len(files), args.count):
        print('Mauvais offset! Abandon...')
        return
    if args.count is not 0:
        files = files[args.offset:min(args.offset+args.count, len(files))]

    ## recupere le header de la premiere ligne et les indices des colonnes a garder
    with open(os.path.join(srcdir, files[0]), 'r') as fil:
        first = fil.readline() # premiere ligne du fichier
        # verif que les echos voulus sont presents
        if not 'DIST'+str(args.echo) in first:
            print("Nb d'echo demande incompatible avec les donnees, abandon")
            return
        # verif que les donnees de RSSI sont la si on les veut
        if not 'RSSI' in first and args.RSSI is True:
            print("Donnees de remission indisponibles, abandon")
            return

        first = first.split()
        indices = getIndices(first, args.echo, args.RSSI) # indices des flags DIST et RSSI
        nbmeas = int(first[indices['DIST1']+5], 16) # nb de mesure par echo
        header = first[0:indices['DIST1']] # en-tete de trame
        header.extend(first[indices['DIST1']+1:indices['DIST1']+6]) # rajoute les infos de mesure
        del first

        # ecriture du fichier de metadonnees
        with open(os.path.join(srcdir, '_metadata.txt'), 'w') as settings:
            settings.write("Nb. d'echo : "+str(args.echo)+'\n')
            settings.write("Mesure par echo : "+str(convert(header[24]))+'\n')
            if args.RSSI is True:
                settings.write("RSSI : Oui\n")
            else:
                settings.write("RSSI : Non\n")
            settings.write("Scan freq. : "+str(convert(header[16])/100)+' Hz\n')
            settings.write("Measure freq. : "+str(convert(header[17])*100)+' Hz\n')
            settings.write("Scale factor : "+str(header[20])+'(h)\n')
            settings.write("Scale offset : "+str(header[21])+'(h)\n')
            settings.write("Start angle : "+str(header[22])+'(h)\n')
            settings.write("Step size : "+str(header[23])+'(h)\n')
            settings.write("Serial num. : "+str(convert(header[4]))+'\n')
            del header

        ## cree une liste des index des colonnes a garder
        used = [] # indice des mesures a garder
        for i in range(args.echo):
            ind = indices['DIST'+str(i+1)] # position de l'element DISTn dans la trame
            used.extend(range(ind+6, ind+6+nbmeas)) # ajoute les nbmeas indices des mesures de DISTn
        if args.RSSI is True:
            for i in range(args.echo):
                ind = indices['RSSI'+str(i+1)] # position de l'element RSSIn dans la trame
                used.extend(range(ind+6, ind+6+nbmeas)) # ajoute les nbmeas indices des mesures de RSSIn
        del indices
        del nbmeas

    """     Pool de workers qui fait planter mon PC :(
    # liste d'iterables contenant les arguments de convertFile() pour la pool
    pool_args = [[x,] + y for x, y in zip(files, repeat([srcdir, dstdir, used, args.date]))]
    with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
        pool.starmap(convertFile, pool_args)
    """

    for file in files:
        convertFile2(file, srcdir, dstdir, used, args.date)
    
if __name__ == '__main__':
    #main()
    cProfile.run('main()')
