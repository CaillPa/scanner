import argparse
import os
import lzma
from collections import deque

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
        if not filename.endswith('.txt.xz'):
            return False
        # TODO rajouter d'autres tests
        return True

    # liste des fichiers dans path
    files = os.listdir(os.path.join(os.path.dirname(__file__), path))
    # filtre les fichiers non valides
    valid = list(filter(isValid, files))
    return sorted(valid)

def parseDatagrams(buff, echo, RSSI, minsize=100,):
    """
        retourne la liste des trames valides lues dans buff
        {stx}___minsize bytes__{etx}
        verifie la presence des balises DISTn et RSSIn selon les parametres
    """
    dist = 'DIST'+str(echo)

    res = deque() # liste des trames valides
    init = buff.split(b'\x03') # decoupe le buffer autours des ETX

    # donnees avec RSSI
    if RSSI is True:
        rssi = 'RSSI'+str(echo)
        for i in init:
            dat = i.split(b'\x02')[-1].decode() # tramecommencant par un STX le plus pres de l'ETX
            # verifications d'integrite
            if len(dat) < minsize:
                continue
            if not rssi in dat:
                continue
            if not dist in dat:
                continue
            res.append(dat)
        return res
    # donnees sans RSSI
    for i in init:
        dat = i.split(b'\x02')[-1].decode()
        if len(dat) < minsize:
            continue
        if not dist in dat:
            continue
        res.append(dat)
    return res

def main():
    parser = argparse.ArgumentParser(description="Outil d'extraction des donnees")
    parser.add_argument('-s', '--size', default='100', type=int,\
        help='Taille des fichiers en sortie (en Mo)')
    parser.add_argument('-c', '--count', default='-1', type=int,\
        help='Nombre de fichiers a decompresser')
    parser.add_argument('-e', '--echo', default='1', type=int,\
        help="Nombre d'echos dans les donnees")
    parser.add_argument('--RSSI', default='False', action='store_true',\
        help='Extraire les donnees de remission')
    parser.add_argument('srcdir', nargs=1,\
        help='Dossier contenant les fichiers compresses')
    parser.add_argument('dstdir', nargs=1,\
        help='Dossier dans lequel stocker les fichiers decompresses')

    args = parser.parse_args()
    srcdir = args.srcdir[0]
    dstdir = args.dstdir[0]
    size = args.size
    # teste si les chemins sont valides
    if not os.path.isdir(srcdir) or not os.path.isdir(dstdir):
        print('Veuillez rentrer des chemins de dossier valide')
        return

    if args.count == -1:
        files = fileList(srcdir)
    else:
        files = fileList(srcdir)[0:args.count]

    buff = [] # buffer contenant la liste des trames valides lues
    n = 0 # compteur de fichiers
    for fil in files:
        path = os.path.join(srcdir, fil) # chemin complet du fichier courant
        with lzma.open(path) as fic:
            print(path)
            fic = lzma.LZMADecompressor().decompress(fic.read()) # fichier decompresse
            buff.extend(parseDatagrams(fic, args.echo, args.RSSI))

            ## creation des fichiers de taille fixe
            w = len(buff[0]) # longeur en octet d'une trame
            if w*len(buff) > size*10**6: # si la taille du buffer depasse la taille max
                ind = int((size*10**6)/w) # nombre max de lignes pour respecter la taille max
                filename = os.path.join(dstdir, 'out'+str(n)+'.txt')
                print(filename)
                with open(filename, 'w') as out:
                    out.write('\n'.join(buff[:ind]))
                n = n+1
                buff = buff[ind:]
    # enregistre les donnees restantes
    filename = os.path.join(dstdir, 'out'+str(n)+'.txt')
    print(filename)
    with open(filename, 'w') as out:
        out.write('\n'.join(buff[:ind]))
    return


if __name__ == '__main__':
    main()
