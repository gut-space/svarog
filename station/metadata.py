from typing import Any, Dict
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

    storage = {}  # Stores the keys

    def __init__(self, filename=METADATA_FILE):
        self.filename = filename
        self.loadFile()

    def loadFile(self):
        """Loads file from disk. The filename was specified in constructor.
           The content is parsed and loaded into self.storage"""
        try:
            with open(self.filename, 'r') as myfile:
                data = myfile.read()

            self.storage = json.loads(data)
        except Exception:
            self.createFile()

    def clear(self):
        self.storage = {}

    def createFile(self):
        """Creates metadata file, trying to guess as many defaults as possible."""

        self.clear()
        self.addDefaults()
        self.writeFile()

    def writeFile(self, filename=None):
        """Writes content of the metadata to disk."""
        if not filename:
            filename = self.filename
        with open(filename, 'w') as outfile:
            outfile.write(self.getString())

    def getAll(self) -> Dict:
        """Returns all metadata as dictionary"""
        return self.storage

    def getString(self) -> Dict:
        """Returns all metadata as a string"""
        return json.dumps(self.storage, indent=4)

    def get(self, key: str) -> Any:
        """Returns the parameter or empty string if missing"""
        return self.storage[key] if key in self.storage.keys() else ""

    def addDefaults(self):
        self.set('antenna', 'unknown')
        self.set('antenna-type', 'unknown')
        self.set('receiver', 'RTL-SDR v3')
        self.set('lna', 'none')
        self.set('filter', 'none')

    def set(self, key: str, value: Any):
        self.storage[key] = value

    def delete(self, key: str):
        if key in self.storage:
            self.storage.pop(key, None)
