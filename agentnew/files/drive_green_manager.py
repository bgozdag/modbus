import time
import json
from threading import Thread, Lock
from definitions import MessageTypes, Requester, ChargePointStatus, AuthorizationStatus, AcpwCommandId
from configuration_manager import DefaultVfactory
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import AWSIoTPythonSDK.core.util.enums
import sqlite3
import os
from datetime import datetime
import subprocess
import hashlib
import base64
from xml.etree import ElementTree
import logging

VOLTAGE_DIFFERENCE = 10000
CURRENT_DIFFERENCE = 500

GENERAL_STATUS_COMMAND = "CHGSTT0"
PHASE_INFO_COMMAND = "CHPHINF"
ERRORS_LIST_COMMAND = "CHERLS0"
SESSION_TOTAL_INFO_COMMAND = "CHSTINF"
REQUEST_DATE_TIME_UPDATE_COMMAND = "CHRDTUP"
SESSION_CURRENT_INFO_COMMAND = "CHSCINF"
GENERAL_TOTAL_INFO_COMMAND = "CHGTINF"
CONTROL_COMMAND = "CHCONTR"
CURRENT_DATE_TIME_COMMAND = "CHCURDT"
CHARGE_WITH_DELAY_COMMAND = "CHWDELY"
ECO_TIME_CONTROL_COMMAND = "CHECOTC"

ROOT_CA_PATH = "/usr/lib/vestel/root-CA.crt"
CERTIFICATE_PATH = "/var/lib/vestel/EVC04-certificate.pem.crt"
PRIVATE_KEY_PATH = "/var/lib/vestel/EVC04-private.pem.key"
AGENT_DB_PATH = "/var/lib/vestel/agent.db"
SYSTEM_DB_PATH = "/usr/lib/vestel/system.db"
VFACTORY_DB_PATH = "/run/media/mmcblk1p3/vfactory.db"
SIGNATURE_CERTIFICATE_PATH = "/usr/lib/vestel/signatureCert.crt"

logger = logging.getLogger("EVC04_Agent.drive_green_manager")


