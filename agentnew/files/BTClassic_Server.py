from bluetooth import *
import time
import json
import threading
import multiprocessing
from os import system
import logging

import Bluetooth_Server

logger = logging.getLogger("EVC04_Agent.BTClassic_Server")


class BTClassic_Server(threading.Thread, Bluetooth_Server.Bluetooth_Server):

    def __init__(self, bHandler, index):
        threading.Thread.__init__(self)
        Bluetooth_Server.Bluetooth_Server.__init__(self, bHandler, index)
        self.btClassicListeningThread = None
        self.connectionRoutineInstance = None
        self.p = None

    def send(self, data):
        if (self.dataToSend != None):
            self.dataToSend.send(data)
        else:
            logger.info(
                "BT Classic not ready to send! Dropping message: " + str(data))

    def on_receive(self, message):
        if (self.bluetoothHandler != None):
            self.bluetoothHandler.onReceive(message)

    def activate(self):
        logger.info("BT Classic active")
        super().activate()

    def deactivate(self):
        logger.info("BT Classic deactive")
        super().deactivate()
        if (self.p != None):
            self.p.terminate()

    def run(self):

        while(self.threadAlive):
            if (self.runServer is False):
                self.runServerChanged.wait()
                self.runServerChanged.clear()
                continue

            server_sock = None
            try:
                server_sock = BluetoothSocket(RFCOMM)
                server_sock.bind(("", PORT_ANY))
                server_sock.listen(1)
                try:
                    server_mac_addr = str(
                        read_local_bdaddr()).strip('[]').strip('\'')
                except:
                    # No BT module, stop
                    logger.info("Problem with BT Classic!")
                    self.deactivate()
                logger.info("MAC: %s" % server_mac_addr)

                uuid = "e9dca046-c27e-406c-8fd0-6d02fa38a61c"
                # uuid = "7d530001-be0a-4827-8204-2974f56ee5d5"

                advertise_service(server_sock, "EVC04",
                                  service_id=uuid,
                                  service_classes=[uuid, SERIAL_PORT_CLASS],
                                  profiles=[SERIAL_PORT_PROFILE]
                                  # protocols = [ OBEX_UUID ]
                                  )

                # Turn BT discoverable on
                system("hciconfig hci0 piscan")

                # creating a pipe
                btConnection_conn, server_conn = multiprocessing.Pipe()
                self.dataToSend, btConnection_sendData = multiprocessing.Pipe()

                connectionListenerThread = threading.Thread(
                    target=self.connectionListener, args=[server_sock, server_conn])
                connectionListenerThread.setDaemon(True)
                connectionListenerThread.start()

                self.p = multiprocessing.Process(target=self.connection, args=[
                                                 server_sock, btConnection_sendData, btConnection_conn])
                logger.info("BT Classic Connection process started")
                self.p.start()
                self.p.join()
                self.p = None
                logger.info("BT Classic Connection process joined")
                btConnection_conn.close()
                btConnection_sendData.close()
                self.dataToSend.close()
                self.dataToSend = None
                connectionListenerThread.join()
                server_conn.close()

            finally:
                if (server_sock != None):
                    server_sock.close()

    def connectionListener(self, server_socket, server_conn):
        try:
            connectionIndex = server_conn.recv()
            self.bluetoothHandler.setConnected(connectionIndex)
            # stop advertising
            system("hciconfig hci0 pscan")
        except EOFError:
            return

        try:
            while True:
                message = server_conn.recv()
                self.on_receive(message)
        except EOFError:
            logger.info("Disconnected BT Classic")
            self.bluetoothHandler.setDisconnected()

    #!!! This function works on a different process, hence the logger causes side-affect;
    # therefore the prints should stay as is !!!
    def connection(self, server_sock, sendPipe, dataPipe):
        port = server_sock.getsockname()[1]
        print("Waiting for connection on RFCOMM channel %d" % port)
        client_sock, client_info = server_sock.accept()
        dataPipe.send(self.index)
        print("Connected BT Classic from {}".format(client_info))
        try:
            connectionListenerThread = threading.Thread(
                target=self.socketListener, args=[client_sock, sendPipe])
            connectionListenerThread.start()

            while True:
                msgBT = str(client_sock.recv(4096), 'utf8')
                if len(msgBT) == 0:
                    break
                print("RECEIVED: " + msgBT)
                dataPipe.send(msgBT)
                # self.on_receive(msgBT)
        except IOError:
            return
        finally:
            if (client_sock != None):
                client_sock.close()

    def socketListener(self, client_sock, sendPipe):
        while True:
            client_sock.send(sendPipe.recv())
