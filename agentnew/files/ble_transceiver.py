import threading
# import crcmod
import binascii
import logging

logger = logging.getLogger("EVC04_Agent.ble_transceiver")
PACKET_ID_LENGTH = 1
MESSAGE_LAST_PACKET_ID_LENGTH = PACKET_ID_LENGTH
MESSAGE_DATA_LENGTH = 100
CRC_LENGTH = 0
MESSAGE_LENGTH = PACKET_ID_LENGTH + \
    MESSAGE_LAST_PACKET_ID_LENGTH + MESSAGE_DATA_LENGTH + CRC_LENGTH
logger.info("Message size will be " + str(MESSAGE_LENGTH))
# crc16 = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0x0000, xorOut=0x0000)


def incrementPacketIndex(packetId, incrementCount=1):
    global PACKET_ID_LENGTH

    packetId += incrementCount
    upperMostPacketId = (2 ** 8) ** PACKET_ID_LENGTH
    if (incrementCount >= upperMostPacketId):
        logger.info("PACKET_ID_LENGTH:" + str(PACKET_ID_LENGTH) +
                    " is low! Tried to increment " + str(incrementCount) + " packets!!!")
        raise Exception

    if (packetId >= upperMostPacketId):
        packetId -= upperMostPacketId
    return packetId


class BLE_Transceiver():
    def __init__(self, senderFunc, recieveCallback):
        self.senderFunc = senderFunc
        self.receiveCallback = recieveCallback
        self.packetIdToBeSent = 0
        self.receivedMessage = bytearray()
        self.expectedPacketId = 0

    def send(self, message):
        # global crc16
        global MESSAGE_DATA_LENGTH, incrementPacketIndex
        logger.info("ble_sender send:" + message)

        splitMessage = [(message[i:i+MESSAGE_DATA_LENGTH])
                        for i in range(0, len(message), MESSAGE_DATA_LENGTH)]
        lastIndex = incrementPacketIndex(
            self.packetIdToBeSent, len(splitMessage) - 1)
        for mes in splitMessage:
            bulkMessage = b"".join([self.packetIdToBeSent.to_bytes(
                1, "little"), lastIndex.to_bytes(1, "little"), bytes(mes, 'ascii')])
            # bulkMessage = b"".join([bulkMessage,crc16(bulkMessage).to_bytes(2,"little")])
            self.packetIdToBeSent = incrementPacketIndex(self.packetIdToBeSent)
            logger.info("Sent Message: {}".format(
                binascii.hexlify(bulkMessage)))
            self.senderFunc(bulkMessage)
        self.packetIdToBeSent = 0

    def receive(self, message):
        # logger.info("ble_receiver received:" + bytearray(message).decode())
        global MESSAGE_LENGTH, PACKET_ID_LENGTH, MESSAGE_LAST_PACKET_ID_LENGTH, CRC_LENGTH, incrementPacketIndex

        # crcPreCalculate = int.from_bytes(message[-CRC_LENGTH :], "little")
        packetId = int.from_bytes(message[0:PACKET_ID_LENGTH], "little")
        lastPacketId = int.from_bytes(
            message[PACKET_ID_LENGTH: PACKET_ID_LENGTH + MESSAGE_LAST_PACKET_ID_LENGTH], "little")

        logger.info("packetId:" + str(packetId) + " expected:" +
                    str(self.expectedPacketId) + " lastPacket:" + str(lastPacketId))
        if (self.expectedPacketId != packetId):
            logger.info("Unexpected Packet Id! Expected:" +
                        str(self.expectedPacketId) + " Received:" + str(packetId))
            self.expectedPacketId = 0
            logger.info("Packet dropped! Message: {}".format(
                binascii.hexlify(message)))
            self.receivedMessage = bytearray()
            return

        self.expectedPacketId = incrementPacketIndex(self.expectedPacketId)

        # crcCalculated = crc16(message[0:-CRC_LENGTH])
        # if (crcCalculated != crcPreCalculate):
        #     logger.info("CRC mismatch! Calculated:" + str(crcCalculated) + " Received:" + str(crcPreCalculate))
        #     logger.info("Packet dropped! Message:", binascii.hexlify(message))
        #     self.broadcastMessage = ""
        #     self.messageParserLock.release()
        #     return
        logger.info("receivedMessagePre:" + self.receivedMessage.decode())
        if (CRC_LENGTH > 0):
            self.receivedMessage += bytearray(
                message)[PACKET_ID_LENGTH + MESSAGE_LAST_PACKET_ID_LENGTH: -CRC_LENGTH]
        else:
            self.receivedMessage += bytearray(
                message)[PACKET_ID_LENGTH + MESSAGE_LAST_PACKET_ID_LENGTH:]

        logger.info("receivedMessageAfter:" + self.receivedMessage.decode())
        if (packetId == lastPacketId):
            self.receiveCallback(self.receivedMessage.decode('ascii'))
            self.receivedMessage = bytearray()
            self.expectedPacketId = 0
