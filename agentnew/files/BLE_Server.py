import threading
import enum
import multiprocessing
import time
import dbus
import dbus.mainloop.glib
from os import system
import logging

from gi.repository import GLib
from example_advertisement import Advertisement
from example_gatt_server import Service, Characteristic
from example_gatt_server import register_app_cb, register_app_error_cb, unregister_app_cb, unregister_app_error_cb
from ble_transceiver import BLE_Transceiver

import Bluetooth_Server

logger = logging.getLogger("EVC04_Agent.BLE_Server")

BLUEZ_SERVICE_NAME = 'org.bluez'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
DEVICE_IFACE = 'org.bluez.Device1'
HANDSHAKE_SERVICE_UUID = '7d531001-be0a-4827-8204-2974f56ee5d5'
HANDSHAKE_RX_CHARACTERISTIC_UUID = '7d531002-be0a-4827-8204-2974f56ee5d5'
HANDSHAKE_TX_CHARACTERISTIC_UUID = '7d531003-be0a-4827-8204-2974f56ee5d5'
CONFIG_SERVICE_UUID = '7d532001-be0a-4827-8204-2974f56ee5d5'
CONFIG_RX_CHARACTERISTIC_UUID = '7d532002-be0a-4827-8204-2974f56ee5d5'
CONFIG_TX_CHARACTERISTIC_UUID = '7d532003-be0a-4827-8204-2974f56ee5d5'
LOCAL_NAME = 'EVC-04'

HANDSHAKE_REQUEST_STR = "Connect BLE"
HANDSHAKE_ESTABLISHED_STR = "Connected BLE"
DISCONNECTED_STR = "Disconnected BLE"
bus = None


class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    def get_service(self, index):
        return self.services[index]

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
        return response


class TxCharacteristic(Characteristic):

    def __init__(self, bus, index, service, uuid):
        Characteristic.__init__(self, bus, index, uuid,
                                ['notify', 'read'], service)
        self.notifying = False
        self.value = []
        for c in DISCONNECTED_STR:
            self.value.append(dbus.Byte(c.encode()))

    def ReadValue(self, options):
        return self.value

    def send_tx(self, s, isStr):
        self.value = []
        if (isStr == True):
            for c in s:
                self.value.append(dbus.Byte(c.encode()))
        else:
            bList = [s[i:i+1] for i in range(len(s))]
            for b in bList:
                self.value.append(dbus.Byte(b))
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': self.value}, [])

    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True

    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False


class RxCharacteristic(Characteristic):
    def __init__(self, bus, index, service, uuid, callback):
        Characteristic.__init__(self, bus, index, uuid,
                                ['write'], service)
        self.callback = callback

    def WriteValue(self, value, options):
        self.callback(value)


class ChargerBLEApplication(Application):
    class ChargerBLEServiceIndex(enum.Enum):
        Handshake_Service = 0
        Config_Service = 1
        SERVICE_COUNT = 2

    def __init__(self, bus, receiveCallbackFunctions):
        Application.__init__(self, bus)
        self.add_service(HandshakeService(
            bus, self.ChargerBLEServiceIndex.Handshake_Service.value, receiveCallbackFunctions))
        self.add_service(ConfigService(
            bus, self.ChargerBLEServiceIndex.Config_Service.value, receiveCallbackFunctions))


class ChargerBLEAdvertisement(Advertisement):
    def __init__(self, bus, index):
        Advertisement.__init__(self, bus, index, 'peripheral')
        self.add_service_uuid(HANDSHAKE_SERVICE_UUID)
        self.add_local_name(LOCAL_NAME)

    def __del__(self):
        self.Release()


class ConfigService(Service):
    def __init__(self, bus, index, receiveCallbackFunctions):
        self.receiveCallbackFunc = receiveCallbackFunctions[index]
        self.bleTransceiver = BLE_Transceiver(
            self.sendPacketized, self.on_receive)

        Service.__init__(self, bus, index, CONFIG_SERVICE_UUID, True)
        self.add_characteristic(TxCharacteristic(
            bus, self.CharacteristicIndex.TX_Characteristic.value, self, CONFIG_TX_CHARACTERISTIC_UUID))
        self.add_characteristic(RxCharacteristic(bus, self.CharacteristicIndex.RX_Characteristic.value,
                                                 self, CONFIG_RX_CHARACTERISTIC_UUID, self.bleTransceiver.receive))

    def sendPacketized(self, message):
        self.send_tx(message, False)

    def service_send(self, message):
        logger.info("configService send:" + message)
        self.bleTransceiver.send(message)

    def on_receive(self, message):
        logger.info("ConfigService remote:" + message)
        self.receiveCallbackFunc(message)


class HandshakeService(Service):
    def __init__(self, bus, index, receiveCallbackFunctions):
        self.receiveCallbackFunc = receiveCallbackFunctions[index]

        Service.__init__(self, bus, index, HANDSHAKE_SERVICE_UUID, True)
        self.add_characteristic(TxCharacteristic(
            bus, self.CharacteristicIndex.TX_Characteristic.value, self, HANDSHAKE_TX_CHARACTERISTIC_UUID))
        self.add_characteristic(RxCharacteristic(
            bus, self.CharacteristicIndex.RX_Characteristic.value, self, HANDSHAKE_RX_CHARACTERISTIC_UUID, self.on_receive))

    def service_send(self, message):
        logger.info("handshake send:" + str(message))
        self.send_tx(message)

    def on_receive(self, s):
        logger.info('HandshakeService remote: {}'.format(
            bytearray(s).decode()))
        self.receiveCallbackFunc(bytearray(s).decode())


