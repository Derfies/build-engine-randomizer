from BuildLibs.buildmap import MapFile
from BuildLibs.games import GameMapSettings


settings = GameMapSettings()
m = MapFile(settings, 'test', bytearray())
m.WriteData()

with open('out.map', 'wb') as f:
    f.write(m.data)
