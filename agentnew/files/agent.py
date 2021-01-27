from abc import ABC, abstractmethod
from ctypes import c_ubyte
import zmq
import serial
import threading
import time
import os
import queue
import json
import uuid
import traceback


import gpio_controller
import subprocess
import datetime
import logging
from logging.config import fileConfig

from configuration_manager import ConfigurationManager, WEBCONFIG_DATABASE, \
    DEBUG, AGENT_DATABASE, VFACTORY_DATABASE
from drive_green_manager import DriveGreenManager
from definitions import MessageTypes, Dealer, AuthorizationStatus, \
    AuthorizationResponse, ChargePointStatus, ChargePointExtendedStatus, \
    ChargePointErrorCode, ByteIndex, AcpwCommandId, ChargePointError, \
    Requester, Mediator, ControlPilotStates, ProximityPilotStates, \
    ChargeSessionStatus, ChargePointAvailability, ChargeStationStatus, \
    Status, MeterType, OtaStatus, OtaType, AcpwOtaStatus, FirmwareUpdateStatus, \
    PeripheralRequest, PhaseType, CurrentOfferedToEvReason
import sqlite3
from bluetooth_handler import BluetoothHandler
from zipfile import ZipFile
import sys

TAG = "EVC04_Agent:"
AUTHORIZATION_TIMEOUT = 60.0

FACTORY_RESET_PIN = 117

logger = logging.getLogger("EVC04_Agent")


class StreamToLogger(object):

    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.log_level, line.rstrip())
            
    def flush(self): 
        pass
         

class MessageMediator(Mediator):

    def __init__(self, charge_station, acpw_handler,
                 internal_meter, rfid_reader, zmq_message_handler,
                 configuration_manager, drive_green_manager, bluetooth_handler=None):

        self._charge_station = charge_station
        if charge_station is not None:
            self._charge_station.mediator = self

        self._acpw_handler = acpw_handler
        if acpw_handler is not None:
            self._acpw_handler.mediator = self

        self._internal_meter = internal_meter
        if internal_meter is not None:
            self._internal_meter.mediator = self

        self._rfid_reader = rfid_reader
        if rfid_reader is not None:
            self._rfid_reader.mediator = self

        self._zmq_message_handler = zmq_message_handler
        if zmq_message_handler is not None:
            self._zmq_message_handler.mediator = self

        self._configuration_manager = configuration_manager
        if configuration_manager is not None:
            self._configuration_manager.mediator = self

        self._drive_green_manager = drive_green_manager
        if drive_green_manager is not None:
            self._drive_green_manager.mediator = self

        self._bluetooth_handler = bluetooth_handler
        if bluetooth_handler is not None:
            self._bluetooth_handler.mediator = self

    @property
    def charge_station(self):
        return self._charge_station

    @charge_station.setter
    def charge_station(self, value):
        self._charge_station = value
        if value is not None:
            self._charge_station.mediator = self

    @property
    def acpw_handler(self):
        return self._acpw_handler

    @acpw_handler.setter
    def acpw_handler(self, value):
        self._acpw_handler = value
        if value is not None:
            self._acpw_handler.mediator = self

    @property
    def internal_meter(self):
        return self._internal_meter

    @internal_meter.setter
    def internal_meter(self, value):
        self._internal_meter = value
        if value is not None:
            self._internal_meter.mediator = self

    @property
    def rfid_reader(self):
        return self._rfid_reader

    @rfid_reader.setter
    def rfid_reader(self, value):
        self._rfid_reader = value
        if value is not None:
            self._rfid_reader.mediator = self

    @property
    def zmq_message_handler(self):
        return self._zmq_message_handler

    @zmq_message_handler.setter
    def zmq_message_handler(self, value):
        self._zmq_message_handler = value
        if value is not None:
            self._zmq_message_handler.mediator = self

    @property
    def configuration_manager(self):
        return self._configuration_manager

    @configuration_manager.setter
    def configuration_manager(self, value):
        self._configuration_manager = value
        if value is not None:
            self._configuration_manager.mediator = self

    @property
    def drive_green_manager(self):
        return self._drive_green_manager

    @drive_green_manager.setter
    def drive_green_manager(self, value):
        self._drive_green_manager = value
        if value is not None:
            self._drive_green_manager.mediator = self

    @property
    def bluetooth_handler(self):
        return self._bluetooth_handler

    @bluetooth_handler.setter
    def bluetooth_handler(self, value):
        self._bluetooth_handler = value
        if value is not None:
            self.bluetooth_handler.mediator = self

    def send(self, message, requester, message_type):

        if requester == self.charge_station:
            # if messageType == "zmq":
            #     self.zmqMessageHandler.sendToSocket(message)

            if message_type == MessageTypes.ACPW:
                self.acpw_handler.send_to_acpw(message)
            elif message_type == MessageTypes.AUTHORIZATION_RESPONSE:
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
                if self.drive_green_manager is not None:
                    self.drive_green_manager.get_message(message, message_type)
            elif message_type == MessageTypes.AUTHORIZATION_STATUS:
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
                self.zmq_message_handler.send_to_socket(message, Dealer.OCPP)
                self.zmq_message_handler.send_to_socket(message, Dealer.MODBUSTCP)
                if self.drive_green_manager is not None:
                    self.drive_green_manager.get_message(message, message_type)
            elif message_type == MessageTypes.AUTHORIZE:
                self.zmq_message_handler.send_to_socket(message, Dealer.OCPP)
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)

            elif message_type == MessageTypes.STATUS_NOTIFICATION:
                self.zmq_message_handler.send_to_socket(message, Dealer.OCPP)
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
                self.zmq_message_handler.send_to_socket(message, Dealer.MODBUSTCP)
                if self.drive_green_manager is not None:
                    self.drive_green_manager.get_message(message, message_type)
            elif message_type == MessageTypes.METER_VALUES:
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
                self.zmq_message_handler.send_to_socket(message, Dealer.MODBUSTCP)
                if self.drive_green_manager is not None:
                    self.drive_green_manager.get_message(message, message_type)
            elif message_type == MessageTypes.CHARGE_SESSION_STATUS:
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
                self.zmq_message_handler.send_to_socket(message, Dealer.MODBUSTCP)
                if self.drive_green_manager is not None:
                    self.drive_green_manager.get_message(message, message_type)
            elif message_type == MessageTypes.CHARGE_POINT_AVAILABILITY:
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
            elif message_type == MessageTypes.DELAY_CHARGE \
                    or message_type == MessageTypes.ECO_CHARGE:
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
                if self.drive_green_manager is not None:
                    self.drive_green_manager.get_message(message, message_type)
            elif message_type == MessageTypes.CHARGE_STATION_STATUS:
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
                self.zmq_message_handler.send_to_socket(message, Dealer.OCPP)
                self.zmq_message_handler.send_to_socket(message, Dealer.MODBUSTCP)
                if self.drive_green_manager is not None:
                    self.drive_green_manager.get_message(message, message_type)
            elif message_type == MessageTypes.FIRMWARE_UPDATE_STATUS:
                self.zmq_message_handler.send_to_socket(message, Dealer.OCPP)
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
                if self.drive_green_manager is not None:
                    self.drive_green_manager.get_message(message, message_type)
            elif message_type == MessageTypes.PROPERTY_CHANGE:
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
                if self.drive_green_manager is not None:
                    self.drive_green_manager.get_message(message, message_type)
            elif message_type == MessageTypes.OCPP:
                self.zmq_message_handler.send_to_socket(message, Dealer.OCPP)
            else:
                logger.info("unhandled message type from charge station")

        elif requester == self.internal_meter:
            self.acpw_handler.send_to_acpw(message)
        elif requester == self.acpw_handler:
            self.charge_station.get_message(message, message_type)
            # For now just pass all the messages to the ocpp dealer.
            self.zmq_message_handler.send_to_socket(message, Dealer.OCPP)
            self.zmq_message_handler.send_to_socket(message, Dealer.MODBUSTCP)
            # TODO more
        elif requester == self.rfid_reader:
            self.charge_station.get_rfid_message(message)
        elif requester == self.zmq_message_handler:
            if message_type == MessageTypes.CONFIGURATION_UPDATE:
                self.configuration_manager.get_message(message, message_type)
                self.zmq_message_handler.send_to_socket(message, Dealer.MODBUSTCP)
            elif message_type == MessageTypes.RESERVATION_REQUEST:
                self.zmq_message_handler.send_to_socket(message, Dealer.UI)
            elif message_type == MessageTypes.OCPP:
                self.charge_station.get_message(message, message_type)
            elif message_type == MessageTypes.EXTERNAL_METER:
                self.zmq_message_handler.send_to_socket(message, Dealer.OCPP)
                self.charge_station.get_message(message, message_type)
            else:
                self.charge_station.get_message(message, message_type)

        elif requester == self.configuration_manager:
            self.charge_station.get_configuration(message, message_type)
        elif requester == self.drive_green_manager:
            if message_type == MessageTypes.BLUETOOTH_MESSAGE:
                self.bluetooth_handler.sendMessage(message, message_type)
            elif message_type == MessageTypes.CONFIGURATION_UPDATE:
                self.configuration_manager.get_message(message, message_type)
            else:
                self.charge_station.get_message(message, message_type)
        elif requester == self.bluetooth_handler:
            if message_type == MessageTypes.BLUETOOTH_MESSAGE:
                self.drive_green_manager.get_message(message, message_type)
            elif message_type == MessageTypes.BLUETOOTH_STATUS:
                self.charge_station.get_message(message, message_type)
        else:
            logger.info("Unknown requester {0}".format(requester))


class RfidReader(Requester):

    def __init__(self):
        super().__init__()

    def start(self):
        rfid_read_thread = threading.Thread(target=self._rfidReaderChannel, daemon=True)
        rfid_read_thread.start()

    def _rfidReaderChannel(self):
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect("ipc:///var/lib/rfid.ipc")
        socket.setsockopt(zmq.SUBSCRIBE, b'')

        while True:
            message = socket.recv()
            try:
                message = message.decode("utf-8")
                logger.info("Received rfid: %s" % message)
                self.mediator.send(message, self, MessageTypes.RFID_UID)

                # if rfidUid['type'] == "rfidEvent":
                #     checkAuthenticationMethod(rfidUid['data']['value'])
                # elif rfidUid['type'] == "rfidAlarm":
                #     if rfidUid['data']['value'] == "ConnectionError":
                #         cmd = createAcpwMessage(
                #             Command.HMI_BOARD_ERR.value, bytearray([1]))
                #     elif rfidUid['data']['value'] == "ConnectionRecover":
                #         cmd = createAcpwMessage(
                #             Command.HMI_BOARD_ERR.value, bytearray([0]))
                #     if cmd is not None:
                #         sendToAcpw(cmd)
                #         sendToDealers(message)
                # else:
                #     logger.info("Unidentified rfid message")
            except:
                logger.info("rfid received broken message: {0}".format(traceback.format_exc()))

            time.sleep(0.01)


class Authorization:

    def __init__(self, charge_point=None, authorization_timer=None, current_authorization_uid=None):
        self.charge_point = charge_point
        self.current_authorization_uid = current_authorization_uid
        self.authorization_timer = authorization_timer

    def should_authorize(self):
        # If charge point is already authorized session should authorize,
        # otherwise session should satisfy next statement
        return self.charge_point.is_authorized() or \
               (self.charge_point.status != ChargePointStatus.FAULTED and self.charge_point.availability != ChargePointAvailability.INOPERATIVE)

    def authorize_mobile(self):
        pass

    def autostart_active(self):
        return False

    def authorize(self, uid):
        if self.should_authorize():
            msg = {
                "idTag": uid,
                "type": "Authorize"
            }
            msg = json.dumps(msg)
            logger.info("AuthorizeRequest {0}".format(msg))
            self.charge_point.charge_station.mediator.send(msg, self.charge_point.charge_station, MessageTypes.AUTHORIZE)

    # def cancelAuthorization(self):
    #     pass

    def receive_authorization_response(self, response, id_tag):
        pass

    def has_current_authorization_uid(self):
        return self.current_authorization_uid is not None

    # def authorizationTimeController(self):
    #     pass
    #
    # def resetAuthorizationTimer(self):
    #     pass

    def authorization_timeout(self):
        if self.charge_point.current_charge_session is None and \
                self.charge_point.control_pilot_state == ControlPilotStates.A1:
            self.charge_point.authorization_response = AuthorizationResponse.TIMEOUT
            self.charge_point.authorization_status = AuthorizationStatus.TIMEOUT
            self.cancel_authorization()

    def cancel_authorization(self):
        if self.charge_point.control_pilot_state == ControlPilotStates.A1:
            stop_blink_auth = PeripheralCommand(
                self.charge_point.charge_station, PeripheralRequest.STOP_AUTH_WAIT_PLUG)
            stop_blink_auth.execute()
        logger.info("authorization timeout, cancel authorization")
        self.authorization_timer = None
        self.charge_point.authorization_status = None
        self.charge_point.authorization_response = None
        self.current_authorization_uid = None
        self.charge_point.stop_charging()

    def reset_authorization_timer(self):
        if self.authorization_timer is not None:
            self.authorization_timer.cancel()
            self.authorization_timer = None


class DriveGreenAuthorization(Authorization):

    def __init__(self, uidList, charge_point=None):
        self._uid_set = uidList
        super().__init__(charge_point)

    def autostart_active(self):
        if len(self._uid_set) == 0 \
                and self.charge_point.charge_station.is_configured():
            return True
        return False

    def authorize_mobile(self):
        if not self.should_authorize():
            return

        if self.charge_point.authorization_status == AuthorizationStatus.START:

            if self.charge_point.current_charge_session is None or self.charge_point.stop_requested:
                if (self.charge_point.charge_station.eco_charge_status == Status.ENABLED and self.charge_point.eco_charge_completed is False) or \
                        self.charge_point.charge_station.delay_charge_status == Status.ENABLED:
                    self.charge_point.immediate_charge = True
                    self.charge_point.start_charging()
                else:
                    self.charge_point.authorization_response = AuthorizationResponse.ACCEPTED
                    self.charge_point.stop_charging()
                    self.charge_point.eco_charge_completed = False
            else:
                self.charge_point.authorization_response = AuthorizationResponse.ACCEPTED
                self.charge_point.stop_charging()
                self.charge_point.eco_charge_completed = False

        else:
            if self.charge_point.status == ChargePointStatus.FINISHING and self.charge_point.current_charge_session is not None:
                self.charge_point.finish_session()
            self.charge_point.grant_authorization()
            self.authorization_timer = threading. \
                Timer(AUTHORIZATION_TIMEOUT, self.authorization_timeout)
            self.authorization_timer.start()
            if self.charge_point.charge_station.eco_charge_status != Status.ENABLED:
                self.charge_point.start_charging()
            else:
                self.charge_point.interlock_control(True)

    def authorize(self, uid):
        super().authorize(uid)

        if not self.should_authorize():
            return

        if self.charge_point.authorization_status == AuthorizationStatus.START:

            if self.charge_point.current_charge_session is None or self.charge_point.stop_requested:
                if self.contains_uid_inset(uid):
                    if uid == self.current_authorization_uid.lower() or \
                            self.current_authorization_uid == "mobileApplication":
                        if (self.charge_point.charge_station.eco_charge_status == Status.ENABLED and self.charge_point.eco_charge_completed is False) or \
                                self.charge_point.charge_station.delay_charge_status == Status.ENABLED:
                            self.charge_point.immediate_charge = True
                            self.charge_point.authorization_start_indicators()
                            self.charge_point.authorization_stop_indicators()
                            self.charge_point.start_charging()
                        else:
                            self.charge_point.authorization_finish_indicators()
                            self.charge_point.authorization_response = AuthorizationResponse.ACCEPTED
                            self.charge_point.stop_charging()
                            self.charge_point.eco_charge_completed = False
                    else:
                        self.charge_point.authorization_response = AuthorizationResponse.INVALID
                        self.charge_point.authorization_fail_indicators()
                else:
                    self.charge_point.authorization_response = AuthorizationResponse.INVALID
                    self.charge_point.authorization_fail_indicators()
            else:
                if uid == self.current_authorization_uid.lower() or \
                        (self.current_authorization_uid == "mobileApplication"
                         and self.contains_uid_inset(uid)):
                    self.charge_point.authorization_finish_indicators()
                    self.charge_point.authorization_response = AuthorizationResponse.ACCEPTED
                    self.charge_point.stop_charging()
                    self.charge_point.eco_charge_completed = False
                else:
                    self.charge_point.authorization_response = AuthorizationResponse.INVALID
                    self.charge_point.authorization_fail_indicators()
        else:
            if self.contains_uid_inset(uid):
                if self.charge_point.status == ChargePointStatus.FINISHING and self.charge_point.current_charge_session is not None:
                    self.charge_point.finish_session()
                self.charge_point.authorization_start_indicators()
                self.charge_point.authorization_stop_indicators()
                self.charge_point.grant_authorization(uid)
                self.authorization_timer = threading. \
                    Timer(AUTHORIZATION_TIMEOUT, self.authorization_timeout)
                self.authorization_timer.start()
                if self.charge_point.charge_station.eco_charge_status != Status.ENABLED:
                    self.charge_point.start_charging()
                else:
                    self.charge_point.interlock_control(True)

            else:
                self.charge_point.authorization_response = AuthorizationResponse.INVALID
                self.current_authorization_uid = None
                self.charge_point.authorization_fail_indicators()

    def contains_uid_inset(self, uid):
        return uid in (setId.lower() for setId in self._uid_set)

    def add_to_set(self, uid):
        
        self._uid_set.add(uid)
        self._update_local_list()
        self.charge_point.card_added_indicators()

    def remove_from_set(self, uid):
        for item in self._uid_set:
            if uid == item.lower():
                self._uid_set.remove(item)
                break
        self._update_local_list()
        self.charge_point.card_removed_indicators()

    def _update_local_list(self):
        try:
            conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            local_list = None
            if len(self._uid_set):
                local_list = ','.join(self._uid_set)
            query = "UPDATE authorizationMode SET localList=? WHERE ID=?;"
            cursor.execute(query, (local_list, 1))
            conn.commit()
            conn.close()
        except:
            logger.error("local list update failure {}".format(traceback.format_exc()))

    def set_is_empty(self):
        return len(self._uid_set) == 0


class NoAuthorization(Authorization):

    def __init__(self, charge_point):
        super().__init__(charge_point)
        operation_mode = SwitchOperationModeCommand(self.charge_point.charge_station, True)
        operation_mode.execute()

    def authorize(self, uid):
        pass  # Simply do nothing


class LocalAuthorization(Authorization):

    def __init__(self, uidList, charge_point=None, current_authorization_uid=None):
        self.__uidList = uidList
        self.current_authorization_uid = current_authorization_uid
        super().__init__(charge_point)
        operation_mode = SwitchOperationModeCommand(self.charge_point.charge_station, False)
        operation_mode.execute()

    def authorize(self, uid):
        super().authorize(uid)

        if not self.should_authorize():
            return

        if self.charge_point.authorization_status == AuthorizationStatus.START:

            if self.charge_point.current_charge_session is None:
                if uid == self.current_authorization_uid.lower():
                    self.charge_point.authorization_finish_indicators()
                    self.charge_point.authorization_response = AuthorizationResponse.ACCEPTED
                    self.charge_point.stop_charging()
                else:
                    self.charge_point.authorization_response = AuthorizationResponse.INVALID
                    self.charge_point.authorization_fail_indicators()
            else:
                if uid == self.charge_point.current_charge_session.authorization_uid.lower():
                    self.charge_point.authorization_finish_indicators()
                    self.charge_point.authorization_response = AuthorizationResponse.ACCEPTED
                    self.charge_point.stop_charging()
                else:
                    self.charge_point.authorization_response = AuthorizationResponse.INVALID
                    self.charge_point.authorization_fail_indicators()
        else:
            if self.contains_uid_inset(uid):
                if self.charge_point.status == ChargePointStatus.FINISHING and self.charge_point.current_charge_session is not None:
                    self.charge_point.finish_session()
                self.charge_point.authorization_start_indicators()
                self.charge_point.authorization_stop_indicators()
                self.charge_point.authorization_response = AuthorizationResponse.ACCEPTED
                self.charge_point.grant_authorization(uid)
                self.authorization_timer = threading. \
                    Timer(AUTHORIZATION_TIMEOUT, self.authorization_timeout)
                self.authorization_timer.start()
                self.charge_point.start_charging()

            else:
                self.charge_point.authorization_response = AuthorizationResponse.INVALID
                self.current_authorization_uid = None
                self.charge_point.authorization_fail_indicators()

    def contains_uid_inset(self, uid):
        return uid in (setId.lower() for setId in self.__uidList)


class OcppAuthorization(Authorization):

    def authorize(self, uid):
        super().authorize(uid)

        if not self.should_authorize():
            return

    def __init__(self, charge_point=None, current_authorization_uid=None):
        self.current_authorization_uid = current_authorization_uid
        super().__init__(charge_point)
        operation_mode = SwitchOperationModeCommand(self.charge_point.charge_station, False)
        operation_mode.execute()

    def receive_authorization_response(self, response, id_tag):
        self.charge_point.authorization_stop_indicators()

        self.charge_point.authorization_response = response
        if self.charge_point.authorization_status == AuthorizationStatus.START:

            if self.charge_point.current_charge_session is None:
                if id_tag == self.current_authorization_uid \
                        and self.charge_point.authorization_response == AuthorizationResponse.ACCEPTED:
                    self.charge_point.authorization_finish_indicators()
                    self.charge_point.stop_charging()
                elif id_tag == self.current_authorization_uid and self.charge_point.authorization_response == AuthorizationResponse.TIMEOUT:
                    self.charge_point.authorization_status = AuthorizationStatus.TIMEOUT
                    self.cancel_authorization()
                else:
                    self.charge_point.authorization_fail_indicators()

            else:
                if id_tag == self.charge_point.current_charge_session.authorization_uid:
                    self.charge_point.authorization_finish_indicators()
                    self.charge_point.stop_charging()
                else:
                    self.charge_point.authorization_fail_indicators()

        else:
            if self.charge_point.authorization_response == AuthorizationResponse.ACCEPTED:
                if self.charge_point.status == ChargePointStatus.FINISHING and self.charge_point.current_charge_session is not None:
                    self.charge_point.finish_session()
                if self.charge_point.reservation.reservation_status == Status.ENABLED:
                    self.charge_point.cancel_reservation(self.charge_point.reservation.reservation_id)
                self.charge_point.authorization_start_indicators()
                self.charge_point.authorization_stop_indicators()
                self.charge_point.grant_authorization(id_tag)
                self.charge_point.start_charging()
            elif self.charge_point.authorization_response == AuthorizationResponse.TIMEOUT:
                self.charge_point.authorization_status = AuthorizationStatus.TIMEOUT
                self.cancel_authorization()
            else:
                self.charge_point.authorization_response = AuthorizationResponse.INVALID
                self.charge_point.authorization_fail_indicators()


