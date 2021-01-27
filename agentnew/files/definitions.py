from enum import Enum
from abc import ABC, abstractmethod
from ctypes import c_uint32, LittleEndianStructure, Union


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(
                Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ControlPilotStates(Enum):
    A1 = 0
    A2 = 1
    B1 = 2
    B2 = 3
    C1 = 4
    C2 = 5
    D1 = 6
    D2 = 7
    E = 8
    F = 9


class ProximityPilotStates(Enum):
    Plugged = 0
    NoCable = 1
    CableModel = 2


class Requester(metaclass=Singleton):

    def __init__(self, mediator=None):
        self.mediator = mediator


class Mediator(ABC):

    @abstractmethod
    def send(self, message, requester, target):
        pass


class MessageTypes(Enum):
    ACPW = 0
    RFID_UID = 1
    AUTHORIZATION_STATUS = 2
    AUTHORIZATION_RESPONSE = 3
    PERIPHERAL_ERROR = 4
    EXTERNAL_METER = 5
    DEALER = 6
    OCPP = 7
    AUTHORIZE = 8
    STATUS_NOTIFICATION = 9
    CHARGE_SESSION_STATUS = 10
    AUTHORIZATION_TYPE = 11
    METER_TYPE = 12
    CONFIGURATION_UPDATE = 13
    METER_VALUES = 14
    BLUETOOTH_MESSAGE = 15
    COMMAND = 16
    RESERVATION_REQUEST = 17
    RESERVATION_RESPONSE = 18
    CHARGE_POINT_AVAILABILITY = 19
    CONFIGURATION_COMPLETE = 20
    ECO_CHARGE = 21
    DELAY_CHARGE = 22
    CHARGE_STATION_STATUS = 23
    BLUETOOTH_STATUS = 24
    FIRMWARE_UPDATE_STATUS = 25
    REGISTRATION_FAIL = 26
    MASTER_ADDITION = 27
    CHARGE_CONTROL = 28
    RFID_CARD_CONFIGURATION = 29
    AVAILABLE_CURRENT = 30
    DISCONNECT_BLUETOOTH = 31
    LOCKABLE_CABLE = 32
    PROPERTY_CHANGE = 33
    POWER_OPTIMIZER = 34
    FREE_CHARGING = 35
    FIRMWARE_UPDATE_INITIALIZATION = 36
    REST = 37
    DLM = 38
    DLM_SLAVE_GROUP_CONFIG_PARAMETERS = 39
    DLM_INSTANT_CURRENT = 40
    DLM_SLAVE_PARAMETERS_REQUEST = 41
    DLM_SETTINGS_REQUEST = 42
    DLM_METERING_DATA = 43
    CONTINUE_AFTER_ECO_CHARGE = 44
    CONTINUE_AFTER_POWER_OFF = 45


class Dealer(Enum):
    __order__ = "OCPP UI BT"
    OCPP = "OCPP1.6"
    UI = "UI"
    BT = "BT_IF"
    MODBUSTCP = "MODBUSTCP"


class AuthorizationStatus(Enum):
    # SUCCESS = "Success"
    # FAIL = "Fail"
    TIMEOUT = "Timeout"
    START = "Start"
    FINISH = "Finish"


class AuthorizationResponse(Enum):
    ACCEPTED = "Accepted"
    BLOCKED = "Blocked"
    EXPIRED = "Expired"
    INVALID = "Invalid"
    CONCURRENT_TX = "ConcurrentTx"
    TIMEOUT = "Timeout"


class ChargeStationStatus(Enum):
    NORMAL = "Normal"
    INITIALIZING = "Initializing"
    ONBOARDING = "Onboarding"
    WAITING_FOR_CONFIGURATION = "WaitingForConfiguration"
    INSTALLING_FIRMWARE = "InstallingFirmware"
    WAITING_FOR_MASTER_ADDITION = "WaitingForMasterAddition"
    ADDED_USER_CARD = "AddedUserCard"
    REMOVED_USER_CARD = "RemovedUserCard"
    WAITING_FOR_CONNECTION = "WaitingForConnection"


class OcppConnectionStatus(Enum):
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"


class FirmwareUpdateStatus(Enum):
    INSTALLING = "Installing"
    INSTALLED = "Installed"
    INSTALLATION_FAILED = "InstallationFailed"


class ChargePointStatus(Enum):
    AVAILABLE = "Available"
    PREPARING = "Preparing"
    CHARGING = "Charging"
    SUSPENDED_EVSE = "SuspendedEVSE"
    SUSPENDED_EV = "SuspendedEV"
    FINISHING = "Finishing"
    RESERVED = "Reserved"
    UNAVAILABLE = "Unavailable"
    FAULTED = "Faulted"


class ChargeSessionStatus(Enum):
    STARTED = "Started"
    STOPPED = "Stopped"
    PAUSED = "Paused"
    SUSPENDED = "Suspended"


class ChargePointExtendedStatus(Enum):
    NONE = "None"
    DELAY_TIMER_ACTIVE = "DelayTimerActive"
    ECO_TIMER_ACTIVE = "EcoTimerActive"
    INITIALIZING = "Initializing"
    WAITING_FOR_CONNECTION = "WaitingConnection"
    # CONNECTED = "Connected"
    UPDATING_FIRMWARE = "UpdatingFirmware"
    UPDATED_FIRMWARE = "UpdatedFirmware"
    ONBOARDING = "Onboarding"
    AUTO_START = "AutoStart"
    WAITING_FOR_CONFIGURATION = "WaitingForConfiguration"


class CurrentOfferedToEvReason(Enum):
    NORMAL = 0
    USER_MAX_CURRENT = 1
    RESERVED = 2
    UNBALANCED_LOAD = 3
    TEMPERATURE = 4
    POWER_OPTIMIZER = 5
    LOAD_SHEDDING = 6
    OCPP_SMART_CHARGING = 7
    APP_AVAILABLE_CURRENT = 8
    DLM_AVAILABLE_CURRENT = 9
    CHARGING_CABLE_CAPACITY = 10
    
    
class ChargePointErrorCode(Enum):
    CONNECTOR_LOCK_FAILURE = "ConnectorLockFailure"
    EV_COMMUNICATION_ERROR = "EVCommunicationError"
    GROUND_FAILURE = "GroundFailure"
    HIGH_TEMPERATURE = "HighTemperature"
    INTERNAL_ERROR = "InternalError"
    LOCAL_LIST_CONFLICT = "LocalListConflict"
    NO_ERROR = "NoError"
    OTHER_ERROR = "OtherError"
    OVER_CURRENT_FAILURE = "OverCurrentFailure"
    POWER_METER_FAILURE = "PowerMeterFailure"
    POWER_SWITCH_FAILURE = "PowerSwitchFailure"
    READER_FAILURE = "ReaderFailure"
    RESET_FAILURE = "ResetFailure"
    UNDER_VOLTAGE = "UnderVoltage"
    OVER_VOLTAGE = "OverVoltage"
    WEAK_SIGNAL = "WeakSignal"


class ChargePointAvailability(Enum):
    INOPERATIVE = "Inoperative"
    OPERATIVE = "Operative"


class ByteIndex(Enum):
    START = 0
    MESSAGE_SIZE = 1
    MESSAGE_ID_SEND = 3
    MESSAGE_ID_RECEIVE = 4
    COMMAND_ID = 5
    PAYLOAD = 6


class AcpwCommandId(Enum):
    ACK = 1
    NACK = 2
    PILOT_STATE = 3
    VOLTAGE = 4
    CURRENT = 5
    ENERGY = 6
    POWER = 7
    START_CHARGING = 8
    STOP_CHARGING = 9
    SET_CURRENT_LIMIT = 10
    UNLOCK = 11
    PAUSE_CHARGE = 12
    FAULTS = 13
    LOG_DUMP = 14
    TEMPERATURE = 15
    OTA_START = 16
    OTA_STATUS = 17
    OTA_DATA = 18
    PERIPHERAL_REQUEST = 19
    PROXIMITY_STATE = 20
    MODE_SELECT = 21
    HMI_BOARD_ERR = 22
    REBOOT = 23
    MAX_CURRENT = 24
    RESET = 25
    VERSION = 26
    SERIAL_NUMBER = 27
    EXTERNAL_CHARGE = 28
    INTERLOCK = 29
    MIN_CURRENT = 30
    APP_AVAILABLE_CURRENT = 31
    DEVICE_CPHOME_CURRENT = 32
    APP_CPHOME_CURRENT = 33
    LOCKABLE_CABLE = 34
    PEAK_OFFPEAK_INFO = 35
    CURRENT_OFFERED_TO_EV = 36
    NUMBER_OF_PHASE = 37
    DLM_STATE_INFORMATION = 38
    DLM_ROLE_INFORMATION = 39
    DLM_METERING_DEVICE_SETTING = 40
    DLM_METERING_DATA_INFORMATION = 41
    DLM_MIN_MAX_STEP_INFORMATION = 42
    DLM_AVAILABLE_CURRENT = 43
    PO_BOARD_SOFTWARE_VERSION_NUMBER = 44
    SERVICE_INFORMATION = 45
    READY_ID_OF_STANDARD_TIC = 46
    CHANGE_AVAILABILITY = 47
    PROXIMITY_PILOT_CURRENT = 48
    SET_MODBUSTCP_CURRENT = 49


class PeripheralRequest(Enum):
    START_BLINK_AUTH = 0
    STOP_BLINK_AUTH = 1
    START_BLINK_REZ = 2
    STOP_BLINK_REZ = 3
    INVALID_CARD_BLINK = 4
    START_BLINK_FIRMWARE = 5
    STOP_BLINK_FIRMWARE = 6
    START_BLINK_ECO = 7
    STOP_BLINK_ECO = 8
    START_BLINK_DELAY = 9
    STOP_BLINK_DELAY = 10
    THREE_BEEP = 11
    START_AUTH_WAIT_PLUG = 12
    STOP_AUTH_WAIT_PLUG = 13
    LONG_BEEP = 14
    FACTORY_RESET_LED = 15
    CONFIG_MODE_START = 16
    CONFIG_MODE_STOP = 17
    TWO_GREEN_BLINK = 18
    TWO_RED_BLINK = 19
    RFID_CONFIG_MODE_START = 20
    RFID_CONFIG_MODE_STOP = 21
    TWO_SHORT_BEEP = 22
    TWO_LONG_BEEP = 23
    MASTER_SET_BEEP = 24


class ErrorBits(LittleEndianStructure):
    _fields_ = [
        ("e0", c_uint32, 1),
        ("e1", c_uint32, 1),
        ("e2", c_uint32, 1),
        ("e3", c_uint32, 1),
        ("e4", c_uint32, 1),
        ("e5", c_uint32, 1),
        ("e6", c_uint32, 1),
        ("e7", c_uint32, 1),
        ("e8", c_uint32, 1),
        ("e9", c_uint32, 1),
        ("e10", c_uint32, 1),
        ("e11", c_uint32, 1),
        ("e12", c_uint32, 1),
        ("e13", c_uint32, 1),
        ("e14", c_uint32, 1),
        ("e15", c_uint32, 1),
        ("e16", c_uint32, 1),
        ("e17", c_uint32, 1),
        ("e18", c_uint32, 1),
        ("e19", c_uint32, 1),
        ("e20", c_uint32, 1),
        ("e21", c_uint32, 1),
        ("e22", c_uint32, 1),
        ("e23", c_uint32, 1),
    ]


class ChargePointError(Union):
    _fields_ = [
        ("bit", ErrorBits),
        ("asInt", c_uint32)
    ]


class BluetoothInterfaceError(Exception):
    pass


class Status(Enum):
    ENABLED = "Enabled"
    DISABLED = "Disabled"


class MeterType(Enum):
    KLEFR_TRI_PHASE = "KlefrTri"
    KLEFR_MONO_PHASE = "KlefrMono"
    INTERNAL = "internal"


class OtaStatus(Enum):
    OSTREE = "Ostree"
    ACPW = "Acpw"


class OtaType(Enum):
    WEBCONFIG = 1
    CLOUD = 2
    OCPP = 3


class AcpwOtaStatus(Enum):
    NOT_READY = 0
    READY = 1
    TRANSFER_COMPLETE = 2
    FINISHED_SUCCESS = 3
    FINISHED_FAIL = 4


class Settings(Enum):
    TIMEZONE = "Timezone"
    LOCKABLE_CABLE = "LockableCable"
    AVAILABLE_CURRENT = "AvailableCurrent"
    FREE_CHARGING = "PlugAndCharge"
    WIFI = "WiFi"
    ETHERNET = "Ethernet"
    CELLULAR = "Cellular"
    POWER_OPTIMIZER = "PowerOptimizer"
    CONTINUE_AFTER_ECO_CHARGE = "ContinueAfterEcoCharge"
    CONTINUE_AFTER_POWER_OFF = "ContinueAfterPowerOff"
    

class PhaseType(Enum):
    MONO_PHASE = 0
    THREE_PHASE = 1