import os
from zipfile import ZipFile
from BuildLibs import games
from BuildLibs.buildmap import *

class GrpFile:
    # https://moddingwiki.shikadi.net/wiki/GRP_Format
    # or zip format, at least in the case of Ion Fury
    def __init__(self, filepath):
        self.filepath = filepath
        print('__init__', filepath)
        self.filesize = os.path.getsize(filepath)
        with open(filepath, 'rb') as f:
            self.sig = f.read(12)
        
        print(self.sig)
        if self.sig[:4] == b'PK\x03\x04':
            print('is a zip file')
            self.type = 'zip'
        elif self.sig[:12] == b'KenSilverman':
            print('is a GRP file')
            self.type = 'grp'
        else:
            raise Exception(filepath + ' is an unknown type')
        
        self.game = games.GetGame(filepath)

    def __enter__(self, *args):
        trace( '__enter__', *args, self.__dict__)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        trace( '__exit__', self.__dict__)
        pass

    def getfile(self, name):
        with ZipFile(self.filepath, 'r') as zip:
            with zip.open(name) as file:
                return file.read()

    def getmap(self, name):
        return MapFile(self.game, name, bytearray(self.getfile(name)))