class AcceptAllAuthorization(Authorization):

    def __init__(self, charge_point=None, current_authorization_uid=None):
        self.current_authorization_uid = current_authorization_uid
        super().__init__(charge_point)
        operation_mode = SwitchOperationModeCommand(self.charge_point.charge_station, False)
        operation_mode.execute()

    def authorize(self, uid):
        super().authorize(uid)

        if not self.should_authorize():
            return

        logger.debug("Accept all authorize")
        if self.charge_point.authorization_status == AuthorizationStatus.START:

            if self.charge_point.current_charge_session is None:
                if uid == self.current_authorization_uid:
                    self.charge_point.authorization_finish_indicators()
                    self.charge_point.authorization_response = AuthorizationResponse.ACCEPTED
                    self.charge_point.stop_charging()
                else:
                    self.charge_point.authorization_response = AuthorizationResponse.INVALID
                    self.charge_point.authorization_fail_indicators()
            else:
                if uid == self.charge_point.current_charge_session.authorization_uid:
                    self.charge_point.authorization_finish_indicators()
                    self.charge_point.authorization_response = AuthorizationResponse.ACCEPTED
                    self.charge_point.stop_charging()
                else:
                    self.charge_point.authorization_response = AuthorizationResponse.INVALID
                    self.charge_point.authorization_fail_indicators()
        else:
            if self.charge_point.status == ChargePointStatus.FINISHING and self.charge_point.current_charge_session is not None:
                self.charge_point.finish_session()
            self.charge_point.authorization_start_indicators()
            self.charge_point.authorization_stop_indicators()
            self.charge_point.authorization_response = AuthorizationResponse.ACCEPTED
            self.charge_point.grant_authorization(uid)
            self.authorization_timer = threading. \
                Timer(AUTHORIZATION_TIMEOUT, self.authorization_timeout)
            self.authorization_timer.start()
            self.charge_point.start_charging()


class ChargeSession:

    # TODO report all session changes
    def __init__(self, session_uuid, authorization_uid=None,
                 charge_point=None, start_time=None, stop_time=None, status=None, start_energy=0, stop_energy=0):
        self.session_uuid = session_uuid
        self.authorization_uid = authorization_uid
        self.start_time = start_time or 0
        self.stop_time = stop_time or 0
        self._status = status
        self.charge_point = charge_point
        self._initial_energy = start_energy
        self._last_energy = stop_energy

    @property
    def initial_energy(self):
        return self._initial_energy

    @initial_energy.setter
    def initial_energy(self, value):
        self._initial_energy = value

    @property
    def last_energy(self):
        return self._last_energy

    @last_energy.setter
    def last_energy(self, value):
        self._last_energy = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        self.report_status()

    def report_status(self):
        msg = {
            "type": "ChargeSessionStatus",
            "status": self.status.value,
            "startTime": int(self.start_time),
            "initialEnergy": self.initial_energy,
            "lastEnergy": self.last_energy
        }
        if self.status == ChargeSessionStatus.STOPPED:
            msg["finishTime"] = int(self.stop_time)  # .strftime("%Y-%m-%d %H:%M:%S")
        msg = json.dumps(msg)
        logger.info("ChargeSessionStatus: {0}".format(msg))
        self.charge_point.charge_station.mediator.send(msg, self.charge_point.charge_station,
                                                       MessageTypes.CHARGE_SESSION_STATUS)

    def start_database_update(self):
        databaseUpdateThread = threading.Thread(target=self._update_database, daemon=True)
        databaseUpdateThread.start()

    def insert_database(self):
        try:
            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            sessionQuery = "INSERT INTO activeChargeSession (sessionUuid, " \
                           "authorizationUid, startTime, stopTime, status, chargePointId, initialEnergy, lastEnergy) " \
                           "VALUES('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', {6}, {7});" \
                .format(self.session_uuid, self.authorization_uid, int(self.start_time),
                        int(self.stop_time), self.status.value, self.charge_point.id,
                        self.initial_energy, self.last_energy)

            cursor.execute(sessionQuery)
            conn.commit()
            conn.close()
        except:
            logger.info("ChargeSession db update issue: {0}".format(traceback.format_exc()))

    def _update_database(self):
        while self.status != ChargeSessionStatus.STOPPED:
            try:
                conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                cursor = conn.cursor()

                sessionQuery = "UPDATE activeChargeSession SET authorizationUid='{0}', " \
                               "startTime='{1}', stopTime='{2}', status='{3}', initialEnergy={5}, " \
                               "lastEnergy={6} WHERE sessionUuid='{4}';". \
                    format(self.authorization_uid, int(self.start_time),
                           int(self.stop_time), self.status.value, self.session_uuid,
                           self.initial_energy, self.last_energy)
                cursor.execute(sessionQuery)
                conn.commit()
                conn.close()
            except:
                logger.info("ChargeSession db update issue: {0}".format(traceback.format_exc()))
            time.sleep(1)

    def stop_and_remove_from_database(self):
        try:
            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
            cursor = conn.cursor()

            sessionQuery = "UPDATE activeChargeSession SET authorizationUid='{0}', " \
                           "startTime='{1}', stopTime='{2}', status='{3}' WHERE " \
                           "sessionUuid='{4}';". \
                format(self.authorization_uid, int(self.start_time),
                       int(self.stop_time), self.status.value, self.session_uuid)
            cursor.execute(sessionQuery)
            conn.commit()

            sessionQuery = "DELETE FROM activeChargeSession WHERE sessionUuid='{0}';" \
                .format(self.session_uuid)
            cursor.execute(sessionQuery)
            conn.commit()
            conn.close()
        except:
            logger.info("ChargeSession db update issue: {0}".format(traceback.format_exc()))

    def start(self):
        self.start_time = time.time()
        self.status = ChargeSessionStatus.STARTED
        self.insert_database()
        self.start_database_update()
        self.charge_point.stop_requested = False

    def stop(self):
        self.stop_time = time.time()
        self.status = ChargeSessionStatus.STOPPED
        self.stop_and_remove_from_database()

    def pause(self):
        self.status = ChargeSessionStatus.SUSPENDED

    def resume(self):
        self.status = ChargeSessionStatus.STARTED


class Metric:
    def __init__(self, P1, P2, P3):
        self.P1 = P1
        self.P2 = P2
        self.P3 = P3

    def get_total(self):
        return self.P1 + self.P2 + self.P3


class Voltage(Metric):
    def __init__(self, P1, P2, P3):
        super().__init__(P1, P2, P3)


class Current(Metric):
    def __init__(self, P1, P2, P3):
        super().__init__(P1, P2, P3)


class Power(Metric):
    def __init__(self, P1, P2, P3):
        super().__init__(P1, P2, P3)


class Energy(Metric):
    def __init__(self, P1, P2, P3):
        super().__init__(P1, P2, P3)


class Reservation:
    def __init__(self, reservation_status, expiry_date="", id_tag="", reservation_id=""):
        self.reservation_status = reservation_status
        self.expiry_date = expiry_date
        self.id_tag = id_tag
        self.reservation_id = reservation_id
        
        