def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'),
                               DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for o, props in objects.items():
        if LE_ADVERTISING_MANAGER_IFACE in props and GATT_MANAGER_IFACE in props:
            return o
    return None


class BLE_Server(threading.Thread, Bluetooth_Server.Bluetooth_Server):

    class AdvertisementState(enum.Enum):
        NotAdvertising = 0
        AdvertisementStarted = 1
        AdvertisementError = 2

    def __init__(self, bHandler, index, advertiseName):
        global LOCAL_NAME
        threading.Thread.__init__(self)
        Bluetooth_Server.Bluetooth_Server.__init__(self, bHandler, index)
        self.bluetoothHandler = bHandler
        self.mainloop = None
        self.app = None
        self.advertisementRegistered = self.AdvertisementState.NotAdvertising
        self.threadAlive = True
        if (advertiseName != None):
            LOCAL_NAME = advertiseName

    def killServer(self):
        self.threadAlive = False

    def activate(self):
        logger.info("BLE active")
        super().activate()

    def deactivate(self):
        logger.info("BLE deactive")
        super().deactivate()
        if (self.mainloop != None):
            if (self.mainloop.is_running()):
                self.mainloop.quit()

    def send(self, data, serviceIndex=ChargerBLEApplication.ChargerBLEServiceIndex.Config_Service):
        if (self.app != None):
            if ((serviceIndex.value < ChargerBLEApplication.ChargerBLEServiceIndex.SERVICE_COUNT.value) and (serviceIndex.value >= 0)):
                if ((serviceIndex == ChargerBLEApplication.ChargerBLEServiceIndex.Config_Service) and
                        (self.bluetoothHandler.isConnected(self.index) == False)):
                    logger.info("Sent message dropped! Not connected to BLE")
                    return
                self.app.get_service(serviceIndex.value).service_send(data)
        else:
            logger.info("Application not set!")

    def on_receive_Config(self, message):
        if ((self.bluetoothHandler != None) and (self.bluetoothHandler.isConnected(self.index))):
            logger.info("BLE_Server on receieve: " + message)
            self.bluetoothHandler.onReceive(message)

    def on_receive_Handshake(self, message):
        if (self.bluetoothHandler != None):
            if (message == HANDSHAKE_REQUEST_STR):
                self.bluetoothHandler.setConnected(self.index)
                self.send(HANDSHAKE_ESTABLISHED_STR,
                          ChargerBLEApplication.ChargerBLEServiceIndex.Handshake_Service)

    def device_property_changed_cb(self, property_name, value, path, interface, device_path):
        global bus
        if property_name != DEVICE_IFACE:
            return

        device = dbus.Interface(bus.get_object(
            BLUEZ_SERVICE_NAME, device_path), DBUS_PROP_IFACE)

        try:
            if (device.Get(DEVICE_IFACE, "Connected") == 0):
                logger.info(DISCONNECTED_STR)
                self.send(
                    DISCONNECTED_STR, ChargerBLEApplication.ChargerBLEServiceIndex.Handshake_Service)
                self.bluetoothHandler.setDisconnected()
        except dbus.exceptions.DBusException as e:
            if e.get_dbus_name() == 'org.freedesktop.DBus.Error.UnknownObject':
                if (self.runServer):
                    logger.info(DISCONNECTED_STR)
                    self.send(
                        DISCONNECTED_STR, ChargerBLEApplication.ChargerBLEServiceIndex.Handshake_Service)
                    self.bluetoothHandler.setDisconnected()
            else:
                logger.info(e)

    def register_ad_cb(self):
        logger.info("BLE advertising started")
        self.advertisementRegistered = self.AdvertisementState.AdvertisementStarted

    def register_ad_error_cb(self, error):
        logger.info('Failed to register BLE advertisement: ' + str(error))
        self.advertisementRegistered = self.AdvertisementState.AdvertisementError
        self.mainloop.quit()

    def run(self):
        global bus
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        adapter = find_adapter(bus)
        if not adapter:
            logger.info('BLE adapter not found')
            return

        service_manager = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter),
            GATT_MANAGER_IFACE)
        ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter),
                                    LE_ADVERTISING_MANAGER_IFACE)

        bus.add_signal_receiver(self.device_property_changed_cb, bus_name=BLUEZ_SERVICE_NAME, signal_name="PropertiesChanged",
                                path_keyword="device_path", interface_keyword="interface")

        self.app = ChargerBLEApplication(
            bus, [self.on_receive_Handshake, self.on_receive_Config])
        adv = ChargerBLEAdvertisement(bus, 0)

        try:
            while self.threadAlive:

                if self.runServer is False:
                    self.runServerChanged.wait()
                    self.runServerChanged.clear()
                    continue

                self.mainloop = GLib.MainLoop()

                ad_manager.RegisterAdvertisement(adv.get_path(), {},
                                                 reply_handler=self.register_ad_cb,
                                                 error_handler=self.register_ad_error_cb)

                service_manager.RegisterApplication(self.app.get_path(), {},
                                                    reply_handler=register_app_cb,
                                                    error_handler=register_app_error_cb)

                self.mainloop.run()
                logger.info("mainloop stopped")
                self.mainloop = None

                if (self.advertisementRegistered is self.AdvertisementState.AdvertisementStarted):
                    service_manager.UnregisterApplication(self.app)
                    ad_manager.UnregisterAdvertisement(adv)
                    self.advertisementRegistered = self.AdvertisementState.NotAdvertising
                    logger.info("BLE advertising stopped")
                else:
                    time.sleep(1)
        finally:
            logger.info("BLE Advertisement Released")
            adv.Release()
