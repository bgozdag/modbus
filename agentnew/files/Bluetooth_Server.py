import enum
import threading
import logging

logger = logging.getLogger("EVC04_Agent.Bluetooth_Server")


class Bluetooth_Server():

    def __init__(self, bluetoothHandler, index):
        self.bluetoothHandler = bluetoothHandler
        self.index = index
        self.threadAlive = True
        self.runServer = False
        self.runServerChanged = threading.Event()

    def getIndex(self):
        return self.index

    def send(self, data):
        logger.info("Not supported")

    def deactivate(self):
        if (self.runServer == True):
            self.runServer = False
            self.runServerChanged.set()

    def activate(self):
        if (self.runServer == False):
            self.runServer = True
            self.runServerChanged.set()

    def killServer(self):
        self.threadAlive = False