class DriveGreenManager(Requester):
    def __init__(self):
        super().__init__()

        self.connection = False
        self.status = None
        self.job_status = None
        self.vendor_error_code = 0
        self.is_configured = False
        self.worker = None
        self.device_uuid = None
        self.server_url = None
        self.user_id = None
        self.endpoint = None
        self.port = None
        self.server_port = None
        self.access_token = None
        self.client = None
        self.customer = None
        self.mutex = Lock()
        self.connect_thread = None
        self.authorization_status = None
        self.last_voltage_p1 = 0
        self.last_voltage_p2 = 0
        self.last_voltage_p3 = 0
        self.last_current_p1 = 0
        self.last_current_p2 = 0
        self.last_current_p3 = 0
        self.active_power_p1 = 0
        self.active_power_p2 = 0
        self.active_power_p3 = 0
        self.voltage_p1 = 0
        self.voltage_p2 = 0
        self.voltage_p3 = 0
        self.current_p1 = 0
        self.current_p2 = 0
        self.current_p3 = 0
        self.initial_energy = 0
        self.total_energy = 0
        self.delay_charge_active = False
        self.eco_time_active = False
        self.charge_session_status = None
        self.charge_start_time = None
        self.get_job_thread = None
        self.initialize_status()
        self._start()

    def _start(self):
        self.connect_thread = Thread(target=self.initialize)
        self.connect_thread.start()

    def join(self):
        self.connect_thread.join()

    def initialize_status(self):
        conn = sqlite3.connect(AGENT_DB_PATH)
        cursor = conn.cursor()
        query = "SELECT status FROM chargePoints;"
        cursor.execute(query)
        row = cursor.fetchone()
        conn.close()
        if row is not None:
            self.status = row[0]

    def initialize(self):
        while True:
            self.mutex.acquire()
            connection = self.connection
            self.mutex.release()
            if connection is True:
                break
            self.mqtt_connect()
            time.sleep(10)

    def register_request(self, app_name, base_token, device_type, mac, soft_ver, model, feature_type,
                         device_name, config_date_time, device_features):
        import requests
        position = self.server_url.find("/")
        url = "https://" + self.server_url[:position] + \
            ":" + self.server_port + self.server_url[position:]
        internet_check = self.wait_for_internet_connection()
        if not internet_check:
            return "NoInternetConnection"
        randoma = {
            "cid": self.user_id,
            "token": base_token
        }

        headers = {"Content-Type": "application/json"}
        try:
            resp = requests.get(
                url=url + "/randoma", headers=headers, params=randoma, verify=ROOT_CA_PATH)
        except:
            return "NoServerConnection"
        resp = resp.json()
        if "status" in resp:
            logger.info(
                "++++++++++++++++++++++++++++++ randoma result:{}".format(resp["status"]))
            if resp["status"] == "SUCCESS":
                valid_token = resp['randomA']
                last_token = self.access_token + valid_token
                hashed_word = hashlib.sha256(
                    last_token.encode('ascii')).digest()
                content_sha256 = base64.b64encode(hashed_word)
                final_token = content_sha256.decode("utf-8", "ignore")
        elif "errors" in resp:
            logger.info("---------------------------------- ERROR on randoma:")
            for item in resp["errors"]:
                logger.info(str(item["code"]) + ": " + str(item["message"]))
            return "ServerError"

        register = {
            "deviceFeatures": device_features,
            "cid": self.user_id,
            "appName": app_name,
            "ip": mac,
            "type": device_type,
            "uuid": self.device_uuid,
            "mac": mac,
            "token": final_token,
            "featureType": feature_type,
            "deviceName": device_name,
            "deviceModel": model,
            "configTimeInEpoch": config_date_time,
            "swVersion": soft_ver
        }

        try:
            resp = requests.post(
                url=url + "/register", json=register, headers=headers, verify=ROOT_CA_PATH)
        except:
            return "NoServerConnection"
        resp = resp.json()
        if "errors" in resp:
            logger.info(
                "---------------------------------- ERROR on register:")
            for item in resp["errors"]:
                logger.info(str(item["code"]) + ": " + str(item["message"]))
            return "ServerError"
        else:
            logger.info(
                "++++++++++++++++++++++++++++++ register result: SUCCESS")
            cert = resp['cert']
            private = resp['private']
            self.endpoint = resp['endpoint']
            self.port = resp['port']

            out1 = open(CERTIFICATE_PATH, "w")
            out1.write(cert)
            out1.close()

            out2 = open(PRIVATE_KEY_PATH, "w")
            out2.write(private)
            out2.close()
            message = {
                "type": "configurationComplete"
            }
            message = json.dumps(message)
            self.mediator.send(
                message, self, MessageTypes.CONFIGURATION_COMPLETE)
            ok_msg = {
                "MessageType": "DriveGreenRegistrationResponse",
                "Status": "OK"
            }
            ok_msg = json.dumps(ok_msg)
            self.mediator.send(ok_msg, self, MessageTypes.BLUETOOTH_MESSAGE)
            self.write_configurations()
            try:
                if self.client is not None:
                    self.client.disconnect()
            except Exception as e:
                logger.info(e)
            self.mqtt_connect()
            return None

    def update_request(self):
        import requests
        position = self.server_url.find("/")
        url = "https://" + self.server_url[:position] + \
            ":" + self.server_port + self.server_url[position:]

        hashed_word = hashlib.sha256(
            self.access_token.encode('ascii')).digest()
        content_sha256 = base64.b64encode(hashed_word)
        base_token = content_sha256.decode("utf-8", "ignore")
        randomb = {
            "token": base_token
        }

        headers = {"Content-Type": "application/json"}
        resp = requests.get(url=url + "/{}/randomb".format(self.device_uuid),
                            headers=headers, params=randomb, verify=ROOT_CA_PATH)
        resp = resp.json()
        if "status" in resp:
            logger.info(
                "++++++++++++++++++++++++++++++ randomb result:{}".format(resp["status"]))
            if resp["status"] == "SUCCESS":
                valid_token = resp['randomB']
                last_token = self.access_token + valid_token
                hashed_word = hashlib.sha256(
                    last_token.encode('ascii')).digest()
                content_sha256 = base64.b64encode(hashed_word)
                final_token = content_sha256.decode("utf-8", "ignore")
        elif "errors" in resp:
            logger.info("---------------------------------- ERROR on randomb:")
            for item in resp["errors"]:
                logger.info(str(item["code"]) + ": " + str(item["message"]))
            return

        device_features = self.read_features()
        features_json = json.loads(device_features)
        soft_ver = features_json['DISPLSW']

        update = {
            "token": final_token,
            "deviceFeatures": device_features,
            "swVersion": soft_ver
        }
        resp = requests.post(url=url + "/{}/update".format(self.device_uuid),
                             json=update, headers=headers, verify=ROOT_CA_PATH)
        resp = resp.json()
        if "status" in resp:
            logger.info(
                "++++++++++++++++++++++++++++++ update result:{}".format(resp["status"]))
        elif "errors" in resp:
            logger.info("---------------------------------- ERROR on update:")
            for item in resp["errors"]:
                logger.info(str(item["code"]) + ": " + str(item["message"]))
            return

    def wait_for_internet_connection(self):
        i = 0
        while True:
            response = subprocess.getoutput("ping 1.1.1.1 -c 1")
            if response.endswith("Network is unreachable"):
                time.sleep(1)
                i += 1
                if i == 20:
                    logger.info("TIMEOUT")
                    return False
            elif response.endswith("100% packet loss"):
                time.sleep(1)
                i += 5
                if i == 20:
                    logger.info("TIMEOUT")
                    return False
            else:
                return True

    def set_timezone(self, timezone):
        os.system("timedatectl set-timezone {}".format(timezone))
        if self.get_timezone() == timezone:
            if self.client is not None:
                shadow_message = {
                    "state": {
                        "reported": {
                            "status": "connected",
                            "customerId": self.user_id,
                            "srv_url": self.server_url,
                            "config": {
                                "timezone": timezone
                            }
                        }
                    }
                }
                shadow_message = json.dumps(shadow_message)
                self.client.publishAsync("$aws/things/{}/shadow/update".format(self.device_uuid), shadow_message, 1,
                                         ackCallback=self.puback)
            logger.info("Timezone set: {}".format(timezone))

    def update_interfaces(self, connection_interface, wifi_ssid=None, wifi_password=None):
        try:
            connection_webconfig = sqlite3.connect(
                "/var/lib/vestel/webconfig.db")
            db = connection_webconfig.cursor()
            if connection_webconfig:
                if connection_interface == "Ethernet":
                    db.execute(
                        'UPDATE ethernetSettings SET enable="true", IPSetting="DHCP" WHERE id=1')

                elif connection_interface == "WiFi":
                    db.execute('UPDATE wifiSettings SET enable="true", ssid="{}", password="{}", securityType="WPA", '
                               'IPSetting="DHCP" WHERE id=1'.format(wifi_ssid, wifi_password))

            connection_webconfig.commit()
            connection_webconfig.close()

        except Exception as e:
            logger.info("update_interfaces error: " + e)

    def get_encrypted_mac(self):
        from Crypto.Cipher import AES
        key = b'\xd0u\x8f\xf2H1\xe0\xcf\xa2\x900s\t\xa4\xd5\x19\x92\x99\x8f\xc7\xa6\x8f\x997\xdc}Bi\xf6\xa7\x9c4'
        cipher = AES.new(key, AES.MODE_ECB)

        # hex_key = []
        # for i in range(0,len(key.hex()),2):
        #   hex_key.append(("0x" + key.hex()[i:i+2].upper()))
        # logger.info (', '.join(hex_key))

        eth1 = subprocess.getoutput("ls /sys/class/net | grep eth1")

        if not eth1:
            mac = subprocess.getoutput(
                "cat /sys/class/net/eth0/address | tr a-z A-Z")
        else:
            mac = subprocess.getoutput(
                "cat /sys/class/net/eth1/address | tr a-z A-Z")

        mac = mac.replace(":", "")

        array = []
        for i in range(0, len(mac), 2):
            array.append((int(mac[i:i + 2], 16)))

        array.append(0)
        array.append(0)

        array += array
        array = bytes(array)

        cipher_text = cipher.encrypt(array).hex()

        return cipher_text.upper()

    def verify_signature(self, data, signature):
        from OpenSSL import crypto

        f = open(SIGNATURE_CERTIFICATE_PATH)
        ss_buf = f.read()
        f.close()
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, ss_buf)
        signature_bytes = base64.decodebytes(signature.encode())

        try:
            crypto.verify(cert=cert, signature=signature_bytes, data=data, digest='sha256')
            logger.info("Verified Signature")
            return None
        except crypto.Error:
            return "SignatureError"

    def error_check(self, error_desc=None):
        if error_desc is not None:
            logger.info("REGISTER ERROR: {}".format(error_desc))
            nok_msg = {
                "MessageType": "DriveGreenRegistrationResponse",
                "Status": "NOK",
                "Error": error_desc
            }
            nok_msg = json.dumps(nok_msg)
            self.mediator.send(nok_msg, self, MessageTypes.BLUETOOTH_MESSAGE)
            message = {
                "status": error_desc
            }
            message = json.dumps(message)
            self.mediator.send(message, self, MessageTypes.REGISTRATION_FAIL)
            return True
        else:
            return False

    def register_device(self, msg):
        try:
            error_desc = None
            wifi_ssid = None
            wifi_password = None
            device_type = "CH"
            feature_type = "DefaultFeature"
            device_features = self.read_features()
            self.access_token = msg["Token"]
            device_name = msg["DeviceName"]
            self.server_url = msg["ServerUrl"]
            self.server_port = msg["Port"]
            signature = msg["Signature"]
            connection_interface = msg["ConnectionInterface"]
            if connection_interface == "WiFi":
                wifi_ssid = msg["WifiSsid"]
                wifi_password = msg["WifiPassword"]
            registration_time = msg["RegistrationTime"]
            self.user_id = msg["UserId"]
            app_name = msg["ApplicationName"]
            start_position = app_name.find("#") + 1
            end_position = app_name.find("#", app_name.find("#") + 1)
            self.customer = app_name[start_position:end_position]
            features_json = json.loads(device_features)
            soft_ver = features_json['DISPLSW']
            device_model = features_json['WGMODEL']
            resp = self.get_encrypted_mac()
            self.device_uuid = "WG_CH_%s" % resp
            hashed_word = hashlib.sha256(
                self.access_token.encode('ascii')).digest()
            content_sha256 = base64.b64encode(hashed_word)
            base_token = content_sha256.decode("utf-8", "ignore")
            mac = self.get_mac()
            mac = mac.replace(":", "")

            verify_data = self.server_url + self.server_port
            error_desc = self.verify_signature(verify_data, signature)
            if self.error_check(error_desc):
                return

            timezone =  msg["Timezone"]
            self.set_timezone(timezone)

            self.update_interfaces(connection_interface,
                                   wifi_ssid, wifi_password)
            message = {
                "type": "interfacesUpdate"
            }
            message = json.dumps(message)
            self.mediator.send(
                message, self, MessageTypes.CONFIGURATION_UPDATE)

            error_desc = self.register_request(app_name, base_token, device_type, mac, soft_ver, device_model, feature_type,
                          device_name, registration_time, device_features)
            if self.error_check(error_desc):
                return
        except Exception as e:
            error_desc = "Other"
            self.error_check(error_desc)
            logger.info(e)

    def get_mac(self):
        eth1 = subprocess.getoutput("ls /sys/class/net | grep eth1")
        if not eth1:
            mac = subprocess.getoutput(
                "cat /sys/class/net/eth0/address | tr a-z A-Z")
        else:
            mac = subprocess.getoutput(
                "cat /sys/class/net/eth1/address | tr a-z A-Z")
        return mac

    def mqtt_connect(self):
        try:
            self.is_configured = self.read_configurations()
            if not self.is_configured:
                return
            self.client = AWSIoTMQTTClient(self.device_uuid)
            self.client.configureEndpoint(self.endpoint, self.port)
            self.client.configureCredentials(
                ROOT_CA_PATH, PRIVATE_KEY_PATH, CERTIFICATE_PATH)

            # AWSIoTMQTTClient connection configuration
            self.client.configureAutoReconnectBackoffTime(1, 32, 20)
            self.client.configureOfflinePublishQueueing(100, dropBehavior=AWSIoTPythonSDK.core.util.enums.DropBehaviorTypes.DROP_OLDEST)
            self.client.configureDrainingFrequency(2)
            self.client.configureConnectDisconnectTimeout(10)
            self.client.configureMQTTOperationTimeout(5)
            self.client.onMessage = self.on_message
            self.client.onOnline = self.on_online
            self.client.onOffline = self.on_offline
            self.client.connectAsync(keepAliveIntervalSecond=10)
            self.client.subscribeAsync("$aws/things/{}/jobs/notify".format(self.device_uuid), 1,
                                       ackCallback=self.suback)
            self.client.subscribeAsync("{}/{}/HM03/CH/{}/to".format(self.customer, self.user_id, self.device_uuid), 1,
                                       ackCallback=self.suback)
            self.client.subscribeAsync("$aws/things/{}/shadow/update/accepted".format(self.device_uuid), 1,
                                       ackCallback=self.suback)

        except Exception as e:
            logger.info(e)

    def read_features(self):
        try:
            wgmodel = None
            modelyr = None
            country = None
            cstomer = None
            modelcd = None
            feature = None
            mainbhw = None
            mainbsw = None
            distype = None
            displhw = None
            displsw = None
            hmiimsi = None
            hmiccid = None
            hmiserl = None

            conn = sqlite3.connect(AGENT_DB_PATH)
            cursor = conn.cursor()
            query = "SELECT hmiDetails.imsi,hmiDetails.iccid,deviceDetails.acpwVersion,deviceDetails.acpwSerialNumber FROM hmiDetails INNER JOIN deviceDetails USING(ID)"
            cursor.execute(query)
            records = cursor.fetchall()
            conn.close()
            for row in records:
                if row[0]:
                    hmiimsi = row[0]
                if row[1]:
                    hmiccid = row[1]
                if row[2]:
                    mainbsw = row[2]
                if row[3]:
                    hmiserl = row[3]

            conn = sqlite3.connect(SYSTEM_DB_PATH)
            cursor = conn.cursor()
            query = "SELECT hmiVersion FROM deviceInfo WHERE ID=1"
            cursor.execute(query)
            records = cursor.fetchall()
            conn.close()
            for row in records:
                if row[0]:
                    displsw = row[0]

            if os.path.exists(VFACTORY_DB_PATH):
                conn = sqlite3.connect(VFACTORY_DB_PATH)
                cursor = conn.cursor()
                query = "SELECT model,modelYear,country,customer,modelCode,mainBoardHw,displayType,displayHw FROM deviceDetails " \
                        "WHERE id=1 "
                cursor.execute(query)
                records = cursor.fetchall()
                conn.close()
                for row in records:
                    if row[0]:
                        wgmodel = row[0]
                    if row[1]:
                        modelyr = row[1]
                    if row[2]:
                        country = row[2]
                    if row[3]:
                        cstomer = row[3]
                    if row[4]:
                        modelcd = row[4]
                    if row[5]:
                        mainbhw = row[5]
                    if row[6]:
                        distype = row[6]
                    if row[7]:
                        displhw = row[7]
            else:
                logger.info("vfactory not found. using default values.")
                wgmodel = DefaultVfactory.MODEL
                modelyr = DefaultVfactory.MODEL_YEAR
                country = DefaultVfactory.COUNTRY
                cstomer = DefaultVfactory.CUSTOMER
                modelcd = DefaultVfactory.MODEL_CODE
                mainbhw = DefaultVfactory.MAINBOARD_HW
                distype = DefaultVfactory.DISPLAY_TYPE
                displhw = DefaultVfactory.DISPLAY_HW

            msg = {
                "WGMODEL": wgmodel,
                "MODELYR": modelyr,
                "COUNTRY": country,
                "CSTOMER": cstomer,
                "MODELCD": modelcd,
                "FEATURE": feature,
                "MAINBHW": mainbhw,
                "MAINBSW": mainbsw,
                "DISTYPE": distype,
                "DISPLHW": displhw,
                "DISPLSW": displsw,
                "HMIIMSI": hmiimsi,
                "HMICCID": hmiccid,
                "HMISERL": hmiserl
            }
            msg = json.dumps(msg)
            return msg

        except Exception as e:
            logger.info(e)

    def read_configurations(self):
        try:
            conn = sqlite3.connect(AGENT_DB_PATH)
            cursor = conn.cursor()
            query = "SELECT deviceUuid,userId,accessToken,serverUrl,serverPort,customer,endpoint,port FROM driveGreen WHERE ID=1"
            cursor.execute(query)
            records = cursor.fetchall()
            conn.close()
            for row in records:
                if row[0]:
                    self.device_uuid = row[0]
                else:
                    return False
                if row[1]:
                    self.user_id = row[1]
                else:
                    return False
                if row[2]:
                    self.access_token = row[2]
                else:
                    return False
                if row[3]:
                    self.server_url = row[3]
                else:
                    return False
                if row[4]:
                    self.server_port = row[4]
                else:
                    return False
                if row[5]:
                    self.customer = row[5]
                else:
                    return False
                if row[6]:
                    self.endpoint = row[6]
                else:
                    return False
                if row[7]:
                    self.port = row[7]
                else:
                    return False
                return True

        except Exception as e:
            logger.info(e)
            return False

    def write_configurations(self):
        try:
            conn = sqlite3.connect(AGENT_DB_PATH)
            cursor = conn.cursor()
            query = 'INSERT OR REPLACE INTO driveGreen (ID, deviceUuid, userId, accessToken, serverUrl, serverPort, customer, endpoint, port) VALUES (1,"{}","{}","{}","{}","{}","{}","{}","{}");'.format(
                self.device_uuid, self.user_id, self.access_token, self.server_url, self.server_port, self.customer, self.endpoint, self.port)
            cursor.execute(query)
            conn.commit()
            conn.close()

        except Exception as e:
            logger.info(e)

    def scan_wireless(self):
        subprocess.getoutput("ifconfig wlan0 up")
        results = subprocess.getoutput(
            "iw dev wlan0 scan | grep -e 'on wlan0\|freq:\|SSID:\|signal:'")
        results = results.replace("\t", "")
        results = results.replace("BSS ", '"Mac": "')
        results = results.replace("(on wlan0)", "")
        results = results.replace("freq: ", '"Band": "')
        results = results.replace("signal: ", '"Rssi": "')
        results = results.replace(" dBm", "")
        results = results.replace(" -- associated", "")
        results = results.replace("SSID: ", '"Ssid": "')
        results = results.replace("\n", '"\n')
        results = results.replace("\\", "\\\\")
        results += '"'
        results = results.split("\n")

        for i in range(len(results)):
            if i % 4 == 0:
                results[i] = "{" + results[i]
            if (i + 1) % 4 == 0:
                results[i] = results[i] + "}"

        ssid_list = ', '.join([str(elem) for elem in results])

        msg = '{"MessageType": "SsidListResponse", "SsidList": [%s]}' % ssid_list

        msg = json.loads(msg)

        for item in msg['SsidList']:
            item["Rssi"] = int(item["Rssi"][:-3])
            if item["Band"][0] == "2":
                item["Band"] = "2.4"
            else:
                item["Band"] = str(item["Band"][0])

        msg = json.dumps(msg)
        self.mediator.send(msg, self, MessageTypes.BLUETOOTH_MESSAGE)

    def send_error_code(self):
        c, f = divmod(self.vendor_error_code, 2 ** 16)
        command = "\"{:s}\":\"{:05d}{:05d}\"".format(ERRORS_LIST_COMMAND, c, f)
        self.publish(command)

    def get_timezone(self):
        res = subprocess.getoutput('timedatectl | grep "Time zone"')
        pos1 = res.find(":") + 2
        pos2 = res.find("(") - 1
        timezone = res[pos1:pos2]
        return timezone

    def on_offline(self):
        self.mutex.acquire()
        self.connection = False
        self.mutex.release()
        logger.info("OFFLINE")

    def on_online(self):
        self.mutex.acquire()
        self.connection = True
        self.mutex.release()
        logger.info("ONLINE")
        timezone = self.get_timezone()
        shadow_message = {
            "state": {
                "reported": {
                    "status": "connected",
                    "customerId": self.user_id,
                    "srv_url": self.server_url,
                    "config": {
                        "timezone": timezone
                    }
                }
            }
        }
        shadow_message = json.dumps(shadow_message)
        self.client.publishAsync("$aws/things/{}/shadow/update".format(self.device_uuid), shadow_message, 1,
                                 ackCallback=self.puback)
        self.send_status_command()
        self.send_error_code()
        self.update_job_status()
        if not self.ota_boot_check():
            if self.get_job_thread is None or not self.get_job_thread.isAlive():
                self.get_job_thread = Thread(target=self.get_next_job)
                self.get_job_thread.start()

    def on_message(self, message):
        message = json.loads(message.payload.decode('utf-8'))
        if "cmd" in message:
            message = message['cmd']
            position = message.find(',')
            command = message[position + 1:position + 8]
            self.publish("\"{}\":\"{}\"".format(
                command, message[position + 8:]))
            logger.info("Received command: {}".format(command))
            if command == CONTROL_COMMAND:
                if message[-1] == '1':
                    start_msg = {
                        "type": "command",
                        "data": {
                            "commandId": AcpwCommandId.START_CHARGING.value,
                            "payload": ""
                        }
                    }
                    start_msg = json.dumps(start_msg)
                    self.mediator.send(start_msg, self, MessageTypes.COMMAND)
                else:
                    stop_msg = {
                        "type": "command",
                        "data": {
                            "commandId": AcpwCommandId.STOP_CHARGING.value,
                            "payload": ""
                        }
                    }
                    stop_msg = json.dumps(stop_msg)
                    self.mediator.send(stop_msg, self, MessageTypes.COMMAND)

            elif command == ECO_TIME_CONTROL_COMMAND:
                least_half = int(message[position + 13:position + 18])
                carry1, start_minute = divmod(least_half, 2 ** 11)
                most_half = int(message[position + 8:position + 13])
                carry2, stop_minute = divmod(most_half, 2 ** 6)
                carry2 = most_half - stop_minute
                stop_minute = stop_minute * (2 ** 5) + carry1
                eco_charge, carry2 = divmod(carry2, 2 ** 6)
                if bool(eco_charge):
                    start_time = "{:02d}:{:02d}".format(
                        int(start_minute / 60), int(start_minute % 60))
                    stop_time = "{:02d}:{:02d}".format(
                        int(stop_minute / 60), int(stop_minute % 60))
                    eco_msg = {
                        "type": "ecoCharge",
                        "status": "Enabled",
                        "startTime": start_time,
                        "stopTime": stop_time
                    }
                else:
                    eco_msg = {
                        "type": "ecoCharge",
                        "status": "Disabled"
                    }
                eco_msg = json.dumps(eco_msg)
                self.mediator.send(eco_msg, self, MessageTypes.ECO_CHARGE)

            elif command == CHARGE_WITH_DELAY_COMMAND:
                least_half = int(message[position + 13:position + 18])
                carry1, delay_time = divmod(least_half, 2 ** 11)
                most_half = int(message[position + 8:position + 13])
                carry2, remaining_time = divmod(most_half, 2 ** 6)
                carry2 = most_half - remaining_time
                remaining_time = remaining_time * (2 ** 5) + carry1
                status, carry2 = divmod(carry2, 2 ** 6)
                if bool(status):
                    delay_msg = {
                        "type": "delayCharge",
                        "status": "Enabled",
                        "delayTime": delay_time,
                        "remainingTime": remaining_time
                    }
                else:
                    delay_msg = {
                        "type": "delayCharge",
                        "status": "Disabled"
                    }
                delay_msg = json.dumps(delay_msg)
                self.mediator.send(delay_msg, self, MessageTypes.DELAY_CHARGE)

        elif "state" in message:
            state = message['state']
            if "desired" in state:
                desired = state['desired']
                if "config" in desired:
                    config = desired['config']
                    if "timezone" in config:
                        timezone = config['timezone']
                        self.set_timezone(timezone)

        elif "jobs" in message:
            jobs = message["jobs"]
            if not self.ota_boot_check() and "QUEUED" in jobs and "IN_PROGRESS" not in jobs:
                logger.info("Received new job update")
                if self.get_job_thread is None or not self.get_job_thread.isAlive():
                    self.get_job_thread = Thread(target=self.get_next_job)
                    self.get_job_thread.start()

        elif "execution" in message:
            try:
                execution = message["execution"]
                document = execution["jobDocument"]
                job_id = execution["jobId"]
                conn = sqlite3.connect(AGENT_DB_PATH)
                cursor = conn.cursor()
                query = 'UPDATE driveGreen SET jobId = "{}" WHERE ID = 1;'.format(job_id)
                cursor.execute(query)
                conn.commit()
                conn.close()
                logger.info("Executing job, id: {}".format(job_id))
                execute_job_thread = Thread(target=self.execute_job , args=((document),))
                execute_job_thread.start()
            except Exception as e:
                logger.info(e)
                self.job_status = "FAILED"
                self.update_job_status()

    def execute_job(self, document):
        try:
            json_array = document['files']
            for item in json_array:
                url = item["fileSource"]["url"]
                filename = os.path.basename(url)
                location = "/var/lib/vestel/{}".format(filename)
                if not self.download_file(url, location):
                    raise Exception
                message = {
                    "type": "agentCommand",
                    "data": {
                        "command": "firmwareUpdate",
                        "location": location
                    }
                }
                message = json.dumps(message)
                self.mediator.send(message, self, MessageTypes.FIRMWARE_UPDATE_STATUS)
        except Exception as e:
            logger.info(e)
            self.job_status = "FAILED"
            self.update_job_status()

    def download_file(self, url, location):
        import urllib.request
        tries = 0
        while True:
            try:
                d = urllib.request.urlopen(url)
                meta = d.getheaders()
                server_file_size = 0
                for item in meta:
                    if "Content-Length" in item:
                        server_file_size = item[1]
                        logger.info("Downloading update file...")
                        urllib.request.urlretrieve(url, location)
                        logger.info("Download completed")
                        local_file_size = os.path.getsize(location)
                        if int(server_file_size) != int(local_file_size):
                            raise Exception("File size doesn't match")
                        return True
            except Exception as e:
                logger.info(e)
                tries = tries + 1
                if tries == 5:
                    return False
                time.sleep(10)
                logger.info("Retrying to download update file")

    def update_job_status(self):
        if self.job_status is not None:
            try:
                conn = sqlite3.connect(AGENT_DB_PATH)
                cursor = conn.cursor()
                query = "SELECT jobId FROM driveGreen;"
                cursor.execute(query)
                row = cursor.fetchone()
                cursor.close()
                conn.close()
                job_id = row[0]
                message = {
                    "status": self.job_status
                }
                message = json.dumps(message)
                self.client.publishAsync("$aws/things/{}/jobs/{}/update".format(
                    self.device_uuid, job_id), message, 1, ackCallback=self.puback)
                logger.info("Job status: {}, {}".format(job_id, self.job_status))

                update_thread = Thread(target=self.update_request)
                update_thread.start()

            except Exception as e:
                logger.info(e)
            self.job_status = None

    def get_next_job(self):
        while True:
            if self.status == ChargePointStatus.AVAILABLE.value:
                message = {
                    "stepTimeoutInMinutes": 35,
                    "clientToken": self.device_uuid
                }
                message = json.dumps(message)
                self.client.publishAsync("$aws/things/{}/jobs/start-next".format(
                    self.device_uuid), message, 1, ackCallback=self.puback)
                break
            else:
                time.sleep(10)

    def ota_boot_check(self):
        ota_deployed = "0"
        try:
            deployCheckFile = open("/var/lib/vestel/isOtaDeployed.txt", "r")
            ota_deployed = deployCheckFile.read(1)
            deployCheckFile.close()
        except FileNotFoundError:
            ota_deployed = "0"
        return ota_deployed == "1"

    def suback(self, mid, data):
        logger.info("Received SUBACK")

    def puback(self, mid):
        logger.info("Received PUBACK")

    def publish(self, msg):
        try:
            message = {"stat": "u:%s-c:{%s}" % (self.device_uuid, msg)}
            json_message = json.dumps(message)
            logger.info("Publishing: {{{}}}".format(msg))
            self.client.publishAsync("{}/{}/HM03/CH/{}/from".format(self.customer, self.user_id, self.device_uuid), json_message,
                                     1, ackCallback=self.puback)
        except Exception as e:
            logger.info(e)

    def send_status_command(self):
        pilot_state = None
        if self.status == ChargePointStatus.AVAILABLE.value:
            pilot_state = 0
        elif self.status == ChargePointStatus.PREPARING.value:
            if self.delay_charge_active:
                pilot_state = 11
            elif self.eco_time_active:
                if self.authorization_status == AuthorizationStatus.START.value:
                    pilot_state = 10
                else:
                    pilot_state = 12
            else:
                pilot_state = 2
        elif self.status == ChargePointStatus.CHARGING.value:
            pilot_state = 5
        elif self.status == ChargePointStatus.FAULTED.value:
            pilot_state = 8
        elif self.status == ChargePointStatus.FINISHING.value:
            if self.authorization_status == AuthorizationStatus.FINISH.value:
                if self.eco_time_active:
                    pilot_state = 12
                else:
                    pilot_state = 2
            else:
                if self.delay_charge_active:
                    pilot_state = 11
                elif self.eco_time_active:
                    pilot_state = 10
                else:
                    pilot_state = 0
        elif self.status == ChargePointStatus.SUSPENDED_EV.value:
            pilot_state = 3
        elif self.status == ChargePointStatus.SUSPENDED_EVSE.value:
            if self.eco_time_active and self.authorization_status == AuthorizationStatus.START.value:
                pilot_state = 3
            else:
                pilot_state = 4
        if pilot_state is not None:
            command = "\"{:s}\":\"{:05d}\"".format(
                GENERAL_STATUS_COMMAND, pilot_state)
            self.publish(command)

    def create_delay_command(self, status, remaining_time, delay_time):
        c, f = divmod(remaining_time, 2 ** 5)
        command = "\"" + CHARGE_WITH_DELAY_COMMAND + "\""
        command += ":\""
        command += "{:05d}".format(int(status) * 2 ** 6 + c)
        command += "{:05d}\"".format(f * 2 ** 11 + delay_time)
        return command

    def send_phase_info(self):
        if (abs(self.voltage_p1 - self.last_voltage_p1) > VOLTAGE_DIFFERENCE or
                abs(self.voltage_p2 - self.last_voltage_p2) > VOLTAGE_DIFFERENCE or
                abs(self.voltage_p3 - self.last_voltage_p3) > VOLTAGE_DIFFERENCE or
                abs(self.current_p1 - self.last_current_p1) > CURRENT_DIFFERENCE or
                abs(self.current_p2 - self.last_current_p2) > CURRENT_DIFFERENCE or
                abs(self.current_p3 - self.last_current_p3) > CURRENT_DIFFERENCE):
            command = "\"" + PHASE_INFO_COMMAND + "\""
            command += ":\""
            command += "{:05d}".format(
                int(self.current_p3 / 1000) * 2 ** 9 + int(self.voltage_p3 / 1000))
            command += "{:05d}".format(
                int(self.current_p2 / 1000) * 2 ** 9 + int(self.voltage_p2 / 1000))
            command += "{:05d}".format(
                int(self.current_p1 / 1000) * 2 ** 9 + int(self.voltage_p1 / 1000))
            command += "\""
            self.publish(command)
        self.last_voltage_p1 = self.voltage_p1
        self.last_voltage_p2 = self.voltage_p2
        self.last_voltage_p3 = self.voltage_p3
        self.last_current_p1 = self.current_p1
        self.last_current_p2 = self.current_p2
        self.last_current_p3 = self.current_p3

    def send_charge_session(self):
        start_time = time.time()
        while self.status == ChargePointStatus.CHARGING.value:
            command = "\"{:s}\":\"{:05d}{:05d}\"".format(SESSION_CURRENT_INFO_COMMAND,
                                                         (self.total_energy -
                                                          self.initial_energy),
                                                         self.active_power_p1 + self.active_power_p2 + self.active_power_p3)
            self.publish(command)
            min_elapsed = int(
                (datetime.now() - self.charge_start_time).total_seconds() / 60)
            command = "\"{:s}\":\"{:05d}\"".format(
                GENERAL_STATUS_COMMAND, min_elapsed * 16 + 5)
            self.publish(command)
            time.sleep(60 - (time.time() - start_time) % 60)

    def read_item(self, item):
        if item["measurand"] == "Current.Import":
            if item['phase'] == "L1":
                self.current_p1 = int(item['value'])
            elif item['phase'] == "L2":
                self.current_p2 = int(item['value'])
            elif item['phase'] == "L3":
                self.current_p3 = int(item['value'])

        elif item["measurand"] == "Power.Active.Import":
            if item['phase'] == "L1":
                self.active_power_p1 = int(item['value'])
            elif item['phase'] == "L2":
                self.active_power_p2 = int(item['value'])
            elif item['phase'] == "L3":
                self.active_power_p3 = int(item['value'])

        elif item["measurand"] == "Voltage":
            if item['phase'] == "L1":
                self.voltage_p1 = int(item['value'])
            elif item['phase'] == "L2":
                self.voltage_p2 = int(item['value'])
            elif item['phase'] == "L3":
                self.voltage_p3 = int(item['value'])

        elif item["measurand"] == "Energy.Active.Import.Register":
            self.total_energy = int(item['value'])

    def get_message(self, message, message_type):
        parsed_msg = json.loads(message)

        if message_type == MessageTypes.BLUETOOTH_MESSAGE:
            if parsed_msg["MessageType"] == "SsidListRequest":
                self.scan_wireless()

            elif parsed_msg["MessageType"] == "DriveGreenConfigurationRequest":
                mac = self.get_mac()
                mac = mac.replace(":", "")
                ok_msg = {
                    "MessageType": "DriveGreenConfigurationResponse",
                    "Status": "OK",
                    "Mac": mac
                }
                ok_msg = json.dumps(ok_msg)
                self.mediator.send(
                    ok_msg, self, MessageTypes.BLUETOOTH_MESSAGE)
                register_thread = Thread(
                    target=self.register_device, args=(parsed_msg,))
                register_thread.start()

        if message_type == MessageTypes.STATUS_NOTIFICATION:
            if "status" in parsed_msg:
                if self.status != parsed_msg["status"]:
                    self.status = parsed_msg["status"]
                    if self.is_configured:
                        self.send_status_command()

            if "vendorErrorCode" in parsed_msg:
                if self.vendor_error_code != parsed_msg["vendorErrorCode"]:
                    self.vendor_error_code = parsed_msg["vendorErrorCode"]
                    if self.is_configured:
                        self.send_error_code()

        elif message_type == MessageTypes.AUTHORIZATION_STATUS:
            self.authorization_status = parsed_msg["status"]
            if self.is_configured and self.eco_time_active:
                self.send_status_command()

        elif message_type == MessageTypes.METER_VALUES:
            if self.is_configured:
                json_array = None
                temp = parsed_msg['meterValue']
                for xs in temp:
                    if xs['sampledValue'] is not None:
                        json_array = xs['sampledValue']
                for item in json_array:
                    self.read_item(item)
                self.send_phase_info()

        elif message_type == MessageTypes.CHARGE_SESSION_STATUS:
            if self.is_configured:
                self.initial_energy = parsed_msg["initialEnergy"]
                self.charge_start_time = datetime.fromtimestamp(
                    parsed_msg["startTime"])
                self.charge_session_status = parsed_msg["status"]
                min_elapsed = int(
                    (datetime.now() - self.charge_start_time).total_seconds() / 60)

                command = "\"" + SESSION_TOTAL_INFO_COMMAND + "\""
                c, f = divmod(
                    (self.total_energy - self.initial_energy), 2 ** 4)
                command += ":\""
                command += "{:05d}".format(c)
                command += "{:05d}".format(f * (2 ** 12) + min_elapsed)
                command += "{:05d}".format(
                    (self.charge_start_time.year - 2000) * (2 ** 9) + self.charge_start_time.month * (
                        2 ** 5) + self.charge_start_time.day)
                if self.charge_session_status == "Started":
                    charge_thread = Thread(target=self.send_charge_session)
                    charge_thread.start()
                    command += "{:05d}".format(self.charge_start_time.hour *
                                               60 * 2 + self.charge_start_time.minute * 2)
                elif self.charge_session_status == "Stopped":
                    command += "{:05d}".format(self.charge_start_time.hour *
                                               60 * 2 + self.charge_start_time.minute * 2 + 1)
                else:
                    return
                command += "\""
                self.publish(command)

        elif message_type == MessageTypes.DELAY_CHARGE:
            if self.is_configured:
                if parsed_msg["type"] == "DelayChargeNotification":
                    if parsed_msg["status"] == "Enabled":
                        remaining_time = parsed_msg["remainingTime"]
                        delay_time = int(parsed_msg["delayTime"])
                        self.delay_charge_active = True
                        command = self.create_delay_command(
                            self.delay_charge_active, remaining_time, delay_time)
                        self.publish(command)
                    else:
                        self.delay_charge_active = False
                    self.send_status_command()

        elif message_type == MessageTypes.ECO_CHARGE:
            if parsed_msg["type"] == "EcoChargeNotification":
                if parsed_msg["status"] == "Enabled":
                    self.eco_time_active = True
                else:
                    self.eco_time_active = False
                if self.is_configured:
                    self.send_status_command()

        elif message_type == MessageTypes.FIRMWARE_UPDATE_STATUS:
            if parsed_msg["type"] == "FirmwareUpdateStatus":
                if parsed_msg["status"] == "Installed":
                    self.job_status = "SUCCEEDED"
                    if self.connection:
                        self.update_job_status()
                        if not self.ota_boot_check():
                            if self.get_job_thread is None or not self.get_job_thread.isAlive():
                                self.get_job_thread = Thread(target=self.get_next_job)
                                self.get_job_thread.start()
                if parsed_msg["status"] == "InstallationFailed":
                    self.job_status = "FAILED"
                    if self.connection:
                        self.update_job_status()
                        if not self.ota_boot_check():
                            if self.get_job_thread is None or not self.get_job_thread.isAlive():
                                self.get_job_thread = Thread(target=self.get_next_job)
                                self.get_job_thread.start()

    def stop(self):
        # TODO
        pass
