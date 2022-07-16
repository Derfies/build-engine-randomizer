from datetime import datetime
import os
from zipfile import ZipFile
from BuildLibs import games
from BuildLibs.buildmap import *
from BuildLibs.confile import ConFile
from BuildLibs.SpoilerLog import SpoilerLog
import traceback
import locale

try:
    locale.setlocale(locale.LC_ALL, '')
except Exception as e:
    error('Failed to set locale', e, '\n', traceback.format_exc())


class GrpFile:
    # https://moddingwiki.shikadi.net/wiki/GRP_Format
    # or zip format, at least in the case of Ion Fury
    def __init__(self, filepath):
        self.filepath = filepath
        info(filepath)
        self.files = {}
        self.filesize = os.path.getsize(filepath)
        with open(filepath, 'rb') as f:
            self.sig = f.read(12)

        trace(self.sig)
        if self.sig[:4] == b'PK\x03\x04':
            debug('is a zip file')
            self.type = 'zip'
            self.GetFilesInfoZip()
        elif self.sig[:12] == b'KenSilverman':
            debug('is a GRP file')
            self.type = 'grp'
            self.GetFilesInfoGrp()
        else:
            raise Exception(filepath + ' is an unknown type, size: ', self.filesize)

        cons = self.GetAllFilesEndsWith('.con')
        self.game = games.GetGame(filepath)
        if not self.game:
            info(repr(cons))
            raise Exception('unidentified game')

        self.conSettings = games.GetGameConSettings(self.game)
        if not self.conSettings:
            raise Exception('missing GameConSettings', self.game, filepath)
        elif not self.conSettings.conFiles:
            warning("This game is missing CON file randomization", self.game, filepath)
            for con in cons:
                self.ExtractFile('temp/', con)
        else:
            for con in self.conSettings.conFiles:
                if con not in cons:
                    warning('file not found', con)

        self.mapSettings = games.GetGameMapSettings(self.game)
        if not self.mapSettings.swappableItems:
            warning("This game doesn't have any swappableItems", self.game, filepath)
        if not self.mapSettings.swappableEnemies:
            warning("This game doesn't have any swappableEnemies", self.game, filepath)


    def GetFilesInfoZip(self) -> None:
        with ZipFile(self.filepath, 'r') as zip:
            for f in zip.infolist():
                self.files[f.filename] = { 'size': f.file_size }

    def GetFilesInfoGrp(self) -> None:
        with open(self.filepath, 'rb') as f:
            f.seek(12)
            data = f.read(4)
            (numFiles,) = unpack('<I', data)
            trace('numFiles:', numFiles)
            offset = 16 + 16*numFiles
            for i in range(numFiles):
                data = f.read(16)
                name = data[:12].strip(b'\x00').decode('ascii')
                (size,) = unpack('<I', data[12:16])
                trace(name, size)
                self.files[name] = {
                    'size': size,
                    'offset': offset
                }
                offset += size

    def getFileHandle(self):
        if self.type == 'zip':
            return ZipFile(self.filepath, 'r')
        else:
            return open(self.filepath, 'rb')

    def getfileZip(self, name, filehandle) -> bytes:
        if name not in self.files:
            raise Exception('file not found in GRP/ZIP', name, len(self.files))

        if filehandle:
            with filehandle.open(name) as f:
                return f.read()

        with ZipFile(self.filepath, 'r') as zip:
            with zip.open(name) as file:
                return file.read()

    def getfileGrp(self, name, filehandle) -> bytes:
        if name not in self.files:
            raise Exception('file not found in GRP', name, len(self.files))

        if filehandle:
            filehandle.seek(self.files[name]['offset'])
            return filehandle.read(self.files[name]['size'])

        with open(self.filepath, 'rb') as f:
            f.seek(self.files[name]['offset'])
            return f.read(self.files[name]['size'])

    def GetAllFilesEndsWith(self, postfix) -> list:
        matches = []
        postfix = postfix.lower()
        for f in self.files.keys():
            if f.lower().endswith(postfix):
                matches.append(f)
        matches.sort()
        return matches

    def getfile(self, name, filehandle=None) -> bytes:
        if name in self.game.path_overrides:
            name = self.game.path_overrides[name]
            gamedir = os.path.dirname(self.filepath)
            if '../' in name:
                name = name.replace('../', gamedir + '/')
                with open(name, 'rb') as file:
                    return file.read()

        if self.type == 'zip':
            return self.getfileZip(name, filehandle)
        else:
            return self.getfileGrp(name, filehandle)

    def getmap(self, name, file) -> MapFile:
        return MapFile(self.game, name, bytearray(self.getfile(name, file)))

    def GetOutputFiles(self, basepath:str='') -> tuple:
        gamedir = os.path.dirname(self.filepath)
        if not basepath:
            basepath = gamedir
        outs = []
        for o in list(self.conSettings.conFiles.keys()) + self.GetAllFilesEndsWith('.map'):
            outs.append(o)
        return (basepath, outs)

    # basepath is only used by tests
    def _Randomize(self, seed:int, settings:dict, basepath:str, spoilerlog, filehandle) -> None:
        spoilerlog.write(datetime.now().strftime('%c') + ': Randomizing with seed: ' + str(seed) + ', settings:\n    ' + repr(settings) + '\n')
        spoilerlog.write(repr(self.game) + '\n\n')

        for (conName,conSettings) in self.conSettings.conFiles.items():
            data = self.getfile(conName, filehandle)
            text = data.decode('iso_8859_1')
            con:ConFile = ConFile(self.game, conSettings, conName, text)
            con.Randomize(seed, settings, spoilerlog)
            out = os.path.join(basepath, conName)
            pathlib.Path(os.path.dirname(out)).mkdir(parents=True, exist_ok=True)
            with open(out, 'w') as f:
                text = con.GetText()
                size = locale.format_string('%d bytes', len(text), grouping=True)
                spoilerlog.write(out + ' is ' + size)
                f.write(text)

        maps = self.GetAllFilesEndsWith('.map')
        mapRenames = {}
        if settings.get('grp.reorderMaps'):
            rng = random.Random(crc32('grp reorder maps', seed))
            mapRenames = dict(zip(maps, rng.sample(maps, k=len(maps))))
        for mapname in maps:
            map:MapFile = self.getmap(mapname, filehandle)
            map.Randomize(seed, settings, spoilerlog)
            writename = mapRenames.get(mapname, mapname)
            out = os.path.join(basepath, writename)
            pathlib.Path(os.path.dirname(out)).mkdir(parents=True, exist_ok=True)
            with open(out, 'wb') as f:
                data = map.GetData()
                size = locale.format_string('%d bytes', len(data), grouping=True)
                spoilerlog.write(mapname + ' writing to ' + out + ', is ' + size)
                f.write(map.GetData())

        spoilerlog.write('\n')
        spoilerlog.write(repr(self.conSettings))
        spoilerlog.write('\n')
        spoilerlog.write(repr(self.mapSettings))


    def Randomize(self, seed:int, settings:dict={}, basepath:str='') -> None:
        gamedir = os.path.dirname(self.filepath)
        if not basepath:
            basepath = gamedir
        out = os.path.join(basepath, 'Randomizer.html')
        pathlib.Path(os.path.dirname(out)).mkdir(parents=True, exist_ok=True)
        with self.getFileHandle() as filehandle, SpoilerLog(out) as spoilerlog:
            try:
                return self._Randomize(seed, settings, basepath, spoilerlog, filehandle)
            except:
                error(self.game, ', seed: ', seed, ', settings: ', settings, ', basepath: ', basepath)
                error('files: ', self.files)
                raise

    def ExtractFile(self, outpath, name, filehandle=None) -> None:
        pathlib.Path(outpath).mkdir(parents=True, exist_ok=True)
        data = self.getfile(name, filehandle)
        trace(name, len(data))
        with open(outpath + name, 'wb') as o:
            o.write(data)

    def ExtractAll(self, outpath) -> None:
        with self.getFileHandle() as filehandle:
            for name in self.files.keys():
                self.ExtractFile(outpath, name, filehandle)


def CreateGrpFile(frompath: str, outpath: str, filenames: list) -> None:
    outfile = open(outpath, 'wb')
    outfile.write(b'KenSilverman')
    outfile.write(pack('<I', len(filenames)))

    datas = []
    for name in filenames:
        with open(frompath + name, 'rb') as f:
            d = f.read()
            datas.append(d)
            outfile.write(pack('<12sI', name.encode('ascii'), len(d)))

    for d in datas:
        outfile.write(d)

    outfile.close()
