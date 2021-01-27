from BLE_Server import BLE_Server
from BTClassic_Server import BTClassic_Server
import Bluetooth_Server
from definitions import MessageTypes, Requester, BluetoothInterfaceError
from bluetooth import *
from os import system
import json
import time
import logging
import sqlite3
import traceback

logger = logging.getLogger("EVC04_Agent.bluetooth_handler")
VFACTORY_DB_PATH = "/run/media/mmcblk1p3/vfactory.db"
bluetooth_configuration = "/etc/bluetooth/main.conf"

class BluetoothHandler(Requester):

    def __init__(self):
        super().__init__()
        logger.info("Bluetooth handler created")
        self.running = True
        self.bluetoothServers = []
        self.connectedBluetoothServerIndex = None

        bluetooth_advertising_name = self.getBluetoothConfiguration("Name")
        
        btClassicServerThread = BTClassic_Server(self, 0)
        btClassicServerThread.setDaemon(True)
        btClassicServerThread.start()
        self.bluetoothServers.append(btClassicServerThread)
        bleServerThread = BLE_Server(self, 1, bluetooth_advertising_name)
        bleServerThread.setDaemon(True)
        bleServerThread.start()
        self.bluetoothServers.append(bleServerThread)

    def __del__(self):
        logger.info("Bluetooth handler destroyed")
        for server in self.bluetoothServers:
            server.killServer()
        self.stop()

    @classmethod
    def get_local_bdaddr(cls):
        try:
            local_bdaddr = str(read_local_bdaddr()).strip("[]'").strip('\'')
            return local_bdaddr
        except Exception as e:
            logger.error("Error reading local bdaddr {}".format(str(e)))

        return ''

    def setConnected(self, index):
        if (index >= len(self.bluetoothServers)):
            logger.info("no bluetoothServer")
            self.connectedBluetoothServerIndex = None
        else:
            try:
                self.connectedBluetoothServerIndex = index
                msg = {
                    "status": "Connected"
                }
                msg = json.dumps(msg)
                logger.info(msg)
                self.mediator.send(msg, self, MessageTypes.BLUETOOTH_STATUS)
                for server in self.bluetoothServers:
                    if (server.getIndex() != index):
                        server.deactivate()
            except ValueError:
                logger.info("Service not found!")
                self.setDisconnected()

    def isConnected(self, index):
        if (self.connectedBluetoothServerIndex == None):
            return False
        elif (self.connectedBluetoothServerIndex == index):
            return True
        else:
            return False

    def setDisconnected(self):
        msg = {
            "status": "Disconnected"
        }
        msg = json.dumps(msg)
        self.mediator.send(msg, self, MessageTypes.BLUETOOTH_STATUS)
        self.connectedBluetoothServerIndex = None
        self.__activateAll()

    def __activateAll(self):
        if (self.running == True):
            for server in self.bluetoothServers:
                server.activate()

    ### PUBLIC API ###
    def start(self):
        logger.info("Bluetooth handler start received")
        self.running = True
        self.__activateAll()

    def stop(self):
        logger.info("Bluetooth handler stop received")
        os.system("echo disconnect | bluetoothctl")
        self.running = False
        self.connectedBluetoothServerIndex = None
        for server in self.bluetoothServers:
            server.deactivate()

    def onReceive(self, message):
        logger.info("Message received (BTHandler):" + message)
        try:
            self.mediator.send(message, self, MessageTypes.BLUETOOTH_MESSAGE)
        except Exception as e:
            logger.info("BTHandler onReceive: Exception occured: " + str(e))

    def sendMessage(self, message, message_type):
        logger.info("Message sent (BTHandler): " + message)
        if (self.connectedBluetoothServerIndex != None):
            self.bluetoothServers[self.connectedBluetoothServerIndex].send(
                message)
        else:
            logger.info("Message dropped!")

    # Change a key-value inside /etc/bluetooth/main.conf bluetooth configuration file
    # returns True if successful else False
    @classmethod
    def setBluetoothConfiguration(cls, key, value):
        # Read file contents
        try:
            filePtr = open(bluetooth_configuration, "r")
            fileString = filePtr.read()
            filePtr.close()

            startingIndex = fileString.find('{} = '.format(str(key)))
            if startingIndex == -1:
                return False

            # Remove comment indicator if exists
            if fileString[startingIndex - 1] == '#':
                fileString = fileString[:startingIndex - 1] + fileString[startingIndex:]
                startingIndex -= 1  # Shift starting index by 1 since a char is removed

            i = int(startingIndex)
            ch = fileString[i]

            # Count characters until end of line
            while ch != '\n':
                ch = fileString[i]
                i += 1

            # Add desired configuration string to conf file string
            newFileString = fileString[:startingIndex] + "{} = {}".format(str(key), str(value)) + fileString[i - 1:]

            # Replace old string with newly constructed string
            filePtr = open(bluetooth_configuration, "w")
            filePtr.write(newFileString)
            filePtr.close()

            logger.info("Bluetooth configuration file key '{}' is successfully set to '{}'".format(str(key), str(value)))
            return True

        except Exception as e:
            logger.error("Error setting bluetooth configuration via conf file: {}".format(str(e)))
            return False

    # Get a bluetooth configuration inside configuration file in path /etc/bluetooth/main.conf
    @classmethod
    def getBluetoothConfiguration(cls, key):
        # Read file contents
        try:
            filePtr = open(bluetooth_configuration, "r")
            fileString = filePtr.read()
            filePtr.close()

            stringToFind = '{} = '.format(str(key))
            startingIndex = fileString.find(stringToFind)
            if startingIndex == -1:
                return None

            i = int(startingIndex + len(stringToFind))
            ch = fileString[i]
            value = ""
            # Append characters until end of line
            while ch != '\n':
                value += ch
                i += 1
                ch = fileString[i]

            return value

        except Exception as e:
            logger.error("Error getting bluetooth configuration via conf file: {}".format(str(e)))
            return None
