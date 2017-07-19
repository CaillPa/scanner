import argparse
import os
import lzma

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

def parseDatagrams(buff, minsize=50):
    """
        retourne la liste ordonnee des datagrames lus dans buff
        {stx}__minsize bytes__{etx}
    """
    res = [] # liste des datagrames valides
    ETX = 0
    while ETX != -1: # tant qu'on trouve un octet de fin de trame
        STX = buff.find(b'\x02')
        ETX = buff.find(b'\x03')
        if ETX - STX > minsize:
            res.append(buff[STX:ETX].decode())
        buff = buff[ETX+1:]
    return res

def extract(files, srcdir, dstdir, size):
    """
        Extrait le contenu de files en fichier de taille size dans dstdir
    """
    buff = [] # buffer contenant la liste des trames valides lues
    n = 0 # compteur de fichiers
    for fil in files:
        path = os.path.join(srcdir, fil) # chemin complet du fichier courant
        with lzma.open(path) as fic:
            print(path)
            fic = lzma.LZMADecompressor().decompress(fic.read()) # fichier decompresse
            buff.extend(parseDatagrams(fic))
            #del fic # libere la memoire asap

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

def main():
    parser = argparse.ArgumentParser(description="Outil d'extraction des donnees")
    parser.add_argument('-s', '--size', default='100', type=int,\
        help='Taille des fichiers en sortie (en Mo)')
    parser.add_argument('-c', '--count', default='10', type=int,\
        help='Nombre de fichiers a decompresser')
    parser.add_argument('srcdir', nargs=1,\
        help='Dossier contenant les fichiers compresses')
    parser.add_argument('dstdir', nargs=1,\
        help='Dossier dans lequel stocker les fichiers decompresses')

    args = parser.parse_args()
    srcdir = args.srcdir[0]
    dstdir = args.dstdir[0]
    # teste si les chemins sont valides
    if not os.path.isdir(srcdir) or not os.path.isdir(dstdir):
        print('Veuillez rentrer des chemins de dossier valide')
        return

    files = fileList(srcdir)[0:args.count]
    extract(files, srcdir, dstdir, 100)


if __name__ == '__main__':
    main()