class ChargePoint:

    def __init__(self, cp_id, charge_station=None, authorization_mode=None, voltage_p1=0, voltage_p2=0, voltage_p3=0,
                 current_p1=0, current_p2=0, current_p3=0, active_power_p1=0, active_power_p2=0, active_power_p3=0, active_energy_p1=0,
                 active_energy_p2=0, active_energy_p3=0, control_pilot_state=ControlPilotStates.A1,
                 proximity_state=ProximityPilotStates.NoCable, charge_session=None, status=ChargePointStatus.AVAILABLE,
                 error_code=None, vendor_error_code=0, availability=None, min_current=0, max_current=0,
                 available_current=0, lockable_cable=0, reservation_status=Status.DISABLED,
                 expiry_date="", id_tag="", reservation_id="", external_charge=1, current_offered_value=0, authorization_status=AuthorizationStatus.FINISH,
                 authorization_uid=None, current_offered_reason=CurrentOfferedToEvReason.NORMAL, proximity_pilot_current=0,
                 failsafe_current=0, failsafe_timeout=0, modbustcp_current=0):

        self.charge_station = charge_station
        self.id = cp_id
        self._authorizationMode = authorization_mode
        self.reservation_thread = None
        if self._authorizationMode is not None:
            self._authorizationMode.chargePoint = self
        self._voltage = Voltage(voltage_p1, voltage_p2, voltage_p3)
        self._current = Current(current_p1, current_p2, current_p3)
        self._active_power = Power(active_power_p1, active_power_p2, active_power_p3)
        self._active_energy = Energy(active_energy_p1, active_energy_p2, active_energy_p3)

        self._control_pilot_state = control_pilot_state
        self._proximity_pilot_state = proximity_state
        self.current_charge_session = charge_session
        self.charge_sessions = {}
        self._authorization_status = authorization_status
        self.authorization_uid = authorization_uid
        self._authorization_response = None
        self._status = status or ChargePointStatus.UNAVAILABLE
        self._transient_status = None
        self._error_code = error_code or ChargePointErrorCode.NO_ERROR
        self._vendor_error_code = vendor_error_code
        self.initialized = False
        self._availability = availability or ChargePointAvailability.OPERATIVE
        self._immediate_charge = False
        self._stop_requested = False
        self.minimum_current = min_current
        self.maximum_current = max_current
        self._proximity_pilot_current = proximity_pilot_current
        self._failsafe_current = failsafe_current
        self._failsafe_timeout = failsafe_timeout
        self._modbustcp_current = modbustcp_current
        self._available_current = available_current
        self._lockable_cable = lockable_cable
        self._reservation = Reservation(reservation_status, expiry_date, id_tag, reservation_id)
        self._external_charge = external_charge
        
        self._cable_connected = False
        self._current_offered_value = current_offered_value
        self._current_offered_reason = current_offered_reason
        self.eco_charge_completed = False
        
        # self.reportInitialStatus()
        # self.__voltage = voltage or Voltage(0, 0, 0)
        # self.__current = current or Current(0, 0, 0)
        # self.__activePower = activePower or Power(0, 0, 0)
        # self.__activeEnergy = activeEnergy or Energy(0, 0, 0)
        self.charge_station.add_charge_point(self)

    def initialize(self):
        
        conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "SELECT * FROM chargePoints;"
        cursor.execute(query)
        
        rows = cursor.fetchall()
        if len(rows) > 0:
            for row in rows:
                charge_point_id, control_pilot_state, proximity_state, status, \
                    error_code, vendor_error_code, voltage_p1, \
                    voltage_p2, voltage_p3, currentP1, currentP2, currentP3, \
                    active_power_p1, active_power_p2, active_power_p3, active_energy_p1, \
                    active_energy_p2, active_energy_p3, last_update, availability, \
                    min_current, max_current, available_current, lockable_cable, \
                    reservation_status, expiry_date, id_tag, reservation_id, external_charge, \
                    current_offered_value, current_offered_reason, proximity_pilot_current, \
                    failsafe_current, failsafe_timeout, modbustcp_current = row

                self.id = charge_point_id
                self._control_pilot_state = ControlPilotStates(control_pilot_state)
                self._proximity_pilot_state = ProximityPilotStates(proximity_state)
                self._status = ChargePointStatus(status)
                self.transient_status = self._status
                self._error_code = ChargePointErrorCode(error_code)
                self._vendor_error_code = vendor_error_code
                self._voltage.P1 = voltage_p1
                self._voltage.P2 = voltage_p2
                self._voltage.P3 = voltage_p3
                self._active_power.P1 = active_power_p1
                self._active_power.P2 = active_power_p2
                self._active_power.P3 = active_power_p3
                self._active_energy.P1 = active_energy_p1
                self._active_energy.P2 = active_energy_p2
                self._active_energy.P3 = active_energy_p3
                self._availability = ChargePointAvailability(availability)
                self.minimum_current = min_current
                self.maximum_current = max_current
                self._available_current = available_current
                self._lockable_cable = lockable_cable
                self._reservation = Reservation(Status(reservation_status), expiry_date, id_tag, reservation_id)
                self._external_charge = external_charge
                self._current_offered_value = current_offered_value
                self._current_offered_reason = CurrentOfferedToEvReason(current_offered_reason)
                self._proximity_pilot_current = proximity_pilot_current
                self._failsafe_current = failsafe_current
                self._failsafe_timeout = failsafe_timeout
                self._modbustcp_current = modbustcp_current

        else:
            cursor = conn.cursor()
            query = "INSERT INTO chargePoints (chargePointId, controlPilotState, " \
                    "proximityPilotState, status, errorCode, vendorErrorCode, " \
                    "voltageP1, voltageP2, voltageP3, " \
                    "currentP1, currentP2, currentP3, " \
                    "activePowerP1, activePowerP2, activePowerP3, " \
                    "activeEnergyP1, activeEnergyP2, activeEnergyP3, lastUpdate, availability, " \
                    "minCurrent, maxCurrent, availableCurrent, lockableCable," \
                    "reservationStatus, expiryDate, idTag, reservationId, externalCharge, currentOfferedValue, " \
                    "currentOfferedReason, proximityPilotCurrent, failsafeCurrent, failsafeTimeout, modbusTcpCurrent) " \
                    "SELECT {cid}, {control_pilot_state}, {proximity_pilot_state}, " \
                    "'{status}', '{error_code}', {vendor_error_code}, {voltage_p1}, " \
                    "{voltage_p2}, {voltage_p3}, {current_p1}, {current_p2}, {current_p3}, " \
                    "{active_power_p1}, {active_power_p2}, {active_power_p3}, {active_energy_p1}, " \
                    "{active_energy_p2}, {active_energy_p3}, {time}, '{availability}', " \
                    "{minimum_current}, {maximum_current}, {available_current}, {lockable_cable}, " \
                    "'{reservation_status}', '{reservation_expiry}', '{reservation_id_tag}', " \
                    "'{reservation_id}', {external_charge}, {current_offered_value}, {current_offered_reason}, {proximity_pilot_current}, " \
                    "{failsafe_current}, {failsafe_timeout}, {modbustcp_current}" \
                    " WHERE NOT EXISTS (SELECT 1 FROM chargePoints WHERE chargePointId={cid});".format(
                        cid=self.id, control_pilot_state=self.control_pilot_state.value, proximity_pilot_state=self.proximity_pilot_state.value, status=self.status.value, error_code=self.error_code.value,
                        vendor_error_code=self._vendor_error_code, voltage_p1=self.voltage.P1, voltage_p2=self.voltage.P2, voltage_p3=self.voltage.P3, current_p1=self.current.P1, current_p2=self.current.P2, current_p3=self.current.P3,
                        active_power_p1=self.active_power.P1, active_power_p2=self.active_power.P2, active_power_p3=self.active_power.P3, active_energy_p1=self.active_energy.P1, active_energy_p2=self.active_energy.P2, active_energy_p3=self.active_energy.P3,
                        time=time.time(), availability=self.availability.value, minimum_current=self.minimum_current, maximum_current=self.maximum_current, available_current=self.available_current, lockable_cable=self.lockable_cable,
                        reservation_status=self.reservation.reservation_status.value, reservation_expiry=self.reservation.expiry_date, reservation_id_tag=self.reservation.id_tag, reservation_id=self.reservation.reservation_id,
                        external_charge=self.external_charge, current_offered_value=self.current_offered_value, current_offered_reason=self.current_offered_reason.value, proximity_pilot_current=self.proximity_pilot_current,
                        failsafe_current=self.failsafe_current, failsafe_timeout=self.failsafe_timeout, modbustcp_current=self.modbustcp_current
                    )
            cursor.execute(query)
            conn.commit()
            
        conn.close()
        
        self.load_last_authorization_and_charge_session()
        self.query_charge_point_status_from_acpw()
        
        databaseUpdateThread = threading.Thread(target=self.update_charge_points_database, daemon=True)
        databaseUpdateThread.start()

    def load_last_authorization_and_charge_session(self):
        try:
            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT sessionUuid, authorizationUid, startTime, " \
                    "stopTime, status, chargePointId, initialEnergy, lastEnergy FROM activeChargeSession WHERE chargePointId={0};". \
                format(self.id)
            cursor.execute(query)
            row = cursor.fetchone()
            if row is not None:
                sessionUuid, authorizationUid, startTime, stopTime, status, id, initialEnergy, lastEnergy = row
                chargeSession = ChargeSession(
                    sessionUuid, authorizationUid, self, startTime, stopTime, ChargeSessionStatus(status), initialEnergy, lastEnergy
                )
                self.current_charge_session = chargeSession

            conn.close()
        except:
            logger.info("ChargeSession db retrieve issue: {0}".format(traceback.format_exc()))

    def report_initial_status(self):
        if self.initialized is False:
            msg = self._create_status_notification_message()
            logger.info("initial status notification : {0}".format(msg))
            self.charge_station.mediator.send(msg, self.charge_station, MessageTypes.STATUS_NOTIFICATION)

    def retrieve_last_charge_session(self):
        try:
            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT sessionUuid, authorizationUid, startTime, " \
                    "stopTime, status, chargePointId, initialEnergy, lastEnergy FROM activeChargeSession WHERE chargePointId={0};". \
                format(self.id)
            cursor.execute(query)
            row = cursor.fetchone()
            if row is not None:
                sessionUuid, authorizationUid, startTime, stopTime, status, id, initialEnergy, lastEnergy = row
                chargeSession = ChargeSession(
                    sessionUuid, authorizationUid, self, startTime, stopTime, ChargeSessionStatus(status), initialEnergy, lastEnergy
                )
                sessionStillActive = False
                if chargeSession.status == ChargeSessionStatus.STARTED:
                    if self.control_pilot_state == ControlPilotStates.C2:
                        sessionStillActive = True
                elif chargeSession.status == ChargeSessionStatus.PAUSED:
                    if self.control_pilot_state == ControlPilotStates.B2 or \
                            self.control_pilot_state == ControlPilotStates.C1:
                        sessionStillActive = True

                if sessionStillActive is False:
                    self.initialized = True  # Set initialized flag here to send session message
                    chargeSession.stop()
                    self.authorization_status = AuthorizationStatus.FINISH
                else:
                    self.current_charge_session = chargeSession
            conn.close()
        except:
            logger.info("ChargeSession db retrieve issue: {0}".format(traceback.format_exc()))

        self.initialized = True
        msg = self._create_status_notification_message()
        if self.current_charge_session is not None:
            self.current_charge_session.report_status()
        
        self.check_reservation()

        logger.info("charge point initialized : {0}".format(msg))
        self.charge_station.mediator.send(msg, self.charge_station, MessageTypes.STATUS_NOTIFICATION)

    def update_charge_points_database(self):
        while True:
            try:
                conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                cursor = conn.cursor()
                query = "UPDATE chargePoints SET controlPilotState={control_pilot_state}, " \
                        "proximityPilotState={proximity_pilot_state}, status='{status}', " \
                        "errorCode='{error_code}', vendorErrorCode='{vendor_error_code}', " \
                        "voltageP1={voltage_p1}, voltageP2={voltage_p2}, voltageP3={voltage_p3}, " \
                        "currentP1={current_p1}, currentP2={current_p2}, currentP3={current_p3}, " \
                        "activePowerP1={active_power_p1}, activePowerP2={active_power_p2}, activePowerP3={active_power_p3}, " \
                        "activeEnergyP1={active_energy_p1}, activeEnergyP2={active_energy_p2}, activeEnergyP3={active_energy_p3}, " \
                        "availability='{availability}', minCurrent={minimum_current}, maxCurrent={maximum_current}, " \
                        "availableCurrent={available_current}, lockableCable={lockable_cable}, " \
                        "reservationStatus='{reservation_status}', expiryDate='{expiry_date}', " \
                        "idTag='{id_tag}', reservationId='{reservation_id}', currentOfferedValue={current_offered_value}, " \
                        "currentOfferedReason={current_offered_reason}, proximityPilotCurrent={proximity_pilot_current}, " \
                        "failsafeCurrent={failsafe_current}, failsafeTimeout={failsafe_timeout}, modbusTcpCurrent={modbustcp_current} " \
                        "WHERE chargePointId={cid};".format(
                            control_pilot_state=self.control_pilot_state.value, proximity_pilot_state=self.proximity_pilot_state.value,
                            status=self.status.value, error_code=self.error_code.value, vendor_error_code=self._vendor_error_code, voltage_p1=self.voltage.P1,
                            voltage_p2=self.voltage.P2, voltage_p3=self.voltage.P3, current_p1=self.current.P1, current_p2=self.current.P2, current_p3=self.current.P3,
                            active_power_p1=self.active_power.P1, active_power_p2=self.active_power.P2, active_power_p3=self.active_power.P3, 
                            active_energy_p1=self.active_energy.P1, active_energy_p2=self.active_energy.P2, active_energy_p3=self.active_energy.P3, availability=self.availability.value,
                            minimum_current=self.minimum_current, maximum_current=self.maximum_current, available_current=self.available_current,lockable_cable=self.lockable_cable,
                            reservation_status=self.reservation.reservation_status.value, expiry_date=self.reservation.expiry_date, id_tag=self.reservation.id_tag,
                            reservation_id=self.reservation.reservation_id, current_offered_reason=self.current_offered_reason.value, current_offered_value=self.current_offered_value,
                            proximity_pilot_current=self.proximity_pilot_current, failsafe_current=self.failsafe_current, failsafe_timeout=self.failsafe_timeout,
                            modbustcp_current=self.modbustcp_current, cid=self.id
                        )
                cursor.execute(query)

                # for chargeSession in self.chargeSessions:
                if self.current_charge_session is not None:
                    sessionQuery = "UPDATE activeChargeSession SET authorizationUid='{0}', " \
                                   "startTime='{1}', stopTime='{2}', status='{3}' WHERE " \
                                   "sessionUuid='{4}';"
                    cursor.execute(sessionQuery)

                conn.commit()
                conn.close()
            except:
                logger.info("ChargePoint db update issue: {0}".format(traceback.format_exc()))
            time.sleep(0.5)

    def grant_authorization(self, uid="mobileApplication"):
        self.authorization_response = AuthorizationResponse.ACCEPTED
        if self.control_pilot_state == ControlPilotStates.A1:
            start_blink_auth = PeripheralCommand(
                self.charge_station, PeripheralRequest.START_AUTH_WAIT_PLUG)
            start_blink_auth.execute()
        self.authorization_status = AuthorizationStatus.START
        self.authorization_mode.current_authorization_uid = uid

    def clear_authorization_uid(self):
        self.authorization_mode.current_authorization_uid = None
        self.authorization_uid = None
        
    def clear_authorization(self):
        self.clear_authorization_uid()
        self.authorization_status = AuthorizationStatus.FINISH
        self.authorization_finish_indicators()

    def authorize(self, cardUid=None):
        if self.authorization_mode is not None:
            if cardUid is not None:
                self.authorization_mode.authorize(cardUid)
            else:
                self.authorization_mode.authorize_mobile()
        else:
            logger.info("Error: authorization mode is not set")

    def is_authorized(self):
        return self.authorization_mode.has_current_authorization_uid() and self.authorization_status == AuthorizationStatus.START

    def _report_property_update(self, prop, prop_type):
        data = {
            "type": prop_type,
            "data": {
                "value": prop
            }
        }
        msg = json.dumps(data)
        logger.info(msg)
        self.charge_station.mediator.send(msg, self.charge_station, MessageTypes.PROPERTY_CHANGE)

    @property
    def transient_status(self):
        return self._transient_status

    @transient_status.setter
    def transient_status(self, value):
        self._transient_status = value
        self.status = self.transient_status
        
    @property
    def cable_connected(self):
        return self._cable_connected
    
    @cable_connected.setter
    def cable_connected(self, value):
        if isinstance(self.authorization_mode, OcppAuthorization) and not self._cable_connected and value:
            conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT FreeModeActive, FreeModeRFID FROM ocppConfigurations;"
            cursor.execute(query)
            row = cursor.fetchone()
            free_mode = row[0]
            uid = row[1]
            if str(free_mode).upper() == "TRUE":
                if not self.authorization_status == AuthorizationStatus.START:
                    self.authorize(uid)
        self._cable_connected = value
    
    @property
    def available_current(self):
        return self._available_current

    @available_current.setter
    def available_current(self, value):
        self._available_current = value
        self._report_property_update(self.available_current, "availableCurrent")

    @property
    def reservation(self):
        return self._reservation

    @reservation.setter
    def reservation(self, value):
        self._reservation = value
        if value.reservation_status == Status.DISABLED:
            self.status = self.transient_status
        else:
            self.status = ChargePointStatus.RESERVED
        self.report_status()
        
    @property
    def lockable_cable(self):
        return self._lockable_cable

    @lockable_cable.setter
    def lockable_cable(self, value):
        self._lockable_cable = value
        self._report_property_update(self.lockable_cable, "lockableCable")

    @property
    def stop_requested(self):
        return self._stop_requested

    @stop_requested.setter
    def stop_requested(self, value):
        self._stop_requested = value

    @property
    def immediate_charge(self):
        return self._immediate_charge

    @immediate_charge.setter
    def immediate_charge(self, value):
        self._immediate_charge = value

    @property
    def external_charge(self):
        return self._external_charge

    @external_charge.setter
    def external_charge(self, value):
        self._external_charge = value
        if 1 == value:
            self.status = self.transient_status
        else:
            self.status = ChargePointStatus.UNAVAILABLE
        msg = self._create_status_notification_message()
        logger.info(msg)
        self.send_to_mediator(msg, MessageTypes.STATUS_NOTIFICATION)

    @property
    def availability(self):
        return self._availability

    @availability.setter
    def availability(self, value):
        self._availability = value
        if value == ChargePointAvailability.OPERATIVE:
            self.status = self.transient_status
            isAvailable = 1
        else:
            self.status = ChargePointStatus.UNAVAILABLE
            isAvailable = 0

        msg = self._create_status_notification_message()
        logger.info(msg)
        self.send_to_mediator(msg, MessageTypes.STATUS_NOTIFICATION)

        cmd = ChangeAvailabilityCommand(self.charge_station, isAvailable)
        cmd.execute()

    @property
    def current_offered_value(self):
        return self._current_offered_value

    @current_offered_value.setter
    def current_offered_value(self, value):
        self._current_offered_value = value

    @property
    def current_offered_reason(self):
        return self._current_offered_reason

    @current_offered_reason.setter
    def current_offered_reason(self, value):
        self._current_offered_reason = value
        prop = {
            "current": self._current_offered_value,
            "reason": self._current_offered_reason.value
        }
        self._report_property_update(prop, "currentOfferedEv")

    @property
    def proximity_pilot_current(self):
        return self._proximity_pilot_current

    @proximity_pilot_current.setter
    def proximity_pilot_current(self, value):
        self._proximity_pilot_current = value
        self._report_property_update(self.proximity_pilot_current, "proximityPilotCurrent")

    @property
    def failsafe_current(self):
        return self._failsafe_current

    @failsafe_current.setter
    def failsafe_current(self, value):
        self._failsafe_current = value
        self._report_property_update(self.failsafe_current, "failsafeCurrent")

    @property
    def failsafe_timeout(self):
        return self._failsafe_timeout

    @failsafe_timeout.setter
    def failsafe_timeout(self, value):
        self._failsafe_timeout = value
        self._report_property_update(self.failsafe_timeout, "failsafeTimeout")

    @property
    def modbustcp_current(self):
        return self._modbustcp_current

    @modbustcp_current.setter
    def modbustcp_current(self, value):
        self._modbustcp_current = value
        self._report_property_update(self.modbustcp_current, "modbusTcpCurrent")

    @property
    def authorization_mode(self):
        return self._authorizationMode

    @authorization_mode.setter
    def authorization_mode(self, value):
        self._authorizationMode = value
        if value is not None:
            self._authorizationMode.chargePoint = self

    @property
    def voltage(self):
        return self._voltage

    @voltage.setter
    def voltage(self, value):
        self._voltage = value
        self.report_meter_values()

    @property
    def current(self):
        return self._current

    @current.setter
    def current(self, value):
        self._current = value
        self.report_meter_values()

    @property
    def active_power(self):
        return self._active_power

    @active_power.setter
    def active_power(self, value):
        self._active_power = value
        self.report_meter_values()

    @property
    def active_energy(self):
        return self._active_energy

    @active_energy.setter
    def active_energy(self, value):
        self._active_energy = value
        self.update_current_session_metric()
        self.report_meter_values()

    def report_meter_values(self):
        dateNow = int(time.time())  # datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = {
            "type": "MeterValues",
            "meterValue": [
                {
                    "timestamp": dateNow,
                    "sampledValue": [
                        {
                            "measurand": "Energy.Active.Import.Register",
                            "unit": "Wh",
                            "value": str(self.active_energy.P1 + self.active_energy.P2 + self.active_energy.P3)
                        },
                        {
                            "measurand": "Current.Import",
                            "unit": "mA",
                            "phase": "L1",
                            "value": str(self.current.P1)
                        },
                        {
                            "measurand": "Current.Import",
                            "unit": "mA",
                            "phase": "L2",
                            "value": str(self.current.P2)
                        },
                        {
                            "measurand": "Current.Import",
                            "unit": "mA",
                            "phase": "L3",
                            "value": str(self.current.P3)
                        },
                        {
                            "measurand": "Power.Active.Import",
                            "unit": "W",
                            "phase": "L1",
                            "value": str(self.active_power.P1)
                        },
                        {
                            "measurand": "Power.Active.Import",
                            "unit": "W",
                            "phase": "L2",
                            "value": str(self.active_power.P2)
                        },
                        {
                            "measurand": "Power.Active.Import",
                            "unit": "W",
                            "phase": "L3",
                            "value": str(self.active_power.P3)
                        },
                        {
                            "measurand": "Voltage",
                            "unit": "mV",
                            "phase": "L1",
                            "value": str(self.voltage.P1)
                        },
                        {
                            "measurand": "Voltage",
                            "unit": "mV",
                            "phase": "L2",
                            "value": str(self.voltage.P2)
                        },
                        {
                            "measurand": "Voltage",
                            "unit": "mV",
                            "phase": "L3",
                            "value": str(self.voltage.P3)
                        },
                    ],
                }
            ]
        }

        msg = json.dumps(msg)
        logger.debug("Meter Values: {0}".format(msg))
        self.send_to_mediator(msg, MessageTypes.METER_VALUES)

    @property
    def error_code(self):
        return self._error_code

    @error_code.setter
    def error_code(self, errorCode):
        error = ChargePointError()
        error.asInt = errorCode
        self._vendor_error_code = errorCode

        if errorCode != 0:

            if error.bit.e0 == 1 or error.bit.e1 == 1 or \
                    error.bit.e2 == 1 or error.bit.e19 == 1:
                errorC = ChargePointErrorCode.CONNECTOR_LOCK_FAILURE
            elif error.bit.e17 == 1:
                errorC = ChargePointErrorCode.GROUND_FAILURE
            elif error.bit.e13 == 1 or error.bit.e14 == 1 or error.bit.e15 == 1:
                errorC = ChargePointErrorCode.OVER_CURRENT_FAILURE
            elif error.bit.e10 == 1 or error.bit.e11 == 1 or error.bit.e12 == 1:
                errorC = ChargePointErrorCode.UNDER_VOLTAGE
            elif error.bit.e7 == 1 or error.bit.e8 == 1 or error.bit.e9 == 1:
                errorC = ChargePointErrorCode.OVER_VOLTAGE
            else:
                errorC = ChargePointErrorCode.OTHER_ERROR
                # TODO other ocpp errors/
            self._error_code = errorC
            self.status = ChargePointStatus.FAULTED
        else:
            self._error_code = ChargePointErrorCode.NO_ERROR
            self.status = self.transient_status

        logger.info("Error code {0}".format(self._error_code.value))
        msg = self._create_status_notification_message()
        logger.info(msg)
        self.send_to_mediator(msg, MessageTypes.STATUS_NOTIFICATION)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        updated_status = None
        if self.error_code != ChargePointErrorCode.NO_ERROR:
            updated_status = ChargePointStatus.FAULTED
        else:
            if self.availability == ChargePointAvailability.INOPERATIVE \
                    or self.external_charge == 0:
                updated_status = ChargePointStatus.UNAVAILABLE
            else:
                if self.reservation.reservation_status == Status.ENABLED:
                    updated_status = ChargePointStatus.RESERVED
                else:
                    updated_status = self.transient_status

        # TODO check status transitions if they are valid or not, e.g from Reserved state to other states

        if self.transient_status == ChargePointStatus.AVAILABLE:
            self.cable_connected = False
        elif self.transient_status == ChargePointStatus.PREPARING or self.transient_status == ChargePointStatus.CHARGING or \
                self.transient_status == ChargePointStatus.SUSPENDED_EVSE or self.transient_status == ChargePointStatus.SUSPENDED_EV or \
                self.transient_status == ChargePointStatus.FINISHING:
            self.cable_connected = True

        if updated_status != self.status and updated_status is not None:
            self._status = updated_status
            logger.info("Status notification {0}".format(self._status.value))
            msg = self._create_status_notification_message()
            logger.info(msg)
            self.send_to_mediator(msg, MessageTypes.STATUS_NOTIFICATION)

    def _create_status_notification_message(self):
        msg = {
            "type": "StatusNotification",
            "status": self.status.value,
            "errorCode": self.error_code.value,
            "vendorErrorCode": self._vendor_error_code
        }

        if isinstance(self.authorization_mode, NoAuthorization) or (isinstance(self.authorization_mode, DriveGreenAuthorization) and self.authorization_mode.autostart_active()):
            msg["extendedStatus"] = ChargePointExtendedStatus.AUTO_START.value
        elif isinstance(self.authorization_mode, OcppAuthorization):
                conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
                cursor = conn.cursor()
                query = "SELECT FreeModeActive FROM ocppConfigurations;"
                cursor.execute(query)
                row = cursor.fetchone()
                free_mode = row[0]
                if str(free_mode).upper() == "TRUE":
                    msg["extendedStatus"] = ChargePointExtendedStatus.AUTO_START.value

        msg = json.dumps(msg)
        return msg

    # @property
    # def extended_status(self):
    #     return self._extended_status
    #
    # @extended_status.setter
    # def extended_status(self, extended_status):
    #     self._extended_status = extended_status
    #     logger.info("Extended Status {0}".format(self._extended_status.value))
    #     msg = self._create_status_notification_message()
    #     logger.info(msg)
    #     self.send_to_mediator(msg, MessageTypes.STATUS_NOTIFICATION)

    @property
    def proximity_pilot_state(self):
        return self._proximity_pilot_state

    @proximity_pilot_state.setter
    def proximity_pilot_state(self, value):
        self._proximity_pilot_state = value
        # if value == ProximityPilotStates.Plugged:
        #     if self.controlPilotState == ControlPilotStates.A1:
        #         self.status = ChargePointStatus.PREPARING
        if value == ProximityPilotStates.NoCable:
            if self.control_pilot_state == ControlPilotStates.A1 \
                    or self.control_pilot_state == ControlPilotStates.A2:
                self.transient_status = ChargePointStatus.AVAILABLE

    @property
    def control_pilot_state(self):
        return self._control_pilot_state

    @control_pilot_state.setter
    def control_pilot_state(self, control_pilot_state):
        self._control_pilot_state = control_pilot_state
        logger.info("ControlPilotState: {0}".format(control_pilot_state))
        if control_pilot_state == ControlPilotStates.A1:

            if self.current_charge_session is not None:
                self.finish_session()
                self.authorization_status = AuthorizationStatus.FINISH
                if self.proximity_pilot_state == ProximityPilotStates.CableModel or \
                        self.proximity_pilot_state == ProximityPilotStates.NoCable:
                    self.transient_status = ChargePointStatus.AVAILABLE

            elif self.current_charge_session is None and \
                    self.authorization_status == AuthorizationStatus.START:
                self.authorization_status = AuthorizationStatus.FINISH
                self.transient_status = ChargePointStatus.AVAILABLE
                self.immediate_charge = False
            else:
                # if self.proximityPilotState == ProximityPilotStates.Plugged:
                #     self.status = ChargePointStatus.PREPARING
                # else:
                self.transient_status = ChargePointStatus.AVAILABLE
                self.immediate_charge = False

            self.stop_requested = False  # Clear stop_reqested flag

            # Stop delay charge if unplugged
            if self.charge_station.delay_charge_status == Status.ENABLED:
                self.charge_station.disable_delay_charge()

        elif control_pilot_state == ControlPilotStates.C2:
            if self.current_charge_session is None:
                self.transient_status = ChargePointStatus.CHARGING
                if self.initialized is True:  # only start new session if chargepoint is initialized
                    self.authorization_mode.reset_authorization_timer()
                    logger.info("New charge session")
                    session_uuid = uuid.uuid1()
                    logger.info("session uuid: {0}".format(session_uuid))
                    initial_energy = self.active_energy.get_total()
                    self.current_charge_session = ChargeSession(
                        session_uuid,
                        self.authorization_mode.current_authorization_uid,
                        self,
                        start_energy=initial_energy,
                        stop_energy=initial_energy
                    )
                    self.current_charge_session.start()
                    self.charge_sessions[session_uuid] = \
                        self.current_charge_session
            else:
                self.transient_status = ChargePointStatus.CHARGING
                self.current_charge_session.resume()

        elif control_pilot_state == ControlPilotStates.B1:
            if self.current_charge_session is not None:
                if (self.current_charge_session.status == ChargeSessionStatus.STARTED or
                    self.current_charge_session.status == ChargeSessionStatus.PAUSED or
                    self.current_charge_session.status == ChargeSessionStatus.SUSPENDED) \
                        and self.stop_requested is False:
                    # keep paused state, do not change status
                    pass
                else:
                    if self.authorization_status != AuthorizationStatus.FINISH:
                        self.authorization_status = AuthorizationStatus.FINISH
                    
                    self.finish_session()
            else:
                if self.authorization_mode.autostart_active():
                    if self.stop_requested is False: 
                        self.authorization_response = AuthorizationResponse.ACCEPTED
                        self.authorization_status = AuthorizationStatus.START
                        self.authorization_mode.current_authorization_uid = "autoStart"
                        self.authorization_uid = 'autoStart'
                        self.transient_status = ChargePointStatus.PREPARING
                        if self.charge_station.eco_charge_status == Status.DISABLED:
                            self.start_charging()
                    else:
                        self.transient_status = ChargePointStatus.PREPARING
                        self.clear_authorization_uid()
                else:
                    self.transient_status = ChargePointStatus.PREPARING
                
                if self.charge_station.eco_charge_status == Status.ENABLED and \
                        self.authorization_status == AuthorizationStatus.START:
                    self.interlock_control(True)

                if self.charge_station.status == ChargeStationStatus.ONBOARDING:
                    self.charge_station.enable_auto_start()

        elif control_pilot_state == ControlPilotStates.C1:

            if self.current_charge_session is not None:
                if self.authorization_status == AuthorizationStatus.FINISH or \
                        self.stop_requested is True:
                    self.current_charge_session.last_energy = \
                        self.active_energy.get_total()
                    self.transient_status = ChargePointStatus.FINISHING
                    self.immediate_charge = False
                else:
                    self.current_charge_session.pause()
                    self.transient_status = ChargePointStatus.SUSPENDED_EVSE
            else:
                if self.authorization_mode.autostart_active():
                    if self.authorization_mode.current_authorization_uid != "mobileApplication":  # to handle autostart delaycharge
                        self.authorization_response = AuthorizationResponse.ACCEPTED
                        self.authorization_status = AuthorizationStatus.START
                        self.authorization_mode.current_authorization_uid = "autoStart"
                        self.authorization_uid = 'autoStart'
                        self.transient_status = ChargePointStatus.PREPARING
                        if self.charge_station.eco_charge_status == Status.DISABLED:
                            self.start_charging()
                    else:
                        self.transient_status = ChargePointStatus.PREPARING
                        self.clear_authorization_uid()
                else:
                    self.transient_status = ChargePointStatus.PREPARING

                if self.charge_station.eco_charge_status == Status.ENABLED and \
                        self.authorization_status == AuthorizationStatus.START:
                    self.interlock_control(True)

                if self.charge_station.status == ChargeStationStatus.ONBOARDING:
                    self.charge_station.enable_auto_start()

        elif control_pilot_state == ControlPilotStates.B2:
            if self.current_charge_session is not None:
                if self.authorization_status == AuthorizationStatus.FINISH:
                    self.transient_status = ChargePointStatus.FINISHING
                    self.immediate_charge = False
                else:
                    self.current_charge_session.pause()
                    self.transient_status = ChargePointStatus.SUSPENDED_EV
            else:
                self.transient_status = ChargePointStatus.SUSPENDED_EV
                if self.initialized is True:  # only start new session if chargepoint is initialized
                    self.authorization_mode.reset_authorization_timer()
                    logger.info("New charge session")
                    session_uuid = uuid.uuid1()
                    logger.info("session uuid: {0}".format(session_uuid))
                    initial_energy = self.active_energy.get_total()
                    self.current_charge_session = ChargeSession(
                        session_uuid,
                        self.authorization_mode.current_authorization_uid,
                        self,
                        start_energy=initial_energy,
                        stop_energy=initial_energy
                    )
                    self.current_charge_session.start()
                    self.charge_sessions[session_uuid] = \
                        self.current_charge_session

        elif control_pilot_state == ControlPilotStates.D1 or \
                control_pilot_state == ControlPilotStates.D2:
            self.transient_status = ChargePointStatus.FAULTED

        elif control_pilot_state == ControlPilotStates.E:
            self.transient_status = ChargePointStatus.FAULTED

        elif control_pilot_state == ControlPilotStates.F:
            self.transient_status = ChargePointStatus.FAULTED
        else:
            logger.info("Undefined control pilot state")
            
    def finish_session(self):
        self.current_charge_session.last_energy = \
            self.active_energy.get_total()
        self.current_charge_session.stop()
        self.transient_status = ChargePointStatus.FINISHING
        self.current_charge_session = None
        self.immediate_charge = False

    @property
    def authorization_status(self):
        return self._authorization_status

    @authorization_status.setter
    def authorization_status(self, value):
        self._authorization_status = value

        if value == AuthorizationStatus.FINISH:
            self.authorization_mode.reset_authorization_timer()

        if value == AuthorizationStatus.TIMEOUT or value == AuthorizationStatus.FINISH:
            self.clear_authorization_uid()

        if value is not None:
            msg = {
                "type": "AuthorizationStatus",
                "status": value.value
            }
            msg = json.dumps(msg)
            logger.info("Authorization Status: {0}".format(msg))
            self.send_to_mediator(msg, MessageTypes.AUTHORIZATION_STATUS)

    @property
    def authorization_response(self):
        return self._authorization_response

    @authorization_response.setter
    def authorization_response(self, value):
        self._authorization_response = value
        if value is not None:
            msg = {
                "idTagInfo": {
                    "status": value.value
                },
                "type": "AuthorizationResponse"
            }
            msg = json.dumps(msg)
            logger.info("Authorization Response: {0}".format(msg))
            self.send_to_mediator(msg, MessageTypes.AUTHORIZATION_RESPONSE)

    def update_current_session_metric(self):
        if self.current_charge_session is not None:
            self.current_charge_session.last_energy = self.active_energy.get_total()

    def start_charging(self):
        self.eco_charge_completed = False
        if self.current_charge_session is not None:
            self.current_charge_session.stop()
            self.current_charge_session = None
        start_charging_command = StartChargingCommand(self.charge_station)
        start_charging_command.execute()

    def stop_charging(self, finish_authorization=True):
        if finish_authorization is True:
            self.authorization_status = AuthorizationStatus.FINISH
            self.stop_requested = True
        stop_charging_command = StopChargingCommand(self.charge_station)
        stop_charging_command.execute()
        if self.current_charge_session is not None:
            if self.current_charge_session.status == ChargeSessionStatus.PAUSED or \
                    self.current_charge_session.status == ChargeSessionStatus.SUSPENDED:
                self.finish_session()

    def pause_charging(self):
        if self.current_charge_session is not None:
            pause_charging_command = PauseChargingCommand(self.charge_station)
            pause_charging_command.execute()

    def cancel_reservation(self, reservation_id):
        if self.reservation.reservation_status == Status.ENABLED and self.reservation.reservation_id == reservation_id:
            self.reservation = Reservation(Status.DISABLED)
            stop_blink_rez = PeripheralCommand(self.charge_station, PeripheralRequest.STOP_BLINK_REZ)
            stop_blink_rez.execute()

    def make_reservation(self, expiry_date, id_tag, reservation_id):
        if self.reservation.reservation_status == Status.ENABLED:
            self.cancel_reservation(self.reservation.reservation_id)
        self.reservation = Reservation(Status.ENABLED, expiry_date, id_tag, reservation_id)
        start_blink_rez = PeripheralCommand(self.charge_station, PeripheralRequest.START_BLINK_REZ)
        start_blink_rez.execute()
        if self.reservation_thread is None or not self.reservation_thread.isAlive():
            self.reservation_thread = threading.Thread(target=self.reservation_timer)
            self.reservation_thread.start()

    def check_reservation(self):
        if self.reservation.reservation_status == Status.ENABLED:
            expiry_datetime = self.reservation.expiry_date
            expiry_datetime = expiry_datetime.split("+")[0]
            expiry_datetime = expiry_datetime.split("Z")[0]
            expiry_datetime = expiry_datetime.split(".")[0]
            expiry_datetime = datetime.datetime.strptime(expiry_datetime, '%Y-%m-%dT%H:%M:%S')
            if expiry_datetime > datetime.datetime.now():
                msg = {
                    "type": "ReserveNow",
                    "expiryDate": self.reservation.expiry_date,
                    "connectorId": str(self.id),
                    "idTag": self.reservation.id_tag,
                    "reservationId": self.reservation.reservation_id
                }
                msg = json.dumps(msg)
                logger.info(msg)
                self.charge_station.mediator.send(msg, self.charge_station.zmq_message_handler,
                                                  MessageTypes.RESERVATION_REQUEST)
                if self.reservation_thread is None or not self.reservation_thread.isAlive():
                    self.reservation_thread = threading.Thread(target=self.reservation_timer)
                    self.reservation_thread.start()
            else:
                self.cancel_reservation(self.reservation.reservation_id)

    def reservation_timer(self):
        expiry_datetime = self.reservation.expiry_date
        expiry_datetime = expiry_datetime.split("+")[0]
        expiry_datetime = expiry_datetime.split("Z")[0]
        expiry_datetime = expiry_datetime.split(".")[0]
        expiry_datetime = datetime.datetime.strptime(expiry_datetime, '%Y-%m-%dT%H:%M:%S')
        while self.reservation.reservation_status == Status.ENABLED and expiry_datetime > datetime.datetime.now():
            time.sleep(1)
        self.cancel_reservation(self.reservation.reservation_id)

    def set_ocpp_current_limit(self, payload):
        set_current_limit_command = SetOcppCurrentLimitCommand(self.charge_station, payload)
        set_current_limit_command.execute()

    def authorization_start_indicators(self):
        authorization_start_indicator = AuthorizationStartIndicatorCommand(self.charge_station)
        authorization_start_indicator.execute()

    def authorization_stop_indicators(self):
        authorization_stop_indicator = AuthorizationStopIndicatorCommand(self.charge_station)
        authorization_stop_indicator.execute()

    def authorization_fail_indicators(self):
        authorization_fail_indicator = AuthorizationFailIndicatorCommand(self.charge_station)
        authorization_fail_indicator.execute()

    def card_removed_indicators(self):
        card_removed_indicator = CardRemovedIndicatorCommand(self.charge_station)
        card_removed_indicator.execute()

    def card_added_indicators(self):
        card_added_indicator = CardAddedIndicatorCommand(self.charge_station)
        card_added_indicator.execute()

    def authorization_finish_indicators(self):
        authorization_finish_indicator = AuthorizationFinishIndicatorCommand(self.charge_station, self.current_charge_session)
        authorization_finish_indicator.execute()

    def interlock_control(self, lock):
        if self.control_pilot_state == ControlPilotStates.B1 or \
                self.control_pilot_state == ControlPilotStates.C1:
            interlock_control = InterlockCommand(self.charge_station, lock)
            interlock_control.execute()

    def query_status(self, commandId):
        query_status_command = QueryStatusCommand(self.charge_station, commandId)
        query_status_command.execute()
        
    def query_charge_point_status_from_acpw(self):
        faults_command = QueryStatusCommand(self.charge_station, AcpwCommandId.FAULTS)
        faults_command.execute()
        proximity_state_command = QueryStatusCommand(self.charge_station, AcpwCommandId.PROXIMITY_STATE)
        proximity_state_command.execute()
        pilot_state_command = QueryStatusCommand(self.charge_station, AcpwCommandId.PILOT_STATE)
        pilot_state_command.execute()
        min_current_command = QueryStatusCommand(self.charge_station, AcpwCommandId.MIN_CURRENT)
        min_current_command.execute()
        max_current_command = QueryStatusCommand(self.charge_station, AcpwCommandId.MAX_CURRENT)
        max_current_command.execute()
        available_current_command = QueryStatusCommand(self.charge_station, AcpwCommandId.APP_AVAILABLE_CURRENT)
        available_current_command.execute()
        lockable_cable_command = QueryStatusCommand(self.charge_station, AcpwCommandId.LOCKABLE_CABLE)
        lockable_cable_command.execute()
        proximity_pilot_current_command = QueryStatusCommand(self.charge_station, AcpwCommandId.PROXIMITY_PILOT_CURRENT)
        proximity_pilot_current_command.execute()
        modbustcp_current_command = QueryStatusCommand(self.charge_station, AcpwCommandId.SET_MODBUSTCP_CURRENT)
        modbustcp_current_command.execute()

        time.sleep(5)  # Wait for acpw message responses

    def reboot_acpw(self):
        reboot_command = QueryStatusCommand(self.charge_station, AcpwCommandId.REBOOT)
        reboot_command.execute()

    def reset_acpw(self):
        reset_command = QueryStatusCommand(self.charge_station, AcpwCommandId.RESET)
        reset_command.execute()

    def report_status(self):
        msg = self._create_status_notification_message()
        logger.info("status notification : {0}".format(msg))
        self.charge_station.mediator.send(msg, self.charge_station, MessageTypes.STATUS_NOTIFICATION)
        self.authorization_status = self._authorization_status

    def send_to_mediator(self, message, messageType):
        if self.initialized is True:
            self.charge_station.mediator.send(message, self.charge_station, messageType)


