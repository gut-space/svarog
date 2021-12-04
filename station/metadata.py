from typing import Any
from utils.globalvars import METADATA_FILE
import json

class Metadata:
    """This class manages metadata, which store hardware (such as lna or receiver type), software
       (such as recipe used) and run-time parameters (such as frequency or name of the satellite).
       This metadata is locally stored in a JSON file. Some fields of that JSON file will be
       overwritten (e.g. frequency and name of the sat being received), but other will be left
       intact. The overall idea is that the station owner can put any additional information there
       and it will be uploaded when observations are reported. This flexible approach allows
       users to specify whatever they feel is important about their station - antenna orientation,
       type and lenght of the cables, etc.

       The file is stored in ~/.config/svarog/metadata.json. If the file is missing, it is created
       on the first use."""

    filename = METADATA_FILE

    storage = {} # Stores the keys

    def __init__(self, filename = METADATA_FILE):
        self.filename = filename
        self.loadFile()

    def loadFile(self):
        try:
            with open(self.filename, 'r') as myfile:
                data=myfile.read()

            self.storage = json.loads(data)
        except:
            self.createFile()

    def clear(self):
        self.storage = {}

    def createFile(self):
        """Creates metadata file, trying to guess as many defaults as possible."""

        self.clear()
        self.addDefaults()
        self.writeFile()

    def writeFile(self):
        txt = json.dumps(self.storage, indent = 4)
        with open(self.filename, 'w') as outfile:
            outfile.write(txt)

    def getAll(self):
        return self.storage

    def get(self, key: str) -> Any:
        """Returns the parameter or empty string if missing"""
        return self.storage[key] if key in self.storage.keys() else ""

    def addDefaults(self):
        self.add('antenna', 'unknown')
        self.add('antenna-type', 'unknown')
        self.add('receiver', 'RTL-SDR v3')
        self.add('lna', 'none')
        self.add('filter', 'none')

    def add(self, key: str, value: Any):
        self.storage[key] = value

    def delete(self, key: str):
        if key in self.storage:
            self.storage.pop(key, None)