class OtaManager:

    ACPW_UPDATE_TIMEOUT = 60 * 60  # One hour
    ACPW_UPDATE_MAX_RETRY = 5
    ACPW_OTA_FILE_PATH = "/usr/lib/vestel/acpw_update.bin"
    OSTREE_COMMIT_FILE = "/var/lib/vestel/update/commitID.txt"
    FIRMWARE_OTA_FILE = "/var/lib/vestel/update/update.bin"
    IS_OTA_DEPLOYED = "/var/lib/vestel/isOtaDeployed.txt"
    OTA_CERT_PATH = "/usr/lib/vestel/otaCert.crt"

    def __init__(self, charge_station):
        self.charge_station = charge_station
        self.update_thread = None
        self.ota_status_message_handler_thread = None
        self.previous_commit_id = None
        self.current_commit_id = None
        self.pending_commit_id = None
        self.ota_status = None
        self.acpw_ota_status = None
        self.ota_type = None
        self.acpw_ota_file = None
        self.ota_message_queue = queue.Queue()
        self.status_message_event = threading.Event()
        self.acpw_ota_progress_event = threading.Event()
        self.acpw_retry_count = 0
        self.target_acpw_version = ""
        self.expire_mutex = threading.Lock()
        self.expire_event = threading.Event()
        
    def update_ostree_status(self):
        ostree_status = os.popen('ostree admin status').read()
        status_output = list(ostree_status.split(" "))
        i = 0
        for item in status_output:
            if item == "arago":
                if status_output[i + 2] == "(pending)\n":
                    logger.info('pending commit: ' + status_output[i + 1].split(".")[0])
                    self.pending_commit_id = status_output[i + 1].split(".")[0]
                elif status_output[i + 2] == "(rollback)\n":
                    logger.info('previous commit: ' + status_output[i + 1].split(".")[0])
                    self.previous_commit_id = status_output[i + 1].split(".")[0]
                else:
                    logger.info('current commit: ' + status_output[i + 1].split(".")[0])
                    self.current_commit_id = status_output[i + 1].split(".")[0]
            i += 1

    def ota_boot_check(self):
        self.update_ostree_status()
        try:
            deployCheckFile = open(OtaManager.IS_OTA_DEPLOYED, "r")
            ostreeDeployed = deployCheckFile.read(1)
            deployCheckFile.close()
        except FileNotFoundError:
            logger.info("File not found: " + OtaManager.IS_OTA_DEPLOYED)
            ostreeDeployed = "0"

        if ostreeDeployed == "1":
            try:
                pending_commit_file = open(OtaManager.OSTREE_COMMIT_FILE, "r")
                pending_commit_id = pending_commit_file.read().split("\n")[0]
                pending_commit_file.close()
            except FileNotFoundError:
                logger.info("File not found: " + OtaManager.OSTREE_COMMIT_FILE)
                pending_commit_id = "0"

            if pending_commit_id == self.current_commit_id:
                logger.info("HMI updated successfully!")
                acpw_ota_thread = threading.Thread(target=self._acpw_ota_progress, daemon=True)
                acpw_ota_thread.start()

            else:
                logger.info("HMI failed to update! pendingCommit: {} currentCommit: {}".format(
                    pending_commit_id, self.current_commit_id
                ))
                self._ota_fail_actions()

    def get_acpw_version_message(self, version):
        if not self.acpw_ota_progress_event.isSet() and self.ota_status == OtaStatus.ACPW:  # Acpw OTA is in progress
            logger.info("Target acpw version: {}".format(self.target_acpw_version))
            logger.info("Current acpw version: {}".format(ChargeStation.read_acpw_version()))
            if self.target_acpw_version == ChargeStation.read_acpw_version():
                self.acpw_ota_status = AcpwOtaStatus.FINISHED_SUCCESS.value
                self.acpw_ota_progress_event.set()  # Force main loop for acpw_ota_progres to finish
                self.status_message_event.set()  # Force main loop for acpw_ota_progres to finish
                self.expire_event.set()  # Force acpw timeout thread to finish
                self.charge_station.query_charge_station_status_from_acpw()
                self.charge_station.charge_points[1].query_charge_point_status_from_acpw()
                logger.info("ACPW update finished")
            else:
                if self.acpw_retry_count < self.ACPW_UPDATE_MAX_RETRY:
                    start_blink_firmware = PeripheralCommand(
                        self.charge_station, PeripheralRequest.START_BLINK_FIRMWARE)
                    start_blink_firmware.execute()
                    self.acpw_retry_count += 1
                    logger.info("ACPW Retry: %s" % self.acpw_retry_count)

                    ota_start = OtaCommand(self.charge_station, AcpwCommandId.OTA_START, bytearray([2]))
                    ota_start.execute()

                    ota_status = OtaCommand(self.charge_station, AcpwCommandId.OTA_STATUS)
                    ota_status.execute()

                else:
                    self.acpw_ota_status = AcpwOtaStatus.FINISHED_FAIL.value
                    self.acpw_ota_progress_event.set()  # Force main loop for acpw_ota_progres to finish
                    self.status_message_event.set()  # Force main loop for acpw_ota_progres to finish
                    self.expire_event.set()  # Force acpw timeout thread to finish
                    logger.info("ACPW update failed after %s retry" % self.acpw_retry_count)

    def verify_ota_file(self, location):
        from OpenSSL import crypto
        try:
            f = open(location, "br")
            buffer = f.read()
            f.close()
            sig_size = buffer[-1]
            sig = buffer[(-1 - sig_size):-1]
            ota_bin = buffer[:(-1 - sig_size)]
            f = open(OtaManager.OTA_CERT_PATH)
            ss_buf = f.read()
            f.close()
            ss_cert = crypto.load_certificate(crypto.FILETYPE_PEM, ss_buf.encode())
            crypto.verify(ss_cert, sig, ota_bin, 'sha256')
            return True
        except crypto.Error:
            return False

    def get_ota_message(self, message):
        self.ota_message_queue.put(message)

    def ota_status_message_handler(self):
        while not self.acpw_ota_progress_event.isSet():
            if not self.ota_message_queue.empty():
                messageTuple = self.ota_message_queue.get()
                self._check_ota_status_message(messageTuple)
            time.sleep(0.2)

    def _check_ota_status_message(self, message):
        self.status_message_event.set()
        status = message[0]
        packetId = message[1]
        logger.info("ota status message received")
        if self.ota_status == OtaStatus.ACPW:
            self.acpw_ota_status = status
            if status == AcpwOtaStatus.NOT_READY.value:
                time.sleep(1)
                cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.OTA_STATUS.value, bytearray([]))
                self.charge_station.mediator.send(cmd, self.charge_station, MessageTypes.ACPW)
            elif status == AcpwOtaStatus.READY.value:
                dataPacket = [packetId] + self.acpw_ota_file[packetId * 512:(packetId + 1) * 512]
                cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.OTA_DATA.value, dataPacket)
                self.charge_station.mediator.send(cmd, self.charge_station, MessageTypes.ACPW)
                logger.info("Send OTA_DATA to ACPW id: %s" % packetId)
            elif status == AcpwOtaStatus.TRANSFER_COMPLETE.value:
                logger.info("ACPW update file has sent succesfully! ACPW will be updated!")
            else:
                logger.info("Received undefined ota status msg: %s" % status)
                self.acpw_ota_status = AcpwOtaStatus.NOT_READY.value
        else:
            logger.info("Received ota status msg from ACPW, but ota session is over!")

    def start_ota(self, ota_type, ota_params=None):

        if self.ota_status != None:
            logger.info('Extra OTA request is rejected')
            return

        self.ota_type = ota_type
        file_location = ota_params['data']['location']

        if self.verify_ota_file(file_location):
            logger.info("OTA file verification succeeded")
            now = datetime.datetime.now()
            retrieve_date = now
            
            try:
                retrieve_date = ota_params['data']['retrieveDate']
                retrieve_date = retrieve_date.split("+")[0]
                retrieve_date = retrieve_date.split("Z")[0]
                retrieve_date = retrieve_date.split(".")[0]
                retrieve_date = datetime.datetime.strptime(retrieve_date, '%Y-%m-%dT%H:%M:%S')
            except:
                logger.info("Ota retrieve date parse error {0}".format(traceback.format_exc()))

            delta_t = retrieve_date - now
            secs = delta_t.total_seconds()
            if secs < 0:
                secs = 0

            try:
                # TODO remove old extract folder if any
                with ZipFile(file_location, 'r') as zip_ref:
                    zip_ref.extractall('/var/lib/vestel/')
                    zip_ref.close()
            except FileNotFoundError:
                logger.info("File not found: " + file_location)
                self._ota_fail_actions()
                return

            logger.info("Ready to start ota")
            logger.info('remaining secs to OTA: %.2f' % secs)
            threading.Timer(secs, self._start_ostree_ota).start()

        else:
            logger.info("OTA file verification failed")
            self._ota_fail_actions()
            os.remove(file_location)

    def _ota_fail_actions(self):
        self.charge_station.firmware_status = FirmwareUpdateStatus.INSTALLATION_FAILED
        stop_blink_firmware = PeripheralCommand(
            self.charge_station, PeripheralRequest.STOP_BLINK_FIRMWARE)
        stop_blink_firmware.execute()
        self.ota_status = None

    def _start_ostree_ota(self):
        logger.info("Check cp availability for OTA")
        while self.charge_station.charge_points[1].cable_connected is True and self.charge_station.charge_points[1].is_authorized() is False:
            time.sleep(10)

        self.ota_status = OtaStatus.OSTREE
        self.charge_station.firmware_status = FirmwareUpdateStatus.INSTALLING

        start_blink_firmware = PeripheralCommand(
            self.charge_station, PeripheralRequest.START_BLINK_FIRMWARE)
        start_blink_firmware.execute()

        logger.info("Apply ostree update")
        staticApply = os.system('ostree static-delta apply-offline ' + OtaManager.FIRMWARE_OTA_FILE)
        if (staticApply != 0):
            logger.info("Wrong update file!: " + OtaManager.FIRMWARE_OTA_FILE)
            self._ota_fail_actions()
            return
        logger.info("updateFwFile: " + OtaManager.FIRMWARE_OTA_FILE)

        try:
            pending_commit_file = open(OtaManager.OSTREE_COMMIT_FILE, "r")
            pending_commit_id = pending_commit_file.read().split("\n")[0]
            pending_commit_file.close()
        except FileNotFoundError:
            logger.info("File not found: " + OtaManager.OSTREE_COMMIT_FILE)
            pending_commit_id = "0"
            self._ota_fail_actions()
            return
        logger.info("pending_commit_id: " + pending_commit_id)

        logger.info("Deploy ostree update")
        deploy = os.popen('ostree admin deploy ' + pending_commit_id).read()
        logger.info("deploy result: " + deploy)

        try:
            deployCheckFile = open(OtaManager.IS_OTA_DEPLOYED, "w")
            deployCheckFile.write("1")
            deployCheckFile.close()
        except FileNotFoundError:
            logger.info("File not found: " + OtaManager.IS_OTA_DEPLOYED)

        time.sleep(5)
        os.system("systemctl stop ocpp ui uid-reader midmeter")
        os.system("ifconfig wlan0 down")
        os.system("hciconfig hci0 down")
        os.system("reboot")

    def _acpw_ota_progress(self):

        self.acpw_ota_progress_event.clear()
        acpw_version = ''

        with open(OtaManager.ACPW_OTA_FILE_PATH, "rb") as acpw_ota_bin:
            acpw_ota_hex = list(acpw_ota_bin.read())
        logger.info("ACPW update file is read!")

        version_size = 0
        while acpw_ota_hex[version_size] != 0:
            self.target_acpw_version += chr(acpw_ota_hex[version_size])
            version_size += 1

        self.acpw_ota_file = acpw_ota_hex[version_size + 1:]
        current_acpw_version = ChargeStation.read_acpw_version()
        if current_acpw_version == self.target_acpw_version:
            logger.info("No need to ACPW update version: {}".format(current_acpw_version))
            self.acpw_ota_status = AcpwOtaStatus.FINISHED_SUCCESS.value
        else:
            self.ota_status = OtaStatus.ACPW

            start_blink_firmware = PeripheralCommand(
                self.charge_station, PeripheralRequest.START_BLINK_FIRMWARE)
            start_blink_firmware.execute()

            logger.info("ACPW updating from v%s to v%s" % (current_acpw_version, self.target_acpw_version))
            # acpwUpdateOngoing = 1
            self.ota_status = OtaStatus.ACPW  # ACPW update in progress
            ota_start = OtaCommand(self.charge_station, AcpwCommandId.OTA_START, bytearray([2]))
            ota_start.execute()

            ota_status = OtaCommand(self.charge_station, AcpwCommandId.OTA_STATUS)
            ota_status.execute()

            self.ota_status_message_handler_thread = threading.Thread(target=self.ota_status_message_handler, daemon=True)
            self.ota_status_message_handler_thread.start()
            
            expire_timer = threading.Thread(target=self._ota_expire_timer, daemon=True)
            expire_timer.start()

        while self.ota_status == OtaStatus.ACPW \
                and not self.expire_event.isSet() \
                and not self.acpw_ota_progress_event.isSet():
            self.status_message_event.clear()
            # we cannot use here self.status_message_event.wait(30) as we may not have RTC battery on the board
            # if device time is updated while wait(30) is working, it returns immediately and cause and extra 
            # ota status message to be sent, which brokes ota process on acpw side.
            status_timeout = 30.0
            while not self.status_message_event.isSet() and status_timeout >= 0.0:
                time.sleep(0.5)
                status_timeout -= 0.5
                
            if not self.status_message_event.isSet() and not self.expire_event.isSet() \
                    and not self.acpw_ota_progress_event.isSet() \
                    and not (self.acpw_ota_status == AcpwOtaStatus.TRANSFER_COMPLETE.value or
                             self.acpw_ota_status == AcpwOtaStatus.FINISHED_SUCCESS.value):
                cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.OTA_STATUS.value, bytearray([]))
                self.charge_station.mediator.send(cmd, self.charge_station, MessageTypes.ACPW)
                logger.info("Send *extra* OTA_STATUS to ACPW")

        try:
            deployCheckFile = open(OtaManager.IS_OTA_DEPLOYED, "w")
            deployCheckFile.write("0")
            deployCheckFile.close()
        except FileNotFoundError:
            logger.info("File not found: " + OtaManager.IS_OTA_DEPLOYED)

        self.status_message_event.set()
        self.acpw_ota_progress_event.set()
        self.expire_event.set()

        self.ota_status = None
        
        if self.acpw_ota_status == AcpwOtaStatus.FINISHED_SUCCESS.value:
            logger.info("ACPW updated succesfully!")
            self.charge_station.firmware_status = FirmwareUpdateStatus.INSTALLED
            stop_blink_firmware = PeripheralCommand(
                self.charge_station, PeripheralRequest.STOP_BLINK_FIRMWARE)
            stop_blink_firmware.execute()
            
        else:
            self.acpw_ota_status = AcpwOtaStatus.FINISHED_FAIL.value
            
            reset_acpw = GenericCommand(self.charge_station, AcpwCommandId.RESET)
            reset_acpw.execute()

            os.system('ostree admin deploy ' + self.previous_commit_id)
            self._ota_fail_actions()
            os.system("ifconfig wlan0 down")
            os.system("hciconfig hci0 down")
            os.system("reboot")
    
    def _ota_expire_timer(self):
        self.expire_event.clear()
        timeout = self.ACPW_UPDATE_TIMEOUT
        while timeout > 0 and not self.expire_event.isSet():
            time.sleep(1)
            timeout -= 1

        if timeout == 0:
            self.expire_event.set()

        logger.info("acpw timer expired")


class ChargeStation(Requester):

    def __init__(self, charge_point_dict=None):
        ChargeStation.initialize_logging()
        self.charge_points = charge_point_dict
        # if chargePoints is not None:
        #     self.chargePoints[1].chargeStation = self
        # self.chargePoints = dict()
        # self.chargePoints[1] = ChargePoint(self, 1)  # TODO right now we have only one charge point
        # self.authorizationMode = authorizationMode
        # self.__authenticationChecker = {
        #     "localList": self.__rfidLocalListAuthentication,
        #     "ocppList": self.__rfidOcppLocalListAuthentication,
        #     "acceptAll": self.__rfidAcceptAllAuthentication,
        # }
        self._rfid_error = 0
        self._mid_error = 0
        self.in_configuration = False
        self.configuration_manager = None
        self.meter = None
        self.drive_green_manager = None
        self.zmq_message_handler = None
        self.acpw_handler = None
        self.rfid_reader = None
        self.is_ocpp_offline_enabled = False
        self._status = ChargeStationStatus.INITIALIZING
        self.transition_status = self._status
        self._delay_charge_status = Status.DISABLED
        self._eco_charge_status = Status.DISABLED
        self.message_queue = queue.Queue()

        self.delay_charge_event = threading.Event()
        self.delay_charge_start_time = 0
        self.delay_charge_time = 0
        self.delay_charge_thread = None
        self._delay_charge_remaining_time = 0

        self.eco_charge_event = threading.Event()
        self.eco_charge_start_time = ""
        self.eco_charge_stop_time = ""
        self.eco_charge_thread = None

        self.wait_for_configuration_event = threading.Event()
        self.wait_for_master_addition_event = threading.Event()
        self._bt_connected = False
        self.ota_manager = OtaManager(self)
        self.maximum_current = 0
        self._firmware_status = None
        self.master_rfid_vfactory = None
        
        self.power_optimizer_min = 0
        self.power_optimizer_max = 0
        self._power_optimizer = 0
        self.phase_type = 0
        self.serial_number = ""
        self.acpw_version = ""
        self.ocpp_connected = False
        self.initialized = False

        super().__init__()
        factoryResetThread = threading.Thread(
            target=self.factory_reset_listener, daemon=True)
        factoryResetThread.start()

    @staticmethod
    def initialize_logging():
        if DEBUG:
            fileConfig("/home/root/logging.conf")
        else:
            fileConfig("/usr/lib/vestel/logging.conf")
        sl = StreamToLogger(logger, logging.ERROR)
        sys.stderr = sl
        logger.info("Logging module is initialized.")
        
    @property
    def firmware_status(self):
        return self._firmware_status

    @firmware_status.setter
    def firmware_status(self, value):
        self._firmware_status = value

        msg = {
            "type": "FirmwareUpdateStatus",
            "status": self._firmware_status.value,
        }
        msg = json.dumps(msg)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.FIRMWARE_UPDATE_STATUS)

        if value == FirmwareUpdateStatus.INSTALLING:
            self.status = ChargeStationStatus.INSTALLING_FIRMWARE
        elif value == FirmwareUpdateStatus.INSTALLED or value == FirmwareUpdateStatus.INSTALLATION_FAILED:
            time.sleep(5)
            if not self.ocpp_connected and not self.is_ocpp_offline_enabled:
                self.status = ChargeStationStatus.WAITING_FOR_CONNECTION
            else:
                self.status = ChargeStationStatus.NORMAL

    @property
    def power_optimizer(self):
        return self._power_optimizer

    @power_optimizer.setter
    def power_optimizer(self, value):
        self._power_optimizer = value
        self._report_property_update(self.power_optimizer, "powerOptimizer")

    @property
    def bt_connected(self):
        return self._bt_connected

    @bt_connected.setter
    def bt_connected(self, value):
        if value:
            logger.info("Received BT connect")
            self.wait_for_configuration_event.set()
        else:
            logger.info("Received BT disconnect")
            if self._bt_connected and self.in_configuration:
                self.wait_for_configuration_event.set()
                self.stop_master_configuration()
                if self.is_configured():
                    self.status = ChargeStationStatus.NORMAL
                else:
                    self.status = ChargeStationStatus.ONBOARDING
                    
        self._bt_connected = value
        
    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value
        msg = self._create_status_message()
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.CHARGE_STATION_STATUS)
        if self._status != ChargeStationStatus.INITIALIZING:
            self.initialized = True

    def _create_status_message(self):
        msg = {
            "type": "ChargeStationStatusNotification",
            "status": self._status.value,
        }
        msg = json.dumps(msg)
        return msg

    @property
    def delay_charge_status(self):
        return self._delay_charge_status

    @delay_charge_status.setter
    def delay_charge_status(self, value):
        self._delay_charge_status = value
        if value is not None:
            if value == Status.ENABLED:
                if self.eco_charge_status == Status.ENABLED:
                    self.update_eco_charge(Status.DISABLED)
                start_blink_delay = GenericCommand(
                    self, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.START_BLINK_DELAY)
                start_blink_delay.execute()
                self.charge_points[1].grant_authorization()
                self.charge_points[1].interlock_control(True)

                self.delay_charge_thread = threading.Thread(
                    target=self._delay_charge_control, daemon=True)
                self.delay_charge_thread.start()
            else:
                stop_blink_delay = GenericCommand(
                    self, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.STOP_BLINK_DELAY)
                stop_blink_delay.execute()
                if self.charge_points[1].authorization_status == AuthorizationStatus.FINISH:
                    self.charge_points[1].interlock_control(False)

            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "UPDATE chargeStation SET delayChargeStatus='{}', " \
                    "delayChargeStart={}, delayChargeTime={} WHERE ID=1;" \
                .format(self.delay_charge_status.value, self.delay_charge_start_time,
                        self.delay_charge_time)
            cursor.execute(query)
            conn.commit()
            conn.close()

            msg = self._create_delay_charge_status_message()
            logger.info(msg)
            self.mediator.send(msg, self, MessageTypes.DELAY_CHARGE)

    @property
    def delay_charge_remaining_time(self):
        return self._delay_charge_remaining_time

    @delay_charge_remaining_time.setter
    def delay_charge_remaining_time(self, value):
        self._delay_charge_remaining_time = value
        if value % 60 == 0:
            msg = self._create_delay_charge_status_message()
            logger.info(msg)
            self.mediator.send(msg, self, MessageTypes.DELAY_CHARGE)

    def _create_delay_charge_status_message(self):
        msg = {
            "type": "DelayChargeNotification",
            "status": self._delay_charge_status.value,
            "remainingTime": int(self._delay_charge_remaining_time / 60),
            "delayTime": int(self.delay_charge_time / 60)
        }
        return json.dumps(msg)

    @property
    def eco_charge_status(self):
        return self._eco_charge_status

    @eco_charge_status.setter
    def eco_charge_status(self, value):
        eco_charge_status_old = self._eco_charge_status
        self._eco_charge_status = value
        if value is not None:
            if value == Status.ENABLED:
                if self.delay_charge_status == Status.ENABLED:
                    self.update_delay_charge(Status.DISABLED)
                if eco_charge_status_old != Status.ENABLED:

                    if self.charge_points[1].current_charge_session is None:
                        if self.charge_points[1].authorization_status == AuthorizationStatus.START:
                            self.charge_points[1].interlock_control(True)

                        start_blink_eco = GenericCommand(
                            self, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.START_BLINK_ECO)
                        start_blink_eco.execute()

                    self.eco_charge_thread = threading.Thread(
                        target=self._eco_charge_control, daemon=True)
                    self.eco_charge_thread.start()
            else:
                self.eco_charge_start_time = ""
                self.eco_charge_stop_time = ""
                if self.charge_points[1].authorization_status == AuthorizationStatus.START:
                    self.charge_points[1].interlock_control(False)
                    self.charge_points[1].authorization_status = AuthorizationStatus.FINISH
                stop_blink_eco = GenericCommand(
                    self, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.STOP_BLINK_ECO)
                stop_blink_eco.execute()

            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "UPDATE chargeStation SET ecoChargeStatus='{}', " \
                    "ecoChargeStart='{}', ecoChargeStop='{}' WHERE ID=1;" \
                .format(self.eco_charge_status.value,
                        self.eco_charge_start_time, self.eco_charge_stop_time)
            cursor.execute(query)
            conn.commit()
            conn.close()

            msg = {
                "type": "EcoChargeNotification",
                "status": self._eco_charge_status.value,
                "startTime": self.eco_charge_start_time,
                "stopTime": self.eco_charge_stop_time
            }
            msg = json.dumps(msg)
            logger.info(msg)
            self.mediator.send(msg, self, MessageTypes.ECO_CHARGE)

    def report_status(self):
        msg = self._create_status_message()
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.CHARGE_STATION_STATUS)
        
    def _report_property_update(self, prop, prop_type):
        data = {
            "type": prop_type,
            "data": {
                "value": prop
            }
        }
        msg = json.dumps(data)
        self.mediator.send(msg, self, MessageTypes.PROPERTY_CHANGE)
        
    def query_charge_station_status_from_acpw(self):
        version_command = QueryStatusCommand(self, AcpwCommandId.VERSION)
        version_command.execute()
        serial_number_command = QueryStatusCommand(self, AcpwCommandId.SERIAL_NUMBER)
        serial_number_command.execute()
        device_cphome_current_command = QueryStatusCommand(self, AcpwCommandId.DEVICE_CPHOME_CURRENT)
        device_cphome_current_command.execute()
        app_cphome_current_command = QueryStatusCommand(self, AcpwCommandId.APP_CPHOME_CURRENT)
        app_cphome_current_command.execute()
        number_of_phase_command = QueryStatusCommand(self, AcpwCommandId.NUMBER_OF_PHASE)
        number_of_phase_command.execute()
        
        time.sleep(5)  # Wait for acpw message responses

    def initialize(self):
        # TODO read factory settings from vfactory.db
        self.message_parser_thread = threading.Thread(target=self._parse_message, daemon=True)
        self.message_parser_thread.start()
        self.configuration_manager = ConfigurationManager()
        self.configuration_manager.initialize_configurations()
        self.acpw_handler = AcpwMessageHandler()

        get_peripheral_data()

        self.rfid_reader = RfidReader()
        self.load_meter()

        self.zmq_message_handler = ZmqMessageHandler()
        message_mediator = MessageMediator(self, self.acpw_handler, self.meter,
                                           self.rfid_reader, self.zmq_message_handler, self.configuration_manager, self.drive_green_manager)

        self.zmq_message_handler.start()
        self.acpw_handler.start()

        self.status = ChargeStationStatus.INITIALIZING

        charge_points = dict()
        charge_points[1] = ChargePoint(1, self)
        self.load_master_card()
        
        # conn = sqlite3.connect(AGENT_DATABASE)
        # cursor = conn.cursor()
        # query = "SELECT * FROM chargePoints;"
        # cursor.execute(query)
        # self.charge_points = dict()
        # rows = cursor.fetchall()
        # if len(rows) > 0:
        #     for row in rows:
        #         chargePointId, controlPilotState, proximityPilotState, status, \
        #             errorCode, vendorErrorCode, voltageP1, \
        #             voltageP2, voltageP3, currentP1, currentP2, currentP3, \
        #             activePowerP1, activePowerP2, activePowerP3, activeEnergyP1, \
        #             activeEnergyP2, activeEnergyP3, lastUpdate, availability, \
        #             minCurrent, maxCurrent, availableCurrent, lockableCable, \
        #             reservation_status, expiry_date, id_tag, reservation_id, external_charge, \
        #             currentOffVal, currentOffReason = row
        #         self.charge_points[chargePointId] = ChargePoint(
        #             chargePointId, self, None, voltageP1, voltageP2, voltageP3,
        #             currentP1, currentP2, currentP3,
        #             activePowerP1, activePowerP2, activePowerP3,
        #             activeEnergyP1, activeEnergyP2, activeEnergyP3,
        #             ControlPilotStates(controlPilotState), ProximityPilotStates(proximityPilotState), None,
        #             ChargePointStatus(status), ChargePointErrorCode(errorCode),
        #             vendorErrorCode, ChargePointAvailability(availability),
        #             minCurrent, maxCurrent, availableCurrent, lockableCable,  
        #             Status(reservation_status), expiry_date, id_tag, reservation_id,
        #             external_charge, currentOffVal, CurrentOfferedToEvReason(currentOffReason)
        #         )
        # else:
        #     self.charge_points[1] = ChargePoint(1, self)  # TODO only one for now
        # conn.close()
        
        # time.sleep(5)
        self.load_authorization()
        self.load_station_settings()
        self.charge_points[1].initialize()
        self.load_eco_delay_charge()
        self.charge_points[1].retrieve_last_charge_session()
        
        self.initialize_hostname_configuration()
        
        if self.has_bluetooth_interface():
            self.initialize_bluetooth_configuration()
            
        # if self.has_master_rfid() and \
        #         not isinstance(
        #             self.charge_points[1].authorization_manager.authorization_mode,
        #             OcppAuthorization):
        #     if self.is_configured():
        #         self.drive_green_manager = DriveGreenManager()
        #         self.mediator.drive_green_manager = self.drive_green_manager
        #         self.mediator.bluetooth_handler = BluetoothHandler()
        #         self.mediator.bluetooth_handler.start()
        
        self.check_station_initial_status()
        
        self.ota_manager.ota_boot_check()

        self.meter.start_query()
        self.rfid_reader.start()

        self.zmq_message_handler.join()
        self.drive_green_manager.join()

    def check_station_initial_status(self):
        logger.info("check initial status")
        try:
            deployCheckFile = open(OtaManager.IS_OTA_DEPLOYED, "r")
            ostreeDeployed = deployCheckFile.read(1)
            deployCheckFile.close()
        except FileNotFoundError:
            logger.info("File not found: " + OtaManager.IS_OTA_DEPLOYED)
            ostreeDeployed = "0"

        if ostreeDeployed == "1":
            self.status = ChargeStationStatus.INSTALLING_FIRMWARE

        if self.configuration_manager.waiting_for_master_addition and \
                self.status != ChargeStationStatus.INSTALLING_FIRMWARE:
            logger.info("Waiting master addition")
            self.delete_old_master_configuration()
            self.start_master_addition()
            return

        if self.charge_points[1].authorization_mode is not None:
            if isinstance(self.charge_points[1].authorization_mode, DriveGreenAuthorization):

                if not self.is_configured() and self.has_master_rfid() and self.status != ChargeStationStatus.INSTALLING_FIRMWARE:
                    self.status = ChargeStationStatus.ONBOARDING
                    # self.transition_status = self.status
                    return
                elif self.is_configured():
                    self.drive_green_manager = DriveGreenManager()
                    self.mediator.drive_green_manager = self.drive_green_manager
                    if self.status != ChargeStationStatus.INSTALLING_FIRMWARE:
                        self.status = ChargeStationStatus.NORMAL
                elif not self.is_configured() and not self.has_master_rfid() and \
                        self.status != ChargeStationStatus.INSTALLING_FIRMWARE:
                    self.start_master_addition()
                return
            elif isinstance(self.charge_points[1].authorization_mode, OcppAuthorization) and \
                    self.status != ChargeStationStatus.INSTALLING_FIRMWARE:
                if self.ocpp_connected or self.is_ocpp_offline_enabled:
                    self.status = ChargeStationStatus.NORMAL
                else:        
                    self.status = ChargeStationStatus.WAITING_FOR_CONNECTION
                self.check_ocpp_connection_status()
                return

        if self.status != ChargeStationStatus.INSTALLING_FIRMWARE:
            self.status = ChargeStationStatus.NORMAL
            
    def initialize_hostname_configuration(self):
        try:
            conn = sqlite3.connect(VFACTORY_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT customer, model FROM deviceDetails WHERE id=1;"
            cursor.execute(query)
            row = cursor.fetchone()
            conn.close()

            if row is not None:
                customer, model = row
                advertising_name = "_".join([customer[:10], model[:5]])
            else:
                advertising_name = "_".join(["VESTEL", "EVC04"])

        except:
            logger.info("vfactory access issue {0}".format(
                traceback.format_exc()))
            advertising_name = "_".join(["VESTEL", "EVC04"])

        os.system("hostnamectl set-hostname {}".format(advertising_name))
        logger.info("Hostname is successfully configured to: {}".format(advertising_name))

    def has_bluetooth_interface(self):
        # Get verbose output for all usb devices
        bt_interface_check_string = subprocess.getoutput('lsusb -v')

        # Check if verbose descriptions contain bluetooth
        if bt_interface_check_string and 'Bluetooth' in bt_interface_check_string:
            return True

        # If bluetooth is not mentioned, return False
        return False

    def initialize_bluetooth_configuration(self):
        server_mac_addr = BluetoothHandler.get_local_bdaddr()

        # If server_mac_addr is not valid abort configuration
        if not server_mac_addr:
            return

        try:
            conn = sqlite3.connect(VFACTORY_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT customer, model FROM deviceDetails WHERE id=1;"
            cursor.execute(query)
            row = cursor.fetchone()
            conn.close()

            if row is not None:
                customer, model = row
                advertising_name = "_".join([customer, model, server_mac_addr[-11:]])
            else:
                advertising_name = "_".join(["VESTEL", "EVC04", server_mac_addr[-11:]])

        except:
            logger.info("vfactory access issue {0}".format(
                traceback.format_exc()))
            advertising_name = "_".join(["VESTEL", "EVC04", server_mac_addr[-11:]])

        BluetoothHandler.setBluetoothConfiguration("Name", advertising_name)
        os.system("systemctl restart bluetooth")
        logger.info("Bluetooth name and alias are successfully configured to: {}".format(advertising_name))

    def load_station_settings(self):
        self.query_charge_station_status_from_acpw()
        
    def load_eco_delay_charge(self):
        conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "SELECT * FROM chargeStation;"
        cursor.execute(query)
        row = cursor.fetchone()
        conn.close()
        if row is not None:
            ID, eco_charge_status, eco_charge_start, eco_charge_stop, delay_charge_status, delay_charge_start, \
                delay_charge_time, power_optimizer_min, power_optimizer_max, power_optimizer, phase_type = row
            if delay_charge_status == Status.ENABLED.value:
                current_time = int(datetime.datetime.now().timestamp())
                logger.info(current_time)
                logger.info(delay_charge_start)
                if current_time > int(delay_charge_start):
                    self.delay_charge_start_time = 0
                    self.delay_charge_status = Status.DISABLED
                else:
                    self.delay_charge_start_time = delay_charge_start
                    self._delay_charge_remaining_time = \
                        self.delay_charge_start_time - int(datetime.datetime.now().timestamp())
                    self.delay_charge_time = delay_charge_time
                    self.delay_charge_status = Status(delay_charge_status)

            if eco_charge_status == Status.ENABLED.value:
                self.eco_charge_start_time = eco_charge_start
                self.eco_charge_stop_time = eco_charge_stop
                self.eco_charge_status = Status(eco_charge_status)

    def load_meter(self):
        if os.path.exists(VFACTORY_DATABASE):
            conn = sqlite3.connect(VFACTORY_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT meterType FROM deviceDetails WHERE ID=1"
            cursor.execute(query)
            meter_type = cursor.fetchone()
            conn.close()
            if meter_type is not None:
                meter_type = meter_type[0]
                if meter_type == MeterType.KLEFR_MONO_PHASE.value:
                    self.meter = MidMeter()
                elif meter_type == MeterType.KLEFR_TRI_PHASE.value:
                    self.meter = MidMeter()
                else:
                    self.meter = InternalMeter()
            else:
                self.meter = InternalMeter()

        else:
            if os.path.exists("/run/media/mmcblk1p3/factorySettings.json"):
                with open('/run/media/mmcblk1p3/factorySettings.json', 'r') as f:
                    try:
                        factory_json = json.load(f)
                        meter_type = factory_json['data']['meterType']
                        if meter_type is not None:
                            if meter_type == "MID":
                                self.meter = MidMeter()
                            else:
                                self.meter = InternalMeter()
                        else:
                                self.meter = InternalMeter()
                    except:
                        self.meter = InternalMeter()
                        logger.info("cannot read factory settings: {}".format(traceback.format_exc()))
            else:
                self.meter = InternalMeter()

    def is_configured(self):
        conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "SELECT configured FROM hmiDetails;"
        cursor.execute(query)
        configured = cursor.fetchone()
        cursor.close()
        conn.close()
        if configured is not None:
            return configured[0] == 1
        return False

    def load_authorization(self):
        
        self.set_authorization()

    def set_authorization(self, row=None):
        authorization = None
        if row is None:
            try:
                conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
                cursor = conn.cursor()
                query = "SELECT id, mode, localList FROM authorizationMode;"
                cursor.execute(query)
                row = cursor.fetchone()
                cursor.close()
                conn.close()
            except:
                pass
         
        if row is not None:
            row_id, mode, local_list = row

            if mode == "driveGreen":
                local = set()
                
                if local_list is not None and local_list != "":
                    local = set(local_list.split(","))
                authorization = DriveGreenAuthorization(local, self.charge_points[1])
            else:
                if self.drive_green_manager is not None:
                    self.drive_green_manager.stop()
                    self.drive_green_manager = None
                if mode == "ocppList":
                    logger.info("ocpp authorization set")
                    authorization = OcppAuthorization(self.charge_points[1])
                    self.ocpp_connected = False
                    if self.initialized and not self.is_ocpp_offline_enabled:
                        self.status = ChargeStationStatus.WAITING_FOR_CONNECTION
                    self.check_ocpp_connection_status()
                elif mode == "acceptAll":
                    authorization = AcceptAllAuthorization(self.charge_points[1])
                elif mode == "localList":
                    local = set()
                    if local_list is not None and local_list != "":
                        local = set(local_list.split(","))
                    authorization = LocalAuthorization(local, self.charge_points[1])
                elif mode == "autoStart":
                    authorization = NoAuthorization(self.charge_points[1])
                else:
                    authorization = None
                    logger.info("Undefined authorization")

        self.charge_points[1].authorization_mode = authorization

    def check_ocpp_connection_status(self):
        msg = {
            "type": "getOcppConnectionStatus"
        }
        msg = json.dumps(msg)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.OCPP)

    def add_charge_point(self, chargePoint):
        if self.charge_points is None:
            self.charge_points = dict()
        self.charge_points[chargePoint.id] = chargePoint

    @property
    def rfid_error(self):
        return self._rfid_error

    @rfid_error.setter
    def rfid_error(self, valueDict):
        self._rfid_error = valueDict["value"]
        rfid_error_command = HmiErrorCommand(self, self._rfid_error | self._mid_error)
        rfid_error_command.execute()

    @property
    def mid_error(self):
        return self._mid_error

    @mid_error.setter
    def mid_error(self, valueDict):
        self._mid_error = valueDict["value"]
        mid_error_command = HmiErrorCommand(self, self._mid_error | self._rfid_error)
        mid_error_command.execute()

    def get_message(self, message, messageType):
        self.message_queue.put({"message": message, "messageType": messageType})

    def add_or_remove_user_card(self, uid):
        if self.charge_points[1].authorization_mode.contains_uid_inset(uid):
            self.charge_points[1].authorization_mode.remove_from_set(uid)
            self.status = ChargeStationStatus.REMOVED_USER_CARD
            long_beep = GenericCommand(
                self, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.TWO_LONG_BEEP)
            long_beep.execute()
            time.sleep(5)
        else:
            self.charge_points[1].authorization_mode.add_to_set(uid)
            self.status = ChargeStationStatus.ADDED_USER_CARD
            short_beep = GenericCommand(
                self, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.TWO_SHORT_BEEP)
            short_beep.execute()
            time.sleep(5)
            # TODO chargeStationStatus change
        
        self.wait_for_configuration_event.set()
        self.stop_master_configuration()
        self.finish_master_configuration()
        self.status = ChargeStationStatus.NORMAL

    def is_master_rfid(self, uid):
        if isinstance(cs.charge_points[1].authorization_mode, DriveGreenAuthorization):
            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT masterCard FROM hmiDetails WHERE ID=1;"
            cursor.execute(query)
            master_rfid = cursor.fetchone()
            conn.close()
            master_rfid = master_rfid[0]
            if master_rfid is not None and master_rfid != "":
                if uid == master_rfid:
                    return True
                return False
            else:
                if self.master_rfid_vfactory is not None \
                        and self.master_rfid_vfactory != "":
                    if uid == self.master_rfid_vfactory:
                        return True
                return False
        return False

    def load_master_card(self):
        if os.path.exists(VFACTORY_DATABASE):
            conn = sqlite3.connect(VFACTORY_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT masterRfid FROM deviceDetails WHERE id=1;"
            cursor.execute(query)
            master_rfid = cursor.fetchone()
            conn.close()
            self.master_rfid_vfactory = master_rfid[0]

    def has_master_rfid(self):
        conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "SELECT masterCard FROM hmiDetails WHERE ID=1;"
        cursor.execute(query)
        master_rfid_agent = cursor.fetchone()
        conn.close()
        master_rfid_agent = master_rfid_agent[0]
        if master_rfid_agent is not None and master_rfid_agent != "":
            logger.info("master rfid is defined")
            return True
        else:
            if self.master_rfid_vfactory is not None \
                    and self.master_rfid_vfactory != "":
                logger.info("master rfid is defined")
                return True
            logger.info("master rfid is not defined")
            return False

    def start_master_configuration(self):

        self.drive_green_manager = DriveGreenManager()
        self.mediator.drive_green_manager = self.drive_green_manager
        start_blink_configuration = PeripheralCommand(
                        self, PeripheralRequest.CONFIG_MODE_START)
        start_blink_configuration.execute()

        master_beep = PeripheralCommand(
                        self, PeripheralRequest.TWO_SHORT_BEEP)
        master_beep.execute()

        logger.info("Starting drive green configuration mode")
        # self.transition_status = self.status
        self.in_configuration = True
        self.mediator.bluetooth_handler = BluetoothHandler()

        try:
            logger.info("Starting BT pairing mode")
            self.mediator.bluetooth_handler.start()
            self.wait_for_configuration()
        except:
            logger.info("No bluetooth! {}".format(traceback.format_exc()))
            self.stop_master_configuration()

    def stop_master_configuration(self):
        if self.in_configuration:
            stop_blink_configuration = GenericCommand(
                self, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.CONFIG_MODE_STOP)
            stop_blink_configuration.execute()
            logger.info("Stop master configuration mode")
            self.in_configuration = False
            self.mediator.bluetooth_handler.stop()

    def finish_master_configuration(self):
        conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "UPDATE hmiDetails SET configured=1 WHERE ID=1;"
        cursor.execute(query)
        conn.commit()
        conn.close()
        # self.status = ChargeStationStatus.NORMAL

    def delete_old_master_configuration(self):
        logger.info("delete old master configuration")
        conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "UPDATE authorizationMode SET localList=NULL WHERE id=1;"
        cursor.execute(query)
        conn.commit()
        conn.close()

        conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "UPDATE hmiDetails SET configured=0, masterCard=NULL WHERE ID=1;"
        cursor.execute(query)
        conn.commit()
        conn.close()

        self.load_authorization()

    def start_master_addition(self):
        logger.info("master set start")
        self.status = ChargeStationStatus.WAITING_FOR_MASTER_ADDITION
        rfid_config_blink_start = GenericCommand(
            self, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.RFID_CONFIG_MODE_START)
        rfid_config_blink_start.execute()

        wait_master_thread = threading.Thread(target=self._wait_for_master_addition, daemon=True)
        wait_master_thread.start()

    def _wait_for_master_addition(self):
        timeout = 60
        self.wait_for_master_addition_event.clear()
        while not self.wait_for_master_addition_event.isSet() and timeout > 0:
            self.wait_for_master_addition_event.wait(1.0)
            timeout -= 1

        self.stop_master_addition()

        if timeout == 0 and not self.wait_for_master_addition_event.isSet():
            # TODO no card is set as master, enable autostart mode in driveGreen
            self.enable_auto_start()

    def enable_auto_start(self):
        logger.info("enable autostart mode")
        self.set_authorization((0, "driveGreen", ""))
        if self.in_configuration:
            self.wait_for_configuration_event.set()
            self.stop_master_configuration()
        self.finish_master_configuration()
        self.status = ChargeStationStatus.NORMAL
        
    def stop_master_addition(self):
        logger.info("master set stop")
        self.status = ChargeStationStatus.NORMAL
        rfid_config_blink_stop = GenericCommand(
            self, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.RFID_CONFIG_MODE_STOP)
        rfid_config_blink_stop.execute()

    def wait_for_configuration(self):
        self.wait_for_configuration_event.clear()
        self.status = ChargeStationStatus.WAITING_FOR_CONFIGURATION
        wait_configuration_thread = threading.Thread(target=self._wait_for_configuration, daemon=True)
        wait_configuration_thread.start()

    def _wait_for_configuration(self):
        timeout = 60
        while not self.wait_for_configuration_event.isSet() and timeout > 0:
            self.wait_for_configuration_event.wait(1.0)
            timeout -= 1

        if timeout == 0 and not self.wait_for_configuration_event.isSet():
            self.stop_master_configuration()
            if self.is_configured():
                self.status = ChargeStationStatus.NORMAL
            else:
                self.status = ChargeStationStatus.ONBOARDING

    def get_rfid_message(self, message):
        rfid_message = json.loads(message)
        if rfid_message['type'] == "rfidEvent":
            card_uid = rfid_message['data']['value']

            charge_point_id = 1
            # TODO right now we only have one charge point,
            #  should check chargePoint id in the future.

            if self.status == ChargeStationStatus.WAITING_FOR_CONFIGURATION:
                if not self.is_master_rfid(card_uid):
                    self.add_or_remove_user_card(card_uid)

            elif self.status == ChargeStationStatus.ONBOARDING:
                # authorization_start_indicator = AuthorizationStartIndicatorCommand(self)
                # authorization_start_indicator.execute()
                if self.is_master_rfid(card_uid) and wifiExists():
                    self.start_master_configuration()
                else:
                    authorization_fail_indicator = AuthorizationFailIndicatorCommand(self)
                    authorization_fail_indicator.execute()
            elif self.status == ChargeStationStatus.WAITING_FOR_MASTER_ADDITION:
                # authorization_start_indicator = AuthorizationStartIndicatorCommand(self)
                # authorization_start_indicator.execute()
                self.wait_for_master_addition_event.set()
                conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                cursor = conn.cursor()
                query = "UPDATE hmiDetails SET masterCard='{}' WHERE ID=1;".format(card_uid)
                cursor.execute(query)
                conn.commit()
                conn.close()
                master_set_beep = GenericCommand(
                    self, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.MASTER_SET_BEEP)
                master_set_beep.execute()
                self.status = ChargeStationStatus.ONBOARDING
            elif self.status == ChargeStationStatus.NORMAL:
                if self.charge_points[charge_point_id].status == ChargePointStatus.AVAILABLE and \
                        self.is_master_rfid(card_uid) and wifiExists():
                    self.start_master_configuration()
                else:
                    self.charge_points[charge_point_id].authorize(card_uid)
            elif self.status == ChargeStationStatus.INSTALLING_FIRMWARE:
                # If an OTA update is ongoing ignore RFID auth
                logger.info("Ignoring RFID auth check due to firmware installation")
            else:
                authorization_start_indicator = AuthorizationStartIndicatorCommand(self)
                authorization_start_indicator.execute()
                logger.info("ChargeStationStatus={}, ignore rfid".format(self.status.value))
                authorization_fail_indicator = AuthorizationFailIndicatorCommand(self)
                authorization_fail_indicator.execute()

            # authorization_stop_indicator = AuthorizationStopIndicatorCommand(self)
            # authorization_stop_indicator.execute()

        elif rfid_message['type'] == "rfidAlarm":
            if rfid_message['data']['value'] == "ConnectionError":
                # New error value for rfid_error is 1 (00000001)
                self.rfid_error = {"value": 1, "message": message}
            elif rfid_message['data']['value'] == "ConnectionRecover":
                self.rfid_error = {"value": 0, "message": message}

            # self.mediator.send(message, self, "zmq")
            # cmd = AcpwMessageHandler.createAcpwMessage(Command.HMI_BOARD_ERR.value, payload)
            # if cmd is not None:
            #     cmdStr = Command.toString(Command.HMI_BOARD_ERR.value)
            #     if cmd is not None:
            #         logger.info("Send %s to acpw" % cmdStr)
            #         self.mediator.send(cmd, self, "acpw")
            #         self.mediator.send(message, self, "zmq")

        else:
            logger.info("Unidentified rfid message")

    def _parse_message(self):

        while True:
            if not self.message_queue.empty():
                try:
                    messageDict = self.message_queue.get()
                    message = messageDict["message"]
                    message_type = messageDict["messageType"]
                    json_object = json.loads(message)
                    charge_point_id = 1  # TODO right now we only have one charge point, should check chargePoint id in the future.
                    if message_type == MessageTypes.ACPW \
                            or message_type == MessageTypes.EXTERNAL_METER:
                        json_type = json_object['type']
                        if json_type == "voltageEvent":
                            self.charge_points[charge_point_id].voltage = \
                                Voltage(json_object['data']['P1'],
                                        json_object['data']['P2'],
                                        json_object['data']['P3'])

                        elif json_type == "currentEvent":
                            self.charge_points[charge_point_id].current = \
                                Current(json_object['data']['P1'],
                                        json_object['data']['P2'],
                                        json_object['data']['P3'])

                        elif json_type == "activePowerEvent":
                            self.charge_points[charge_point_id].active_power = \
                                Power(json_object['data']['P1'],
                                      json_object['data']['P2'],
                                      json_object['data']['P3'])

                        elif json_type == "totalEnergyEvent":
                            self.charge_points[charge_point_id].active_energy = \
                                Energy(json_object['data']['P1'],
                                       json_object['data']['P2'],
                                       json_object['data']['P3'])

                        elif json_type == "midConnection":
                            logger.info("MID connection status changed: %s" % json_object['data'])
                            if json_object['data'] == "ConnectionLost":
                                # New error value for mid_error is 2 (00000010)
                                self.mid_error = {"value": 2, "message": message}
                            else:
                                self.mid_error = {"value": 0, "message": message}

                        elif json_type == "pilotState":
                            self.charge_points[charge_point_id].control_pilot_state = ControlPilotStates(
                                json_object['data']['value'])

                        elif json_type == "faultState":
                            self.charge_points[charge_point_id].error_code = json_object['data']['value']

                        elif json_type == "proximityState":
                            self.charge_points[charge_point_id].proximity_pilot_state = ProximityPilotStates(
                                json_object['data']['value'])

                        elif json_type == "maximumCurrent":
                            self.charge_points[charge_point_id].maximum_current = json_object['data']['value']

                        elif json_type == "otaStatus":
                            if self.ota_manager is not None:
                                self.ota_manager.get_ota_message(
                                    (json_object['data']['value'], json_object['data']['packetId'])
                                )

                        elif json_type == "acpwVersion":
                            if self.ota_manager is not None:
                                self.acpw_version = json_object['data']['value']

                                if os.path.exists(AGENT_DATABASE):
                                    connection = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                                    if connection:
                                        cursor = connection.cursor()
                                        query = "INSERT OR IGNORE INTO deviceDetails(ID, acpwVersion) " \
                                                "VALUES(1, '{0}');".format(self.acpw_version)
                                        cursor.execute(query)
                                        query = "UPDATE deviceDetails SET acpwVersion='{}' WHERE ID=1;".format(
                                            self.acpw_version)
                                        cursor.execute(query)
                                        logger.info("ACPW version is updated in db")
                                        connection.commit()
                                        connection.close()
                                    else:
                                        logger.info("Database connection is failed! for acpw version update")

                                self.ota_manager.get_acpw_version_message(self.acpw_version)
                                
                        elif json_type == "minCurrent":
                            self.charge_points[charge_point_id].minimum_current = json_object['data']['value']

                        elif json_type == "proximityPilotCurrent":
                            self.charge_points[charge_point_id].proximity_pilot_current = json_object['data']['value']

                        elif json_type == "modbusTcpCurrent":
                            self.charge_points[charge_point_id].modbustcp_current = json_object['data']['value']

                        elif json_type == "availableCurrent":
                            self.charge_points[charge_point_id].available_current = json_object['data']['value']
                                
                        elif json_type == "serialNumber":
                            self.serial_number = json_object['data']['value']

                            if os.path.exists(AGENT_DATABASE):
                                connection = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                                if connection:
                                    cursor = connection.cursor()
                                    query = "INSERT OR IGNORE INTO deviceDetails(ID, acpwSerialNumber) " \
                                            "VALUES(1, '{0}');".format(self.serial_number)
                                    cursor.execute(query)
                                    query = "UPDATE deviceDetails SET acpwSerialNumber='{0}' WHERE ID=1;".format(
                                        self.serial_number)
                                    cursor.execute(query)
                                    logger.info("Serial number is updated in db")
                                    connection.commit()
                                    connection.close()
                                else:
                                    logger.info("Database connection is failed for serial number update!")
                        
                        elif json_type == "lockableCable":
                            self.charge_points[charge_point_id].lockable_cable = json_object['data']['value']
                            
                        elif json_type == "powerOptimizerLimits":
                            self.power_optimizer_min = json_object['data']['min']
                            self.power_optimizer_max = json_object['data']['max']

                            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                            cursor = conn.cursor()
                            query = "UPDATE chargeStation SET powerOptimizerMin={0}, powerOptimizerMax={1} WHERE ID=1;".format(
                                self.power_optimizer_min, self.power_optimizer_max)
                            cursor.execute(query)
                            conn.commit()
                            conn.close()

                        elif json_type == "phaseType":
                            self.phase_type = PhaseType(json_object['data']['value'])

                            self.number_of_phases = True
                            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                            cursor = conn.cursor()
                            query = "UPDATE chargeStation SET phaseType={0} WHERE ID=1;".format(self.phase_type.value)
                            cursor.execute(query)
                            conn.commit()
                            conn.close()

                            # if self.dlm_message_handler is not None:
                            #     if self.number_of_phases == True and self.dlm_info == True:
                            #         msg = {
                            #             "type": "dlmSlaveParametersRequest"
                            #         }
                            #         msg = json.dumps(msg)
                            #         self.mediator.send(msg, self, MessageTypes.DLM_SLAVE_PARAMETERS_REQUEST)

                        elif json_type == "powerOptimizer":
                            self.power_optimizer = json_object['data']['value']
                            
                            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                            cursor = conn.cursor()
                            query = "UPDATE chargeStation SET powerOptimizer={0} WHERE ID=1;".format(
                                self.power_optimizer)
                            cursor.execute(query)
                            conn.commit()
                            conn.close()

                        elif json_type == "currentOfferedEv":
                            self.charge_points[charge_point_id].current_offered_value = json_object['data']['value'][
                                'current']
                            self.charge_points[charge_point_id].current_offered_reason = CurrentOfferedToEvReason(
                                json_object['data']['value'][
                                    'reason'])
                        
                        elif json_type == "externalCharge":
                            self.charge_points[charge_point_id].external_charge = json_object['data']['value']

                    elif message_type == MessageTypes.AVAILABLE_CURRENT:
                        value = json_object['data']['value']
                        app_current_limit_command = SetAppCurrentLimitCommand(self, value)
                        app_current_limit_command.execute()

                    elif message_type == MessageTypes.LOCKABLE_CABLE:
                        value = json_object['data']['value']
                        lockable_cable_command = SetLockableCableCommand(self, value)
                        lockable_cable_command.execute()
                        
                    elif message_type == MessageTypes.POWER_OPTIMIZER:
                        value = json_object['data']['value']
                        power_optimizer_command = SetPowerOptimizerCommand(self, value)
                        power_optimizer_command.execute()

                    elif message_type == MessageTypes.BLUETOOTH_STATUS:
                        if json_object['status'] == "Connected":
                            self.bt_connected = True
                        elif json_object['status'] == "Disconnected":
                            self.bt_connected = False

                    elif message_type == MessageTypes.REGISTRATION_FAIL:
                        if json_object['status'] != "NoInternetConnection":
                            self.stop_master_configuration()
                            if self.is_configured():
                                self.status = ChargeStationStatus.NORMAL
                            else:
                                self.status = ChargeStationStatus.ONBOARDING

                    else:
                        json_type = json_object['type']
                        if json_type == "command":
                            cmd_id = json_object["data"]["commandId"]
                            cmd_id = AcpwCommandId(cmd_id)
                            payload = json_object["data"]["payload"]

                            if cmd_id == AcpwCommandId.PILOT_STATE:
                                self.charge_points[charge_point_id].query_status(cmd_id)

                            elif cmd_id == AcpwCommandId.VOLTAGE:
                                pass
                            elif cmd_id == AcpwCommandId.CURRENT:
                                pass
                            elif cmd_id == AcpwCommandId.ENERGY:
                                pass
                            elif cmd_id == AcpwCommandId.POWER:
                                pass
                            elif cmd_id == AcpwCommandId.START_CHARGING:
                                logger.info("Authorize received")
                                self.charge_points[charge_point_id].authorize()

                            elif cmd_id == AcpwCommandId.STOP_CHARGING:
                                logger.info("STOP_CHARGING ")
                                self.charge_points[charge_point_id].authorize()

                            elif cmd_id == AcpwCommandId.SET_CURRENT_LIMIT:
                                self.charge_points[charge_point_id].set_ocpp_current_limit(payload)

                            elif cmd_id == AcpwCommandId.UNLOCK:
                                pass
                            elif cmd_id == AcpwCommandId.PAUSE_CHARGE:
                                self.charge_points[charge_point_id].pause_charging()

                            elif cmd_id == AcpwCommandId.FAULTS:
                                self.charge_points[charge_point_id].query_status(cmd_id)

                            elif cmd_id == AcpwCommandId.LOG_DUMP:
                                pass
                            elif cmd_id == AcpwCommandId.TEMPERATURE:
                                pass
                            elif cmd_id == AcpwCommandId.OTA_START:
                                pass
                            elif cmd_id == AcpwCommandId.OTA_DATA:
                                pass
                            elif cmd_id == AcpwCommandId.PERIPHERAL_REQUEST:
                                pass
                            elif cmd_id == AcpwCommandId.PROXIMITY_STATE:
                                self.charge_points[charge_point_id].query_status(cmd_id)

                            elif cmd_id == AcpwCommandId.MODE_SELECT:
                                pass
                            elif cmd_id == AcpwCommandId.HMI_BOARD_ERR:
                                pass
                            elif cmd_id == AcpwCommandId.REBOOT:
                                pass
                            elif cmd_id == AcpwCommandId.MAX_CURRENT:
                                self.charge_points[charge_point_id].query_status(cmd_id)
                            elif cmd_id == AcpwCommandId.NUMBER_OF_PHASE:
                                self.charge_points[charge_point_id].query_status(cmd_id)

                            else:
                                # TODO send unknown command back as response.
                                pass
                        elif json_type == "AuthorizationResponse":
                            self.charge_points[charge_point_id].authorization_mode.receive_authorization_response(
                                AuthorizationResponse(json_object["idTagInfo"]["status"]), json_object["idTagInfo"]["idTag"])

                        elif json_type == "ReserveNow":
                            connector_id = int(json_object["connectorId"])
                            if connector_id in self.charge_points.keys():
                                self.mediator.send(message, self.zmq_message_handler, MessageTypes.RESERVATION_REQUEST)
                                self.charge_points[connector_id].make_reservation(json_object["expiryDate"],
                                                                                  json_object["idTag"],
                                                                                  json_object["reservationId"])
                            else:
                                logger.info("no such a chargepoint for reservation {}".format(connector_id))

                        elif json_type == "CancelReservation":
                            reservation_id = json_object["reservationId"]
                            for charge_point in self.charge_points.values():
                                if charge_point.reservation.reservation_status == Status.ENABLED:
                                    self.mediator.send(message, self.zmq_message_handler,
                                                       MessageTypes.RESERVATION_REQUEST)
                                    charge_point.cancel_reservation(reservation_id)

                        elif json_type == "ocppOffline":
                            self.is_ocpp_offline_enabled = json_object["status"]
                            if self.is_ocpp_offline_enabled and self.status == ChargeStationStatus.WAITING_FOR_CONNECTION:
                                self.status = ChargeStationStatus.NORMAL
                            elif not self.is_ocpp_offline_enabled and not self.ocpp_connected and self.initialized:
                                self.status = ChargeStationStatus.WAITING_FOR_CONNECTION

                        elif json_type == "UnlockConnector":
                            connector_id = json_object["connectorId"]
                            if connector_id in self.charge_points:
                                self.charge_points[connector_id].stop_charging()

                        elif json_type == "ChangeAvailability":
                            connector_id = int(json_object["connectorId"])
                            self.charge_points[connector_id].availability = ChargePointAvailability(
                                json_object["status"])

                        elif json_type == "GeneralStatus":
                            if self.charge_points is not None:
                                for charge_point in self.charge_points.values():
                                    self.report_status()
                                    charge_point.report_status()
                                    
                        elif json_type == "agentCommand":
                            cmd = json_object["data"]["command"]
                            if cmd == "factoryReset":
                                self.reset_factory_settings()
                            elif cmd == "hardReset":
                                self.reset_hard()
                            elif cmd == "softReset":
                                self.reset_soft()
                            elif cmd == "firmwareUpdate":
                                self.update_firmware(json_object)
                            else:
                                logger.info("undefined agent command")
                                
                        elif json_type == "configurationComplete":
                            self.stop_master_configuration()
                            self.finish_master_configuration()
                            self.status = ChargeStationStatus.NORMAL
                            
                        elif json_type == "ecoCharge":
                            logger.info(json_object)
                            status = json_object["status"]
                            start_time = 0
                            stop_time = 0
                            if status == "Enabled":
                                start_time = json_object["startTime"]
                                stop_time = json_object["stopTime"]
                            self.update_eco_charge(status, start_time, stop_time)

                        elif json_type == "delayCharge":
                            status = json_object["status"]
                            delay_time = 0
                            if status == "Enabled":
                                delay_time = json_object["delayTime"]
                            self.update_delay_charge(status, delay_time)

                        elif json_type == "firmwareUpdate":
                            self.ota_manager.start_ota(OtaType.OCPP, json_object)
                            
                        elif json_type == "acpwVersionRequest":
                            msg = {'type': "acpwVersionResponse", 'value': ""}
                            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                            cursor = conn.cursor()
                            query = "SELECT acpwVersion FROM deviceDetails WHERE ID=1 "
                            cursor.execute(query)
                            records = cursor.fetchone()
                            conn.close()
                            if records is not None and records[0] is not None:
                                msg['value'] = records[0]
                                msg = json.dumps(msg)
                                logger.info(msg)
                                self.mediator.send(msg, self, MessageTypes.OCPP)
                                
                        elif json_type == "serialRequest":
                            msg = {'type': "serialResponse", 'value': ""}
                            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                            cursor = conn.cursor()
                            query = "SELECT acpwSerialNumber FROM deviceDetails WHERE ID=1 "
                            cursor.execute(query)
                            records = cursor.fetchone()
                            conn.close()
                            if records is not None and records[0] is not None:
                                msg['value'] = records[0]
                                msg = json.dumps(msg)
                                logger.info(msg)
                                self.mediator.send(msg, self, MessageTypes.OCPP)
                                
                        elif json_type == "cellularRequest":
                            msg = {'type': "cellularResponse", 'value': {}}
                            msg['value']['IMEI'] = ""
                            msg['value']['IMSI'] = ""
                            msg['value']['ICCID'] = ""
                            conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                            cursor = conn.cursor()
                            query = "SELECT imei ,imsi ,iccid FROM hmiDetails WHERE ID=1 "
                            cursor.execute(query)
                            records = cursor.fetchone()
                            conn.close()
                            if records is not None and records[0] is not None and records[1] is not None and records[2] is not None:
                                msg['value']['IMEI'] = records[0]
                                msg['value']['IMSI'] = records[1]
                                msg['value']['ICCID'] = records[2]
                                msg = json.dumps(msg)
                                logger.info(msg)
                                self.mediator.send(msg, self, MessageTypes.OCPP)
                                
                        elif json_type == "ocppConnected":
                            self.ocpp_connected = True
                            if self.initialized and self.status == ChargeStationStatus.WAITING_FOR_CONNECTION:
                                self.status = ChargeStationStatus.NORMAL
                        elif json_type == "ocppDisconnected":
                            self.ocpp_connected = False
                            if self.initialized and not self.is_ocpp_offline_enabled and self.status == ChargeStationStatus.NORMAL:
                                self.status = ChargeStationStatus.WAITING_FOR_CONNECTION

                            if self.configuration_manager.is_cellular_enabled():
                                self.configuration_manager.reset_quectel_modem()

                        elif json_type == "failsafeCurrent":
                            self.charge_points[charge_point_id].failsafe_current = json_object['data']['value']

                        elif json_type == "failsafeTimeout":
                            self.charge_points[charge_point_id].failsafe_timeout = json_object['data']['value']

                        elif json_type == "modbusTcpCurrent":
                            value = json_object['data']['value']
                            modbustcp_current_command = SetModbusTcpCurrentCommand(self, value)
                            modbustcp_current_command.execute()
                        
                        else:
                            logger.info("Unknown request")

                        # if cmd is not None:
                        #     self.mediator.send(cmd, self, "acpw")
                    # elif (jsonObject["type"] == "rfidAuthentication"):
                    #     sendToDealers(msg)
                except:
                    logger.info("Malformed message: {0}".format(traceback.format_exc()))

            time.sleep(0.1)

    def update_eco_charge(self, status, start_time, stop_time):

        if status == "Enabled":
            logger.info("ECO charge enabled")
            self.eco_charge_start_time = start_time
            self.eco_charge_stop_time = stop_time
            self.eco_charge_status = Status.ENABLED

        else:
            logger.info("ECO charge disabled")
            self.eco_charge_event.set()
            self.eco_charge_status = Status.DISABLED

    def in_eco_charge_interval(self):
        current_time = datetime.datetime.now().strftime("%H:%M:%S")

        # Stop charging when eco time interval just ends and lock the connector
        if current_time == self.eco_charge_stop_time + ":00" and \
                self.charge_points[1].current_charge_session is not None:
            logger.info("stopping eco charge")
            self.charge_points[1].eco_charge_completed = True
            self.charge_points[1].stop_charging(False)
            time.sleep(6)
            logger.info("locking connector")
            self.charge_points[1].interlock_control(True)

        if self.eco_charge_start_time > self.eco_charge_stop_time:
            if self.eco_charge_start_time + ":00" <= current_time <= "23:59:59":
                return True
            elif "00:00:00" <= current_time < self.eco_charge_stop_time:
                return True
            return False
        else:
            if self.eco_charge_start_time + ":00" <= current_time < self.eco_charge_stop_time + ":00":
                return True
            return False

    def _eco_charge_control(self):
        logger.info("Eco time control started")
        self.eco_charge_event.clear()

        while not self.eco_charge_event.isSet():
            self.eco_charge_event.wait(1.0)
            in_eco_charge_interval = self.in_eco_charge_interval()
            logger.debug("eco charge interval= {}".format(in_eco_charge_interval))
            logger.debug("eco auth uid= {}".format(self.charge_points[1].authorization_mode.current_authorization_uid))
            logger.debug("eco forced charge = {}".format(self.charge_points[1].immediate_charge))
           
            session_control = False
            if self.charge_points[1].current_charge_session is None:
                session_control = True
            else:
                if self.charge_points[1].current_charge_session.status == ChargeSessionStatus.PAUSED:
                    session_control = True
                    
            if self.charge_points[1].authorization_status == AuthorizationStatus.START \
                    and (session_control is True or self.charge_points[1].stop_requested) \
                    and (
                    self.charge_points[1].control_pilot_state == ControlPilotStates.B1
                    or self.charge_points[1].control_pilot_state == ControlPilotStates.C1):
                if in_eco_charge_interval:
                    logger.info("starting for eco charge")
                    self.charge_points[1].start_charging()

        self.eco_charge_status = Status.DISABLED

    def update_delay_charge(self, status, delay_time):
        logger.info("Receive delay charge update")
        if status == "Enabled":
            self.delay_charge_time = delay_time * 60
            self.delay_charge_start_time = \
                int(datetime.datetime.now().timestamp()) + self.delay_charge_time
            self._delay_charge_remaining_time = \
                self.delay_charge_start_time - int(datetime.datetime.now().timestamp())
            self.delay_charge_status = Status.ENABLED
            logger.info("Receive delay charge update 1")
        else:
            logger.info("Receive delay charge update 2")
            self.disable_delay_charge()

    def disable_delay_charge(self):
        self.charge_points[1].clear_authorization()
        self.delay_charge_event.set()

    def _delay_charge_control(self):
        logger.info("Start delay charge controller")
        self.delay_charge_event.clear()

        while (not self.delay_charge_event.isSet()) \
                and self.delay_charge_remaining_time > 0 \
                and self.charge_points[1].status != ChargePointStatus.CHARGING:
            self.delay_charge_event.wait(1.0)
            self.delay_charge_remaining_time -= 1

        if not self.delay_charge_event.isSet() \
                and self.charge_points[1].status != ChargePointStatus.CHARGING:
            logger.info("Authorizing for delay charge")
            self.charge_points[1].start_charging()
        else:
            logger.info("Canceled delay charge Control")

        self._delay_charge_remaining_time = 0
        self.delay_charge_start_time = 0
        self.delay_charge_status = Status.DISABLED

    def get_configuration(self, message, message_type):

        if message_type == MessageTypes.AUTHORIZATION_TYPE:
            if message is not None:
                self.set_authorization(message)

        elif message_type == MessageTypes.METER_TYPE:
            meterType = message['data']['meterType']

        else:
            logger.info("undefined configuration received")

    def _create_rfid_local_list(self, json_obj):
        rfid_local_list = []
        for list_item in json_obj["data"]["list"]:
            try:
                rfid_local_list.append(list_item.lower())
            except:
                logger.info("Rfid local list construct issue {0}".format(traceback.format_exc()))
                return []

        return rfid_local_list

    def reset_factory_settings(self):
        logger.info("*************FACTORY RESET STARTED********************")
        os.system("systemctl stop ocpp ui uid-reader midmeter")

        # TODO do this safely?
        os.system("rm -rf /var/lib/vestel")
        # TODO remove /var/log folder?

        list(self.charge_points.values())[0].reset_acpw()
        os.system("systemctl start ui")

        time.sleep(0.5)

        logger.info("***********reboot services for factory reset**********")
        os.system("systemctl start ocpp uid-reader midmeter")
        os.system("systemctl restart agent")

    def reset_hard(self):
        for charge_point in self.charge_points.values():
            charge_point.stop_charging()
        time.sleep(8)
        list(self.charge_points.values())[0].reboot_acpw()
        time.sleep(0.5)
        os.system("ifconfig wlan0 down")
        os.system("hciconfig hci0 down")
        os.system("reboot")

    def reset_soft(self):
        for charge_point in self.charge_points.values():
            charge_point.stop_charging()
        time.sleep(8)
        os.system("systemctl restart agent ui ocpp uid-reader midmeter")

    def update_firmware(self, json_object):
        self.ota_manager.start_ota(OtaType.WEBCONFIG, json_object)

    def factory_reset_listener(self):
        gpio_controller.export_gpio_pin(FACTORY_RESET_PIN)
        factoryTimer = 25

        while True:
            pinVal = gpio_controller.read_gpio_pin(FACTORY_RESET_PIN)
            if pinVal == 1:
                factoryTimer = 25
            else:
                if factoryTimer == 0:
                    self.reset_factory_settings()
                else:
                    factoryTimer = factoryTimer - 1
            time.sleep(0.5)

    @staticmethod
    def read_acpw_version():
        acpw_version = ''
        if os.path.exists(AGENT_DATABASE):
            connection = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
            if connection:
                cursor = connection.cursor()
                query = "SELECT acpwVersion FROM deviceDetails WHERE ID=1;"
                cursor.execute(query)
                acpw_version = cursor.fetchone()
                if acpw_version is not None:
                    acpw_version = acpw_version[0]
            else:
                logger.info("Database connection is failed!")
            connection.close()
        else:
            logger.info("Database file is not exists!")
        return acpw_version
    #
    # def getConfiguration(self, authorization, list):
    #     authorizationMode = None
    #     if authorization == "ocppList":
    #         authorizationMode = OcppAuthorization()
    #     elif authorization == "acceptAll":
    #         authorizationMode = AcceptAllAuthorization()
    #     elif authorization == "localList":
    #         authorizationMode = LocalAuthorization(list)
    #
    #     self.authorizationMode = authorizationMode


class Command(ABC):

    @abstractmethod
    def execute(self):
        pass


class StartChargingCommand(Command):

    def __init__(self, owner):
        self.owner = owner

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.START_CHARGING.value, bytearray([]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class StopChargingCommand(Command):

    def __init__(self, owner):
        self.owner = owner

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.STOP_CHARGING.value, bytearray([]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class PauseChargingCommand(Command):

    def __init__(self, owner):
        self.owner = owner

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.PAUSE_CHARGE.value, bytearray([]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class OtaCommand(Command):

    def __init__(self, owner, ota_command, payload=bytearray([])):
        self.owner = owner
        self.ota_command = ota_command
        self.payload = payload

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(self.ota_command.value, self.payload)
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class AuthorizationStartIndicatorCommand(Command):

    def __init__(self, owner):
        self.owner = owner

    def execute(self):
        # Start blinking for authorization
        cmd = AcpwMessageHandler.create_acpw_protocol_message(
            AcpwCommandId.PERIPHERAL_REQUEST.value, bytearray([PeripheralRequest.START_BLINK_AUTH.value]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)

        # Beep
        cmd = AcpwMessageHandler.create_acpw_protocol_message(
            AcpwCommandId.PERIPHERAL_REQUEST.value, bytearray([PeripheralRequest.THREE_BEEP.value]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class AuthorizationStopIndicatorCommand(Command):

    def __init__(self, owner):
        self.owner = owner

    def execute(self):
        # Stop blinking for authorization
        cmd = AcpwMessageHandler.create_acpw_protocol_message(
            AcpwCommandId.PERIPHERAL_REQUEST.value, bytearray([PeripheralRequest.STOP_BLINK_AUTH.value]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class AuthorizationFailIndicatorCommand(Command):

    def __init__(self, owner):
        self.owner = owner

    def execute(self):
        # Start blinking for invalid rfid card
        cmd = AcpwMessageHandler.create_acpw_protocol_message(
            AcpwCommandId.PERIPHERAL_REQUEST.value, bytearray([PeripheralRequest.INVALID_CARD_BLINK.value]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class CardRemovedIndicatorCommand(Command):

    def __init__(self, owner):
        self.owner = owner

    def execute(self):
        # Start blinking for card removal
        cmd = AcpwMessageHandler.create_acpw_protocol_message(
            AcpwCommandId.PERIPHERAL_REQUEST.value, bytearray([PeripheralRequest.TWO_RED_BLINK.value]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class CardAddedIndicatorCommand(Command):

    def __init__(self, owner):
        self.owner = owner

    def execute(self):
        # Start blinking for card addition
        cmd = AcpwMessageHandler.create_acpw_protocol_message(
            AcpwCommandId.PERIPHERAL_REQUEST.value, bytearray([PeripheralRequest.TWO_GREEN_BLINK.value]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class AuthorizationFinishIndicatorCommand(Command):

    def __init__(self, owner, charge_session):
        self.owner = owner
        self.charge_session = charge_session

    def execute(self):
        # Stop blinking for authorization wait
        stop_blink_auth_wait = PeripheralCommand(
            self.owner, PeripheralRequest.STOP_BLINK_AUTH)
        stop_blink_auth_wait.execute()

        if self.charge_session is None:
            # Stop blinking for auth pluging
            stop_blink_auth = PeripheralCommand(
                self.owner, PeripheralRequest.STOP_AUTH_WAIT_PLUG)
            stop_blink_auth.execute()

        # long beep
        long_beep = GenericCommand(
            self.owner, AcpwCommandId.PERIPHERAL_REQUEST, PeripheralRequest.LONG_BEEP)
        long_beep.execute()


class QueryStatusCommand(Command):

    def __init__(self, owner, commandId):
        self.owner = owner
        self.command_id = commandId

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(self.command_id.value, bytearray([]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class GenericCommand(Command):

    def __init__(self, owner, commandId, payload=None):
        self.owner = owner
        self.command_id = commandId
        if payload is not None:
            self.payload = bytearray([payload.value])
        else:
            self.payload = bytearray([])

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(self.command_id.value, self.payload)
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class SetOcppCurrentLimitCommand(Command):

    def __init__(self, owner, payload=None):
        self.owner = owner
        if payload is not None:
            self.payload = bytearray([payload])
        else:
            self.payload = bytearray([])

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.SET_CURRENT_LIMIT.value, self.payload)
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class SetAppCurrentLimitCommand(Command):

    def __init__(self, owner, payload=None):
        self.owner = owner
        if payload is not None:
            self.payload = bytearray([payload])
        else:
            self.payload = bytearray([])

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.APP_AVAILABLE_CURRENT.value, self.payload)
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)
        time.sleep(0.2)
        # query app available current for db update
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.APP_AVAILABLE_CURRENT.value, bytearray([]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class SetLockableCableCommand(Command):

    def __init__(self, owner, payload=None):
        self.owner = owner
        if payload is not None:
            self.payload = bytearray([payload])
        else:
            self.payload = bytearray([])

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.LOCKABLE_CABLE.value, self.payload)
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)
        time.sleep(0.2)
        # query lockable cable status for db update
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.LOCKABLE_CABLE.value, bytearray([]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class SetPowerOptimizerCommand(Command):

    def __init__(self, owner, payload=None):
        self.owner = owner
        if payload is not None:
            self.payload = bytearray([payload])
        else:
            self.payload = bytearray([])

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.APP_CPHOME_CURRENT.value, self.payload)
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)
        time.sleep(0.2)
        # query lockable cable status for db update
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.APP_CPHOME_CURRENT.value, bytearray([]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class SetModbusTcpCurrentCommand(Command):

    def __init__(self, owner, payload=None):
        self.owner = owner
        if payload is not None:
            self.payload = bytearray([payload])
        else:
            self.payload = bytearray([])

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.SET_MODBUSTCP_CURRENT.value, self.payload)
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)
        time.sleep(0.2)
        # query lockable cable status for db update
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.SET_MODBUSTCP_CURRENT.value, bytearray([]))
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class PeripheralCommand(Command):

    def __init__(self, owner, payload=None):
        self.owner = owner
        if payload is not None:
            self.payload = bytearray([payload.value])
        else:
            self.payload = bytearray([])

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.PERIPHERAL_REQUEST.value, self.payload)
        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class SwitchOperationModeCommand(Command):

    def __init__(self, owner, auto_start):
        self.owner = owner
        self.auto_start = auto_start

    def execute(self):
        if self.auto_start is True:
            cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.MODE_SELECT.value, bytearray([0]))
        else:
            cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.MODE_SELECT.value, bytearray([1]))

        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class HmiErrorCommand(Command):

    def __init__(self, charge_station, value):
        self.charge_station = charge_station
        self.value = value

    def execute(self):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.HMI_BOARD_ERR.value,
                                                              bytearray([self.value]))
        if cmd is not None:
            self.charge_station.mediator.send(cmd, self.charge_station, MessageTypes.ACPW)


class InterlockCommand(Command):

    def __init__(self, owner, lock):
        self.owner = owner
        self.lock = lock

    def execute(self):
        if self.lock is True:
            cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.INTERLOCK.value, bytearray([1]))
        else:
            cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.INTERLOCK.value, bytearray([0]))

        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class ChangeAvailabilityCommand(Command):
    def __init__(self, owner, isAvailable):
        self.owner = owner
        self.isAvailable = isAvailable

    def execute(self):
        if self.isAvailable == 1:
            cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.CHANGE_AVAILABILITY.value, bytearray([1]))
        else:
            cmd = AcpwMessageHandler.create_acpw_protocol_message(AcpwCommandId.CHANGE_AVAILABILITY.value, bytearray([0]))

        self.owner.mediator.send(cmd, self.owner, MessageTypes.ACPW)


class ZmqMessageHandler(Requester):

    def __init__(self):
        super().__init__()
        self.broker = None
        self.dealer_queue = queue.Queue()
        self.zmq_router_thread = None
        self.zmq_send_thread = None
        self.web_config_listen_thread = None

    def join(self):
        self.zmq_router_thread.join()
        self.zmq_send_thread.join()
        self.web_config_listen_thread.join()

    def start(self):
        self.zmq_router_thread = threading.Thread(target=self._zmqReceiver, daemon=True)
        self.zmq_router_thread.start()
        time.sleep(1)
        self.zmq_send_thread = threading.Thread(target=self._zmq_sender, daemon=True)
        self.zmq_send_thread.start()
        self.web_config_listen_thread = threading.Thread(target=self._web_config_listen, daemon=True)
        self.web_config_listen_thread.start()

    def _web_config_listen(self, context=None):

        context = context or zmq.Context.instance()
        subscriber = context.socket(zmq.SUB)
        subscriber.connect("ipc:///var/lib/webconfig.ipc")
        subscriber.setsockopt(zmq.SUBSCRIBE, b"")

        while True:
            message = subscriber.recv()
            try:
                message = message.decode("utf-8")
                logger.info("webconfig update %s" % message)
                json_message = json.loads(message)
                if json_message['type'] == "agentCommand":
                    self.mediator.send(message, self, MessageTypes.COMMAND)
                else:
                    self.mediator.send(message, self, MessageTypes.CONFIGURATION_UPDATE)
                # func = self.settingsUpdateChecker.get(x['type'], None)
                # if func is not None:
                #     logger.info("webConfig update {0}".format(x['type']))
                #     jsonObj = self.getJsonObjFromFile(x['data']['filePath'])
                #     func(jsonObj)
            except:
                logger.info("webconfig receive parse error: {0}".format(traceback.format_exc()))

            time.sleep(0.5)

    def _zmqReceiver(self, context=None):
        context = context or zmq.Context.instance()
        self.broker = context.socket(zmq.ROUTER)
        self.broker.bind("ipc:///var/lib/routing.ipc")

        while True:
            try:
                identity = self.broker.recv_string(flags=zmq.NOBLOCK)
                msg = self.broker.recv_string(flags=zmq.NOBLOCK)
                logger.info("Zmq message from {0}: {1}".format(identity, msg))
            except:
                time.sleep(0.05)
                continue
            
            try:
                if identity == "midMeter":
                    self.mediator.send(msg, self, MessageTypes.EXTERNAL_METER)
                elif identity == "OCPP1.6":
                    self.mediator.send(msg, self, MessageTypes.OCPP)
                elif identity == "rest":
                    self.mediator.send(msg, self, MessageTypes.REST)
                else:
                    self.mediator.send(msg, self, MessageTypes.DEALER)
            except:
                logger.info("Router receive parse error: {0}".format(traceback.format_exc()))

    def send_to_socket(self, data, destination=None):
        self.dealer_queue.put({"data": data, "destination": destination})

    def _zmq_sender(self):
        while True:
            if not self.dealer_queue.empty():
                value_dict = self.dealer_queue.get()
                destination = value_dict["destination"]
                if destination is not None:
                    self.broker.send_string(destination.value, flags=zmq.SNDMORE)
                    self.broker.send_string(value_dict['data'])
                else:
                    for dealer in Dealer:
                        self.broker.send_string(dealer.value, flags=zmq.SNDMORE)
                        self.broker.send_string(value_dict['data'])
                # send to dealers
                # for x in dealerList:
                #     broker.send_string(x, flags=zmq.SNDMORE)
                #     broker.send_string(data)
                # broker.send_multipart([b'UI', b'ACK'])
            time.sleep(0.01)


class Configurator(Requester):
    pass


class Meter(Requester):
    def __init__(self, command_list=None):
        self.command_list = command_list
        super().__init__()

    def start_query(self):
        pass


class InternalMeter(Meter):
    def __init__(self, command_list=None):
        command_list = command_list or \
                       [
                           AcpwCommandId.ENERGY.value,
                           AcpwCommandId.POWER.value,
                           AcpwCommandId.CURRENT.value,
                           AcpwCommandId.VOLTAGE.value
                       ]
        super().__init__(command_list)

    def _query_metrics(self):
        while True:
            for command in self.command_list:
                self._get_metric(command, bytearray([]))
            time.sleep(20)

    def _get_metric(self, command, payload):
        cmd = AcpwMessageHandler.create_acpw_protocol_message(command, payload)
        if cmd is not None:
            self.mediator.send(cmd, self, MessageTypes.ACPW)
            # sendToAcpw(cmd)

    def start_query(self):
        query_thread = threading.Thread(target=self._query_metrics, daemon=True)
        query_thread.start()


class MidMeter(Meter):
    def __init__(self, commandList=None):
        super().__init__(commandList)


class AcpwMessageHandler(Requester):
    message_id = c_ubyte(1)
    crc_table = []
    start_byte = 0xDE
    stop_byte = 0xAD
    serial_reset_time = 120.0  # Seconds

    def __init__(self, serial_port=None):

        self.serial_port = serial_port or serial.Serial()
        self.serial_outgoing_queue = queue.Queue()
        self.serial_incoming_queue = queue.Queue()
        self.serial_event = threading.Event()
        self.serial_sent_event = threading.Event()
        self.serial_timer_thread = threading.Thread(target=self._reset_serial, daemon=True)
        self.serial_sent_time = time.time()
        self._protocol_message_checker = {
            AcpwCommandId.ACK.value: self._ack_received,
            AcpwCommandId.NACK.value: self._nack_received,
            AcpwCommandId.PILOT_STATE.value: self._control_pilot_state_received,
            AcpwCommandId.VOLTAGE.value: self._voltage_received,
            AcpwCommandId.CURRENT.value: self._current_received,
            AcpwCommandId.ENERGY.value: self._total_energy_received,
            AcpwCommandId.POWER.value: self._active_power_received,
            # Command.START_CHARGING.value:   8,
            # Command.STOP_CHARGING.value:    9,
            # Command.SET_CURRENT_LIMIT.value:10,
            # Command.UNLOCK.value:           11,
            # Command.REBOOT.value:           12,
            AcpwCommandId.FAULTS.value: self._faults_received,
            AcpwCommandId.LOG_DUMP.value: self._log_dump_received,
            # Command.TEMPERATURE.value:      15,
            AcpwCommandId.OTA_START.value: self._ota_start_received,
            AcpwCommandId.OTA_STATUS.value: self._ota_status_received,
            AcpwCommandId.OTA_DATA.value: self._fw_update_result_received,
            # Command.PERIPHERAL_REQUEST.value: 19,
            AcpwCommandId.PROXIMITY_STATE.value: self._proximity_pilot_state_received,
            AcpwCommandId.MAX_CURRENT.value: self._max_current_received,
            AcpwCommandId.VERSION.value: self._version_received,
            AcpwCommandId.SERIAL_NUMBER.value: self._serialnumber_received,
            AcpwCommandId.EXTERNAL_CHARGE.value: self._external_charge_received,
            AcpwCommandId.MIN_CURRENT.value: self._min_current_received,
            AcpwCommandId.APP_AVAILABLE_CURRENT.value: self._app_available_current_received,
            AcpwCommandId.DEVICE_CPHOME_CURRENT.value: self._device_cphome_current_received,
            AcpwCommandId.APP_CPHOME_CURRENT.value: self._app_cphome_received,
            AcpwCommandId.LOCKABLE_CABLE.value: self._lockable_cable_received,
            AcpwCommandId.PEAK_OFFPEAK_INFO.value: self._peak_offpeak_received,
            AcpwCommandId.CURRENT_OFFERED_TO_EV.value: self._current_offered_to_ev_received,
            AcpwCommandId.NUMBER_OF_PHASE.value: self._number_of_phase_received,
            AcpwCommandId.PROXIMITY_PILOT_CURRENT.value: self._proximity_pilot_current_received,
            AcpwCommandId.SET_MODBUSTCP_CURRENT.value: self._modbustcp_current_received
        }

        AcpwMessageHandler.crc_table = self.create_crc_table()
        super().__init__(self)
        self.serial_timer_thread.start()

    @staticmethod
    def create_acpw_protocol_message(command, data):
        try:
            message_id = AcpwMessageHandler.generate_message_id()
            message = bytearray([message_id, 0, command])
            if len(data) > 0:
                message.extend(data)
            message_size = (len(message) + 4).to_bytes(2, byteorder="big")  # plus 4 - crc and message size itself
            message.insert(0, message_size[0])
            message.insert(1, message_size[1])
            crc = AcpwMessageHandler.calculate_crc(message)
            crc_bytes = crc.to_bytes(2, byteorder="big")
            message.insert(len(message), int(hex(crc_bytes[0]), 16))
            message.insert(len(message), crc_bytes[1])
            message.insert(ByteIndex.START.value, AcpwMessageHandler.start_byte)
            message.insert(len(message), AcpwMessageHandler.stop_byte)
            return message
        except:
            logger.info("Malformed ACPW message create data {0}".format(traceback.format_exc()))
            return None

    @staticmethod
    def generate_message_id():
        AcpwMessageHandler.message_id.value += 1
        return AcpwMessageHandler.message_id.value

    def _ack_received(self, data):
        pass
        # sendToDealers("ACK")

    def _nack_received(self, data):
        pass

    def _control_pilot_state_received(self, data):

        pilot_state = data[ByteIndex.PAYLOAD.value]
        # self.__checkPilotStateChange(pilotState)

        ps = {
            "type": "pilotState",
            "data": {
                "value": pilot_state
            }
        }

        msg = json.dumps(ps)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _voltage_received(self, data):

        voltage_p1 = int.from_bytes(
            data[ByteIndex.PAYLOAD.value:ByteIndex.PAYLOAD.value + 4],
            byteorder='big')
        voltage_p2 = int.from_bytes(
            data[ByteIndex.PAYLOAD.value + 4:ByteIndex.PAYLOAD.value + 8],
            byteorder='big')
        voltage_p3 = int.from_bytes(
            data[ByteIndex.PAYLOAD.value + 8:ByteIndex.PAYLOAD.value + 12],
            byteorder='big')

        voltage = {
            "type": "voltageEvent",
            "data": {
                "P1": voltage_p1, "P2": voltage_p2, "P3": voltage_p3
            }
        }

        msg = json.dumps(voltage)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _current_received(self, data):

        current_p1 = int.from_bytes(
            data[ByteIndex.PAYLOAD.value:ByteIndex.PAYLOAD.value + 4],
            byteorder='big')
        current_p2 = int.from_bytes(
            data[ByteIndex.PAYLOAD.value + 4:ByteIndex.PAYLOAD.value + 8],
            byteorder='big')
        current_p3 = int.from_bytes(
            data[ByteIndex.PAYLOAD.value + 8:ByteIndex.PAYLOAD.value + 12],
            byteorder='big')

        current = {
            "type": "currentEvent",
            "data": {
                "P1": current_p1, "P2": current_p2, "P3": current_p3
            }
        }

        msg = json.dumps(current)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _total_energy_received(self, data):

        total_energy = int.from_bytes(
            data[ByteIndex.PAYLOAD.value:ByteIndex.PAYLOAD.value + 8],
            byteorder='big')
        energy = {
            "type": "totalEnergyEvent",
            "data": {
                "P1": total_energy,
                "P2": 0,
                "P3": 0
            }
        }

        msg = json.dumps(energy)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _active_power_received(self, data):

        active_power_p1 = int.from_bytes(
            data[ByteIndex.PAYLOAD.value:ByteIndex.PAYLOAD.value + 4],
            byteorder='big')
        active_power_p2 = int.from_bytes(
            data[ByteIndex.PAYLOAD.value + 4:ByteIndex.PAYLOAD.value + 8],
            byteorder='big')
        active_power_p3 = int.from_bytes(
            data[ByteIndex.PAYLOAD.value + 8:ByteIndex.PAYLOAD.value + 12],
            byteorder='big')

        active_power = {
            "type": "activePowerEvent",
            "data": {
                "P1": active_power_p1, "P2": active_power_p2, "P3": active_power_p3
            }
        }

        msg = json.dumps(active_power)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _faults_received(self, data):

        fault = int.from_bytes(
            data[ByteIndex.PAYLOAD.value:ByteIndex.PAYLOAD.value + 4], byteorder='big')
        fault_json = {
            "type": "faultState",
            "data": {
                "value": fault
            }
        }

        msg = json.dumps(fault_json)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _fw_update_result_received(self, data):
        logger.info("fwUpdate result received")

    def _proximity_pilot_state_received(self, data):

        val = data[ByteIndex.PAYLOAD.value]
        proximity_state = {
            "type": "proximityState",
            "data": {
                "value": val
            }
        }

        msg = json.dumps(proximity_state)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _log_dump_received(self, data):
        pass

    def _ota_start_received(self, data):
        pass

    def _ota_status_received(self, data):
        received_ota_status = int.from_bytes(
            data[ByteIndex.PAYLOAD.value:ByteIndex.PAYLOAD.value + 1],
            byteorder='big')
        received_packet_id = int.from_bytes(
            data[ByteIndex.PAYLOAD.value + 1:ByteIndex.PAYLOAD.value + 2],
            byteorder='big')

        ota_status = {
            "type": "otaStatus",
            "data": {
                "value": received_ota_status,
                "packetId": received_packet_id
            }
        }
        msg = json.dumps(ota_status)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _max_current_received(self, data):
        val = data[ByteIndex.PAYLOAD.value]
        maxCurrent = {
            "type": "maximumCurrent",
            "data": {
                "value": val
            }
        }

        msg = json.dumps(maxCurrent)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _version_received(self, data):
        size = len(data)
        acpw_version = data[ByteIndex.PAYLOAD.value:size - 3]
        acpw_version = acpw_version.decode("utf-8")

        version = {
            "type": "acpwVersion",
            "data": {
                "value": acpw_version
            }
        }
        msg = json.dumps(version)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _serialnumber_received(self, data):

        size = len(data)
        serial_number = data[ByteIndex.PAYLOAD.value:size - 3]
        serial_number = serial_number.decode("utf-8")
        logger.info("Serial Number Received: %s" % serial_number)

        serial = {
            "type": "serialNumber",
            "data": {
                "value": serial_number
            }
        }
        msg = json.dumps(serial)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _external_charge_received(self, data):
        val = data[ByteIndex.PAYLOAD.value]
        external_charge = {
            "type": "externalCharge",
            "data": {
                "value": val
            }
        }

        msg = json.dumps(external_charge)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _min_current_received(self, data):
        val = data[ByteIndex.PAYLOAD.value]

        min_current = {
            "type": "minCurrent",
            "data": {
                "value": val
            }
        }

        msg = json.dumps(min_current)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _proximity_pilot_current_received(self, data):
        val = data[ByteIndex.PAYLOAD.value]

        proximity_pilot_current = {
            "type": "proximityPilotCurrent",
            "data": {
                "value": val
            }
        }

        msg = json.dumps(proximity_pilot_current)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _modbustcp_current_received(self, data):
        val = data[ByteIndex.PAYLOAD.value]

        modbustcp_current = {
            "type": "modbusTcpCurrent",
            "data": {
                "value": val
            }
        }

        msg = json.dumps(modbustcp_current)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _app_available_current_received(self, data):
        val = data[ByteIndex.PAYLOAD.value]
        available_current = {
            "type": "availableCurrent",
            "data": {
                "value": val
            }
        }

        msg = json.dumps(available_current)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _device_cphome_current_received(self, data):
        minimum = int.from_bytes(
            data[ByteIndex.PAYLOAD.value:ByteIndex.PAYLOAD.value + 1],
            byteorder='big')
        maximum = int.from_bytes(
            data[ByteIndex.PAYLOAD.value + 1:ByteIndex.PAYLOAD.value + 2],
            byteorder='big')

        power_optimizer_limits = {
            "type": "powerOptimizerLimits",
            "data": {
                "min": minimum,
                "max": maximum
            }
        }
        msg = json.dumps(power_optimizer_limits)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _app_cphome_received(self, data):
        val = data[ByteIndex.PAYLOAD.value]

        power_optimizer = {
            "type": "powerOptimizer",
            "data": {
                "value": val
            }
        }

        msg = json.dumps(power_optimizer)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)

    def _number_of_phase_received(self, data):
        val = data[ByteIndex.PAYLOAD.value]

        phase_type = {
            "type": "phaseType",
            "data": {
                "value": val
            }
        }

        msg = json.dumps(phase_type)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)
        
    def _lockable_cable_received(self, data):
        val = data[ByteIndex.PAYLOAD.value]
        lockable_cable = {
            "type": "lockableCable",
            "data": {
                "value": val
            }
        }

        msg = json.dumps(lockable_cable)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)
        
    def _peak_offpeak_received(self, data):
        pass
    
    def _current_offered_to_ev_received(self, data):
        current_offered = int.from_bytes(
            data[ByteIndex.PAYLOAD.value:ByteIndex.PAYLOAD.value + 1],
            byteorder='big')
        reason = int.from_bytes(
            data[ByteIndex.PAYLOAD.value + 1:ByteIndex.PAYLOAD.value + 2],
            byteorder='big')

        current_offered_msg = {
            "type": "currentOfferedEv",
            "data": {
                "value": {
                    "current": current_offered,
                    "reason": reason
                }
            }
        }
        msg = json.dumps(current_offered_msg)
        logger.info(msg)
        self.mediator.send(msg, self, MessageTypes.ACPW)
        
    def start(self):
        acpw_read_thread = threading.Thread(target=self._serial_read, args=("/dev/ttyS1", 9600), daemon=True)
        acpw_read_thread.start()

        acpw_send_thread = threading.Thread(target=self._serial_write, daemon=True)
        acpw_send_thread.start()

        acpw_parse_thread = threading.Thread(target=self._parse_acpw_message, daemon=True)
        acpw_parse_thread.start()

    def _serial_read(self, portName, baudRate):
        try:
            self.serial_port = serial.Serial(portName, baudRate)
            self.serial_event.clear()
        except:
            logger.info("Cannot open acpw serial")
            return
        while not self.serial_event.isSet():
            try:
                if self.serial_port.inWaiting() > 0:
                    self.serial_sent_event.clear()
                    logger.debug("Got raw serial")
                    in_waiting = self.serial_port.inWaiting()
                    received_data = self.serial_port.read(in_waiting)
                    time.sleep(0.1)
                    # check for remaining byte
                    remaining = self.serial_port.read(self.serial_port.inWaiting())
                    if len(remaining) > 0:
                        received_data += remaining
                    self.serial_incoming_queue.put(received_data)
            except:
                logger.info("ACPW serial port read error {0}".format(traceback.format_exc()))
            time.sleep(0.1)

    def _serial_write(self):
        while True:
            try:
                if not self.serial_outgoing_queue.empty() and self.serial_port.isOpen():
                    data = self.serial_outgoing_queue.get()
                    # TODO check for ACK
                    self.serial_port.write(data)
                    if not self.serial_sent_event.isSet():
                        self.serial_sent_time = time.time()
                    self.serial_sent_event.set()
                    logger.info("Sent {0} to ACPW, payload {1}".format(
                        AcpwCommandId(data[ByteIndex.COMMAND_ID.value]).name, data[ByteIndex.PAYLOAD.value])
                    )
                    if DEBUG:
                        logger.debug("Raw data:")
                        for b in data:
                            logger.debug(hex(b))
                        print()
            except:
                logger.info("ACPW serial port send error {0}".format(traceback.format_exc()))

            time.sleep(0.1)

    def _reset_serial(self):
        while True:
            if time.time() - self.serial_sent_time > AcpwMessageHandler.serial_reset_time and self.serial_sent_event.isSet():
                logger.info("resetting serial port")
                self.serial_event.set()
                self.serial_sent_event.clear()
                self.serial_port.close()
                logger.info("closed serial port")
                time.sleep(0.1)
                acpw_read_thread = threading.Thread(target=self._serial_read, args=("/dev/ttyS1", 9600), daemon=True)
                acpw_read_thread.start()
                logger.info("opened new serial port")
            time.sleep(1)

    def _parse_acpw_message(self):
        while True:
            try:
                if not self.serial_incoming_queue.empty():
                    data = self.serial_incoming_queue.get()
                    fragments = self._split_acpw_message(data)
                    if DEBUG:
                        logger.debug("Received messages: ")
                        logger.debug("----------------")
                        for val in fragments:
                            for b in val:
                                logger.debug(hex(b), end=" ")
                            print()
                            logger.debug("----------------")

                    for val in fragments:
                        if self._check_acpw_message_integrity(data):
                            logger.debug("Serial incoming msg is valid")
                            command = val[ByteIndex.COMMAND_ID.value]
                            logger.debug("Serial incoming command id %d" % command)
                            acpw_command = None
                            try:
                                acpw_command = AcpwCommandId(command)
                            except:
                                logger.info("Undefined command received from acpw")
                                continue
                            
                            logger.info("Received: {0}".format(acpw_command.name))
                            func = self._get_command_func(command)
                            if func is not None:
                                try:
                                    func(val)
                                except:
                                    logger.info("Command data error from acpw {0}".format(traceback.format_exc()))
                            else:
                                logger.info("Undefined command received from acpw")
            except:
                logger.info("Unexpected content acpw")
                
            time.sleep(0.01)

    def _split_acpw_message(self, data):
        # TODO implement remaining bytes case
        fragment_list = []
        size = len(data)
        start_index = 0
        try:
            while True:
                if data[start_index] == 0xde:

                    try:
                        logger.debug("start index %d" % start_index)
                        logger.debug("size %d" % size)
                        message_size = int.from_bytes(
                            data[start_index + ByteIndex.MESSAGE_SIZE.value:start_index + 3],
                            byteorder='big')
                        logger.debug("message size %d" % message_size)
                        # logger.info(data[startIndex + messageSize])
                        if (size > start_index + message_size and
                                data[start_index + message_size + 1] == 0xad):
                            logger.debug("found")
                            # found valid message
                            fragment_list.append(
                                data[start_index:start_index + message_size + 2])

                            # for b in data[startIndex:startIndex + messageSize+2]:
                            #     logger.info(hex(b))
                            if size > start_index + message_size + 3:  # check if another message remaining
                                logger.debug("another message")
                                start_index = start_index + message_size + 2
                            else:
                                logger.debug("no more msg, break")
                                break
                        else: # Discard incomplete message and move the index
                            startIndex += 1

                    except:
                        logger.info("!!! incomplete message")
                        if DEBUG:
                            for b in data:
                                logger.debug(hex(b), end=" ")
                            print()
                            logger.debug("~~~~~~~~~~~~~~~~")
                        break  # TODO remaining
                else:
                    start_index += 1
                    logger.debug("splitAcpwMessage search  startIndex {0}".format(start_index))
                time.sleep(0.01)
        except:
            logger.info("splitAcpwMessage discard")

        return fragment_list

    def _check_acpw_message_integrity(self, data):
        logger.debug("checking message integrity")
        size = len(data)
        if self.calculate_crc(data[ByteIndex.MESSAGE_SIZE.value:size - 3]):
            return True
        return False

    def _get_command_func(self, commandId):
        func = self._protocol_message_checker.get(commandId, None)
        return func

    @staticmethod
    def create_crc_table():
        crc_poly = 0x1021
        crc_tabccitt = [0] * 256
        for i in range(256):
            crc = 0
            c = i << 8
            for j in range(8):
                if (crc ^ c) & 0x8000:
                    crc = (crc << 1) ^ crc_poly
                else:
                    crc = crc << 1
                c = c << 1
            crc_tabccitt[i] = crc
        return crc_tabccitt

    @staticmethod
    def calculate_crc(data):
        crc = 0xFFFF
        for b in data:
            short_c = 0x00ff & b
            tmp = ((crc >> 8) ^ short_c & 0x00ff)
            crc = ((crc << 8) ^ AcpwMessageHandler.crc_table[tmp & 0xff]) & 0xffff
        return crc

    def send_to_acpw(self, data):
        self.serial_outgoing_queue.put(data)


def get_peripheral_data():
    interfaces = ConfigurationManager.get_network_interfaces()
    if "wwan0" in interfaces:
        imei_cmd = 'echo -ne "at+gsn\r\n" | busybox microcom -t 100 /dev/ttyUSB3'
        imei = ""
        try:
            imei = subprocess.check_output(imei_cmd, stderr=subprocess.STDOUT, shell=True)
            imei = str(imei.decode("utf-8"))
            if imei.find('ERROR') != -1:
                imei = ""
            else:
                imei = imei.replace("at+gsn", "").replace("OK", "").replace("\r", "").replace("\n", "")
        except:
            logger.info("imei read error: {0}".format(traceback.format_exc()))

        imsi_cmd = 'echo -ne "at+cimi\r\n" | busybox microcom -t 100 /dev/ttyUSB3'
        imsi = ""
        try:
            imsi = subprocess.check_output(imsi_cmd, stderr=subprocess.STDOUT, shell=True)
            imsi = str(imsi.decode("utf-8"))
            if imsi.find('ERROR') != -1:
                imsi = ""
            else:
                imsi = imsi.replace("at+cimi", "").replace("OK", "").replace("\r", "").replace("\n", "")
        except:
            logger.info("imsi read error: {0}".format(traceback.format_exc()))

        iccid_cmd = 'echo -ne "at+qccid\r\n" | busybox microcom -t 100 /dev/ttyUSB3'
        iccid = ""
        try:
            iccid = subprocess.check_output(iccid_cmd, stderr=subprocess.STDOUT, shell=True)
            iccid = str(iccid.decode("utf-8"))
            if iccid.find('ERROR') != -1:
                iccid = ""
            else:
                iccid = iccid.replace("at+qccid", ""). \
                    replace("+QCCID: ", ""). \
                    replace("OK", "").replace("\r", "").replace("\n", "")
        except:
            logger.info("iccid read error: {0}".format(traceback.format_exc()))

        conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "INSERT INTO hmiDetails (ID, imei, imsi, iccid )" \
                "SELECT {0}, '{1}', '{2}', '{3}'" \
                "WHERE NOT EXISTS (SELECT 1 FROM hmiDetails WHERE ID={0});". \
            format(1, imei, imsi, iccid)
        cursor.execute(query)
        query = "UPDATE hmiDetails SET imei='{0}', imsi='{1}', iccid='{2}' WHERE ID=1;".format(imei, imsi, iccid)
        cursor.execute(query)
        conn.commit()
        conn.close()


def wifiExists():
    interfaces = getNetworkInterfaces()
    if 'wlan0' in interfaces:
        return True
    logger.info("board does not look have a wifi")
    return False


def getNetworkInterfaces():
    cmd = "ls /sys/class/net/"
    interfaceList = os.popen(cmd).read().split()
    return interfaceList


if __name__ == "__main__":
    cs = ChargeStation()
    cs.initialize()
