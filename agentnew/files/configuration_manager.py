import os
import json
import traceback
import subprocess
import signal
import ipaddress
from definitions import MessageTypes, Requester
import sqlite3
import threading
import time
import socket
import fcntl
import struct
import gpio_controller
import logging

DEBUG = False

if DEBUG:
    AGENT_DATABASE_DEFAULT = "/home/root/agent.db"
    WEBCONFIG_DATABASE_DEFAULT = "/home/root/webconfig.db"
else:
    AGENT_DATABASE_DEFAULT = "/usr/lib/vestel/agent.db"
    WEBCONFIG_DATABASE_DEFAULT = "/usr/lib/vestel/webconfig.db"

AGENT_DATABASE = "/var/lib/vestel/agent.db"
WEBCONFIG_DATABASE = "/var/lib/vestel/webconfig.db"
WEBCONFIG_VFACTORY_DATABASE = "/run/media/mmcblk1p3/webconfig.db"
ACCOUNT_DATABASE = "/var/lib/vestel/account.db"
VFACTORY_DATABASE = "/run/media/mmcblk1p3/vfactory.db"

logger = logging.getLogger("EVC04_Agent.configuration_manager")


class ConfigurationManager(Requester):
    DIP_SW_OFF = 1
    DIP_SW_ON = 0

    def __init__(self):
        self.wwan_connection_process = None
        self.dip_static_ip = ConfigurationManager.DIP_SW_OFF
        self._dip_webconfig_disable = ConfigurationManager.DIP_SW_OFF
        self.dip_master_configuration = ConfigurationManager.DIP_SW_OFF

        self.waiting_for_master_addition = False
        self.force_for_static_ip = False
        super().__init__()

    @property
    def dip_webconfig_disable(self):
        return self._dip_webconfig_disable

    @dip_webconfig_disable.setter
    def dip_webconfig_disable(self, value):
        self._dip_webconfig_disable = value
        if value == ConfigurationManager.DIP_SW_ON:
            subprocess.Popen(["systemctl", "disable", "lighttpd"])
            subprocess.Popen(["systemctl", "disable", "restv2"])
            subprocess.Popen(["systemctl", "stop", "lighttpd"])
            subprocess.Popen(["systemctl", "stop", "restv2"])

        elif value == ConfigurationManager.DIP_SW_OFF:
            subprocess.Popen(["systemctl", "enable", "lighttpd"])
            subprocess.Popen(["systemctl", "enable", "restv2"])
            subprocess.Popen(["systemctl", "start", "lighttpd"])
            subprocess.Popen(["systemctl", "start", "restv2"])

    def _network_priority_control(self):

        time.sleep(10)
        while True:
            try:
                interfaces = self.get_network_interfaces()
                ethernet_interface_name = "eth0"
                if "eth1" in interfaces:
                    ethernet_interface_name = "eth1"

                wifi_ip = self.get_ip_address("wlan0")
                if not (wifi_ip == 0 or wifi_ip is None or wifi_ip == ""):
                    os.system("ifmetric wlan0 100")

                ethernet_ip = self.get_ip_address(ethernet_interface_name)
                if not (ethernet_ip == 0 or ethernet_ip is None or ethernet_ip == ""):
                    os.system("ifmetric " + ethernet_interface_name + " 1000")

                cellular_ip = self.get_ip_address("wwan0")
                if not (cellular_ip == 0 or cellular_ip is None or cellular_ip == ""):
                    os.system("ifmetric wwan0 10")
            except:
                logger.info("setNetworkPriorities issue {0}".format(
                    traceback.format_exc()))

            time.sleep(10)

    def get_ip_address(self, if_name):
        try:
            if_name = if_name[:15].encode('utf-8')
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            return socket.inet_ntoa(fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', if_name)
            )[20:24])
        except:
            return None

    def wifi_ready(self):
        i = 0
        while i < 10:
            interface_list = self.get_network_interfaces()
            if not "wlan0" in interface_list:
                time.sleep(6)
            else:
                return True
            i += 1
        logger.info("wlan0 cannot be detected")
        return False

    def apply_general_settings(self):
        conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "SELECT id, displayLanguage, backlightDimming, backlightDimmingLevel " \
                "FROM generalSettings;"
        cursor.execute(query)
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row is not None:
            row_id, display_language, backlight_dim, backlight_dim_level = row
            pass

    def apply_authentication_settings(self):
        conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "SELECT id, mode, localList FROM authorizationMode;"
        cursor.execute(query)
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row is not None:
            self.mediator.send(row, self, MessageTypes.AUTHORIZATION_TYPE)

    def apply_factory_settings(self, jsonObj):
        self.mediator.send(jsonObj, self, MessageTypes.METER_TYPE)

    def copy_from_json_database(self):
        connection_webconfig = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
        db = connection_webconfig.cursor()
        # Copy general settings to the webconfig database
        if os.path.exists("/var/lib/vestel/generalSettings.json"):
            with open('/var/lib/vestel/generalSettings.json', 'r') as f:
                try:
                    json_general = json.load(f)
                    db.execute("UPDATE generalSettings SET displayLanguage='" + json_general['data'][
                        'displayLanguage'] + "' WHERE id=1")
                    f.close()
                except:
                    logger.info("database update error: {0}".format(
                        traceback.format_exc()))

        # Copy OCPP settings to the webconfig database
        if os.path.exists("/var/lib/vestel/ocppSettings.json"):
            with open('/var/lib/vestel/ocppSettings.json', 'r') as f:
                try:
                    jsonOcpp = json.load(f)
                    db.execute("UPDATE ocppSettings SET ocppVersion='" + jsonOcpp['data'][
                        'ocppVersion'] + "' WHERE id=1")
                    db.execute("UPDATE ocppSettings SET centralSystemAddress='" + jsonOcpp['data'][
                        'centralSystemAddress'] + "' WHERE id=1")
                    db.execute("UPDATE ocppSettings SET chargePointId='" + jsonOcpp['data'][
                        'chargePointId'] + "' WHERE id=1")
                    f.close()
                except:
                    logger.info("database update error: {0}".format(
                        traceback.format_exc()))

        # Copy OCPP configurations to the webconfig database
        if os.path.exists("/var/lib/vestel/ocppConfigurations.json"):
            with open('/var/lib/vestel/ocppConfigurations.json', 'r') as f:
                try:
                    json_ocpp_conf = json.load(f)
                    # Get keys from json file and create sql command
                    conf_keys = json_ocpp_conf['data'].keys()
                    for key in conf_keys:
                        if key != "status":
                            cmd = "UPDATE ocppConfigurations SET " + key + "='" + json_ocpp_conf['data'][
                                key] + "' WHERE id=1"
                            db.execute(cmd)
                    f.close()
                except:
                    logger.info("database update error: {0}".format(
                        traceback.format_exc()))

        # Copy LAN settings to the webconfig database
        if os.path.exists("/var/lib/vestel/interfaces.json"):
            with open('/var/lib/vestel/interfaces.json', 'r') as f:
                try:
                    json_network = json.load(f)
                    db.execute("UPDATE ethernetSettings SET enable='" + str(
                        json_network['data']['Ethernet']['enable']).lower() + "' WHERE id=1")
                    db.execute("UPDATE ethernetSettings SET IPSetting='" + json_network['data']['Ethernet'][
                        'IPSetting'] + "' WHERE id=1")
                    if 'IPAddress' in json_network['data']['Ethernet']:
                        db.execute("UPDATE ethernetSettings SET IPAddress='" + json_network['data']['Ethernet'][
                            'IPAddress'] + "' WHERE id=1")
                    if 'NetworkMask' in json_network['data']['Ethernet']:
                        db.execute("UPDATE ethernetSettings SET networkMask='" + json_network['data']['Ethernet'][
                            'NetworkMask'] + "' WHERE id=1")
                    if 'Gateway' in json_network['data']['Ethernet']:
                        db.execute("UPDATE ethernetSettings SET gateway='" + json_network['data']['Ethernet'][
                            'Gateway'] + "' WHERE id=1")
                    if 'PrimaryDNS' in json_network['data']['Ethernet']:
                        db.execute("UPDATE ethernetSettings SET primaryDNS='" + json_network['data']['Ethernet'][
                            'PrimaryDNS'] + "' WHERE id=1")
                    if 'SecondaryDNS' in json_network['data']['Ethernet']:
                        db.execute("UPDATE ethernetSettings SET secondaryDNS='" + json_network['data']['Ethernet'][
                            'SecondaryDNS'] + "' WHERE id=1")
                except:
                    logger.info("database update error: {0}".format(
                        traceback.format_exc()))

                # Copy WLAN settings to the webconfig database
                try:
                    db.execute("UPDATE wifiSettings SET enable='" + str(
                        json_network['data']['Wifi']['enable']).lower() + "' WHERE id=1")
                    if 'wifiSSID' in json_network['data']['Wifi']:
                        db.execute("UPDATE wifiSettings SET ssid='" + json_network['data']['Wifi'][
                            'wifiSSID'] + "' WHERE id=1")
                    if 'wifiPassword' in json_network['data']['Wifi']:
                        db.execute("UPDATE wifiSettings SET password='" + json_network['data']['Wifi'][
                            'wifiPassword'] + "' WHERE id=1")
                    if 'wifiSecurity' in json_network['data']['Wifi']:
                        db.execute("UPDATE wifiSettings SET securityType='" + json_network['data']['Wifi'][
                            'wifiSecurity'] + "' WHERE id=1")
                    if 'wifiIPSetting' in json_network['data']['Wifi']:
                        db.execute("UPDATE wifiSettings SET IPSetting='" + json_network['data']['Wifi'][
                            'wifiIPSetting'] + "' WHERE id=1")
                    if 'wifiIPaddress' in json_network['data']['Wifi']:
                        db.execute("UPDATE wifiSettings SET IPAddress='" + json_network['data']['Wifi'][
                            'wifiIPaddress'] + "' WHERE id=1")
                    if 'wifiNetworkMask' in json_network['data']['Wifi']:
                        db.execute("UPDATE wifiSettings SET networkMask='" + json_network['data']['Wifi'][
                            'wifiNetworkMask'] + "' WHERE id=1")
                    if 'wifiDefaultGateway' in json_network['data']['Wifi']:
                        db.execute("UPDATE wifiSettings SET gateway='" + json_network['data']['Wifi'][
                            'wifiDefaultGateway'] + "' WHERE id=1")
                    if 'wifiPrimaryDns' in json_network['data']['Wifi']:
                        db.execute("UPDATE wifiSettings SET primaryDNS='" + json_network['data']['Wifi'][
                            'wifiPrimaryDns'] + "' WHERE id=1")
                    if 'wifiSecondaryDns' in json_network['data']['Wifi']:
                        db.execute("UPDATE wifiSettings SET secondaryDNS='" + json_network['data']['Wifi'][
                            'wifiSecondaryDns'] + "' WHERE id=1")
                except:
                    logger.info("database update error: {0}".format(
                        traceback.format_exc()))

                # Copy Cellular settings to the webconfig database
                try:
                    db.execute("UPDATE cellularSettings SET enable='" + str(
                        json_network['data']['Cellular']['enable']).lower() + "' WHERE id=1")
                    if 'apn' in json_network['data']['Cellular']:
                        db.execute("UPDATE cellularSettings SET apnName='" + json_network['data']['Cellular'][
                            'apn'] + "' WHERE id=1")
                    if 'apnUserName' in json_network['data']['Cellular']:
                        db.execute(
                            "UPDATE cellularSettings SET apnUsername='" + json_network['data']['Cellular'][
                                'apnUserName'] + "' WHERE id=1")
                    if 'apnPassword' in json_network['data']['Cellular']:
                        db.execute(
                            "UPDATE cellularSettings SET apnPassword='" + json_network['data']['Cellular'][
                                'apnPassword'] + "' WHERE id=1")
                    if 'simPin' in json_network['data']['Cellular']:
                        db.execute("UPDATE cellularSettings SET simPin='" + json_network['data']['Cellular'][
                            'simPin'] + "' WHERE id=1")
                    f.close()
                except:
                    logger.info("database update error: {0}".format(
                        traceback.format_exc()))

        # Copy authorization mode settings to the webconfig database
        if os.path.exists("/var/lib/vestel/authentication.json"):
            with open('/var/lib/vestel/authentication.json', 'r') as f:
                try:
                    json_mode = json.load(f)
                    mode = json_mode['data']['mode']
                    db.execute(
                        "UPDATE authorizationMode SET mode='" + mode + "' WHERE id=1")

                    if mode == "localList":
                        rfid_list = json_mode['data']['list']
                        rfid_list = ','.join(rfid_list)
                        db.execute(
                            "UPDATE authorizationMode SET localList='" + rfid_list + "' WHERE id=1")
                    f.close()
                except:
                    logger.info("database update error: {0}".format(
                        traceback.format_exc()))

        # Copy account data to the webconfig database
        if os.path.exists(ACCOUNT_DATABASE):
            conn_account = sqlite3.connect(ACCOUNT_DATABASE, timeout=10.0)
            cursor_account = conn_account.cursor()
            query = "SELECT ID, USERNAME, PASSWORD, FIRSTLOGIN FROM USERS;"
            cursor_account.execute(query)
            row_account = cursor_account.fetchone()
            cursor_account.close()
            conn_account.close()
            if row_account is not None:
                row_id, username, password, first_login = row_account
                try:
                    db.execute("UPDATE account SET username='" +
                               username + "' WHERE id=1")
                    db.execute("UPDATE account SET password='" +
                               password + "' WHERE id=1")
                    db.execute("UPDATE account SET firstLogin='" +
                               first_login + "' WHERE id=1")
                except:
                    logger.info("database update error: {0}".format(
                        traceback.format_exc()))
        connection_webconfig.commit()
        connection_webconfig.close()

    def create_new_database(self, newFileName, oldFileName):
        new_db = sqlite3.connect(newFileName, timeout=10.0)
        old_db = sqlite3.connect(oldFileName, timeout=10.0)
        query = "".join(line for line in old_db.iterdump())
        new_db.executescript(query)

    def check_db_versions(self):
        conn = sqlite3.connect(WEBCONFIG_DATABASE_DEFAULT, timeout=10.0)
        cursor = conn.cursor()
        query = "SELECT dbVersion FROM dbInfo;"
        cursor.execute(query)
        row_db = cursor.fetchone()
        cursor.close()
        conn.close()
        if row_db is not None:
            db_version = row_db
        # vfactory database
        conn_vfactory = sqlite3.connect(WEBCONFIG_VFACTORY_DATABASE, timeout=10.0)
        cursor_vfactory = conn_vfactory.cursor()
        query = "SELECT dbVersion FROM dbInfo;"
        cursor_vfactory.execute(query)
        row = cursor_vfactory.fetchone()
        cursor_vfactory.close()
        conn_vfactory.close()
        if row is not None:
            vfactory_version = row
        if db_version < vfactory_version:
            return False
        else:
            return True

    def get_database_version(self, dbFile):
        if os.path.exists(dbFile):
            connection = sqlite3.connect(dbFile, timeout=10.0)
            if (connection):
                db = connection.cursor()
                dbCommand = "SELECT dbVersion FROM dbInfo WHERE id=1"
                db.execute(dbCommand)
                version = db.fetchone()
            else:
                logger.info("Database connection is failed!")
            connection.commit()
            db.close()
            connection.close()
        return version

    def create_database_ddl(self, dbName):
        con = sqlite3.connect(dbName, timeout=10.0)
        db = con.cursor()
        with open('/var/lib/vestel/dump.ddl', 'w') as f:
            for line in con.iterdump():
                if "CREATE TABLE" not in line:
                    if "dbInfo" not in line:
                        if "sqlite_sequence" not in line:
                            if line.startswith("INSERT INTO"):
                                line = str(line).replace(
                                    "INSERT INTO", "INSERT OR REPLACE INTO")
                                stat = line.split('"')
                                if len(stat) > 1:
                                    table = stat[1]
                                    selectStmt = "SELECT * FROM %s" % table
                                    db.execute(selectStmt)
                                    columnNames = [description[0]
                                                   for description in db.description]
                                    if columnNames is not None:
                                        columnList = ', '.join(columnNames)
                                        columnList = "( " + columnList + " )"
                                    table = '"' + table + '"'
                                    columnList = table + columnList
                                    line = line.replace(table, columnList)
                                    f.write('%s\n' % line)
        f.close()
        db.close()
        con.close()

    def initiate_agent_database(self):
        recreate_db = False
        try:
            connection_agent = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
            db = connection_agent.cursor()
            db.execute("SELECT * from deviceDetails")
            db.close()
            connection_agent.close()
        except:
            recreate_db = True
            logger.info("recreating agent db")

        if not os.path.exists(AGENT_DATABASE) or recreate_db:
            self.create_new_database(AGENT_DATABASE, AGENT_DATABASE_DEFAULT)
        else:
            try:
                connection_agent = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                db = connection_agent.cursor()
                db.execute("SELECT * from dbInfo")
                db.close()
                connection_agent.close()
                old_version = self.get_database_version(AGENT_DATABASE)
            except:
                old_version = ""

            new_version = self.get_database_version(AGENT_DATABASE_DEFAULT)
            if old_version == "" or new_version > old_version:
                try:
                    self.create_database_ddl(AGENT_DATABASE)
                    cmd = "rm " + str(AGENT_DATABASE)
                    os.system(cmd)
                    self.create_new_database(
                        AGENT_DATABASE, AGENT_DATABASE_DEFAULT)
                    conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
                    c = conn.cursor()
                    f = open("/var/lib/vestel/dump.ddl", "r")
                    sql = f.readlines()
                    for statement in sql:
                        try:
                            c.executescript(statement)
                        except sqlite3.Error as err:
                            logger.info(err)
                    c.close()
                    conn.close()
                    os.system("rm /var/lib/vestel/dump.ddl")
                except sqlite3.Error as err:
                    logger.info(err)

    def initiate_webconfig_database(self):
        recreate_db = False
        try:
            connection_webconfig = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
            db = connection_webconfig.cursor()
            db.execute("SELECT * from dbInfo")
            db.close()
            connection_webconfig.close()
        except:
            recreate_db = True
            logger.info("recreating webconfig db")

        if not os.path.exists(WEBCONFIG_DATABASE) or recreate_db:
            self.create_new_database(
                WEBCONFIG_DATABASE, WEBCONFIG_DATABASE_DEFAULT)
            if os.path.exists(WEBCONFIG_DATABASE):
                connection_webconfig = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
                db = connection_webconfig.cursor()
                if connection_webconfig:
                    if os.path.exists(WEBCONFIG_VFACTORY_DATABASE):
                        if self.check_db_versions():
                            try:
                                self.create_database_ddl(
                                    WEBCONFIG_VFACTORY_DATABASE)
                                conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
                                c = conn.cursor()
                                f = open('/var/lib/vestel/dump.ddl', 'r')
                                sql = f.readlines()
                                for statement in sql:
                                    try:
                                        c.executescript(statement)
                                    except sqlite3.Error as err:
                                        logger.info(err)
                                c.close()
                                conn.close()
                                os.system("rm /var/lib/vestel/dump.ddl")
                            except sqlite3.Error as err:
                                logger.info(err)
                        else:
                            logger.info("Database versions mismatch!")
                    else:
                        self.copy_from_json_database()

                    connection_webconfig.commit()
                    connection_webconfig.close()
        else:
            old_version = self.get_database_version(WEBCONFIG_DATABASE)
            new_version = self.get_database_version(WEBCONFIG_DATABASE_DEFAULT)
            if old_version[0] < 10:
                cmd = "rm " + WEBCONFIG_DATABASE
                os.system(cmd)
                self.create_new_database(
                    WEBCONFIG_DATABASE, WEBCONFIG_DATABASE_DEFAULT)
                self.copy_from_json_database()
            else:
                if new_version > old_version:
                    try:
                        self.create_database_ddl(WEBCONFIG_DATABASE)
                        cmd = "rm " + str(WEBCONFIG_DATABASE)
                        os.system(cmd)
                        self.create_new_database(
                            WEBCONFIG_DATABASE, WEBCONFIG_DATABASE_DEFAULT)
                        conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
                        c = conn.cursor()
                        f = open("/var/lib/vestel/dump.ddl", "r")
                        sql = f.readlines()
                        for statement in sql:
                            try:
                                c.executescript(statement)
                            except sqlite3.Error as err:
                                logger.info(err)
                        c.close()
                        conn.close()
                        os.system("rm /var/lib/vestel/dump.ddl")
                    except sqlite3.Error as err:
                        logger.info(err)

    def initialize_configurations(self):
        os.makedirs("/var/lib/vestel", mode=0o700, exist_ok=True)
        self.initiate_agent_database()
        self.initiate_webconfig_database()
        self.check_dip_switches()
        self.apply_settings()

        network_priority_thread = threading.Thread(
            target=self._network_priority_control, daemon=True)
        network_priority_thread.start()

    def check_dip_switches(self):
        gpio_controller.export_gpio_pin(57)
        gpio_controller.export_gpio_pin(56)
        gpio_controller.export_gpio_pin(55)

        conn = sqlite3.connect(AGENT_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "SELECT * FROM dipSwitch;"
        cursor.execute(query)
        row = cursor.fetchone()
        if row is not None:
            id, dip1, dip2, dip3, dip4, dip5, dip6 = row
            self.dip_master_configuration = dip1
            self.dip_static_ip = dip2
            if self.dip_master_configuration != gpio_controller.read_gpio_pin(57):
                self.dip_master_configuration = gpio_controller.read_gpio_pin(57)
                query = "UPDATE dipSwitch SET dip1={} WHERE ID=1".format(
                    self.dip_master_configuration)
                cursor.execute(query)
                logger.info("master card dip switch toggled")
                self.waiting_for_master_addition = True

            if self.dip_static_ip != gpio_controller.read_gpio_pin(56):
                self.dip_static_ip = gpio_controller.read_gpio_pin(56)
                query = "UPDATE dipSwitch SET dip2={} WHERE ID=1".format(
                    self.dip_static_ip)
                cursor.execute(query)
                logger.info("static ip dip switch toggled")
                self.force_for_static_ip = True

        conn.commit()
        conn.close()

        self.dip_webconfig_disable = gpio_controller.read_gpio_pin(55)

    def apply_settings(self):
        self.apply_network_interface_settings(boot=True)
        self.apply_general_settings()

    def get_message(self, message, message_type):
        message = json.loads(message)
        if message_type == MessageTypes.CONFIGURATION_UPDATE:
            if message["type"] == "authenticationUpdate":
                self.apply_authentication_settings()
            elif message["type"] == "generalUpdate":
                self.apply_general_settings()
            elif message["type"] == "interfacesUpdate":
                self.apply_network_interface_settings()
        elif message_type == MessageTypes.COMMAND:
            pass

    @staticmethod
    def get_network_interfaces():
        cmd = "ls /sys/class/net/"
        interface_list = os.popen(cmd).read().split()
        return interface_list

    def apply_network_interface_settings(self, boot=False):
        self.apply_wwan_settings()
        self.apply_ethernet_settings(boot)
        self.apply_wifi_settings()

    def apply_ethernet_settings(self, boot):
        ethernet_interface_name = "eth0"
        ethernet_file_name = "/etc/systemd/network/10-eth.network"
        interfaces = self.get_network_interfaces()
        if "eth1" in interfaces:
            ethernet_interface_name = "eth1"
            ethernet_file_name = "/etc/systemd/network/15-eth.network"

        os.system("rm " + ethernet_file_name)

        row = None
        try:
            conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT id, type, enable, IPSetting, IPAddress, " \
                    "networkMask, gateway, primaryDNS, secondaryDNS FROM " \
                    "ethernetSettings;"

            cursor.execute(query)
            row = cursor.fetchone()

            cursor.close()
            conn.close()

        except Exception as e:
            logger.error("Webconfig database error during ethernet configuration: {}".format(str(e)))

        if self.force_for_static_ip and boot:
            ip_address = "192.168.0.10"
            subnet_mask = "255.255.255.0"
            subnet_mask_prefix = "24"
            primaryDNS = "8.8.8.8"
            secondaryDNS = "8.8.4.4"
            address = ip_address + "/" + subnet_mask_prefix
            gateway = "192.168.0.1"
            config_file = "[Match]\nName={0}\n[Network]\n".format(
                ethernet_interface_name)
            config_file = config_file + "Address={0}\nGateway={1}".format(
                address, gateway)
            os.system('echo \"' + config_file +
                      '\" > \"' + ethernet_file_name + '\"')

            try:
                conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
                cursor = conn.cursor()

                query = 'UPDATE ethernetSettings SET IPSetting="Static", IPAddress="{}", gateway="{}", networkMask="{}", primaryDNS="{}", secondaryDNS="{}" WHERE id=1'.format(
                    ip_address, gateway, subnet_mask, primaryDNS, secondaryDNS)
                cursor.execute(query)
                conn.commit()

                cursor.close()
                conn.close()

            except Exception as e:
                logger.error("Error occurred saving ethernet configuration on webconfig database: {}".format(str(e)))
                
        else:
            if row is not None:
                row_id, network_type, enable, ip_setting, \
                ip_address, network_mask, gateway, primary_dns, secondary_dns = row
                if enable == "true":
                    if ip_setting == "Static":
                        address = ipaddress.IPv4Interface(
                            ip_address + '/' + network_mask).with_prefixlen
                        config_file = "[Match]\nName={0}\n[Network]\n".format(
                            ethernet_interface_name)
                        config_file = config_file + "Address={0}\nGateway={1}\nDNS={2} {3}".format(
                            address, gateway, primary_dns, secondary_dns)
                        os.system('echo \"' + config_file +
                                  '\" > \"' + ethernet_file_name + '\"')
                    else:
                        config_file = "[Match]\nName={0}\n[Network]\nDHCP=yes".format(
                            ethernet_interface_name)
                        os.system('echo \"' + config_file +
                                  '\" > \"' + ethernet_file_name + '\"')
                else:
                    disable_ethernet = "ln -s /dev/null /etc/systemd/network/10-eth.network"
                    down_ethernet = 'ifconfig ' + ethernet_interface_name + ' down'
                    if ethernet_interface_name == "eth1":
                        disable_ethernet = "ln -s /dev/null /etc/systemd/network/15-eth.network"
                    os.system(disable_ethernet)
                    os.system(down_ethernet)

        os.system("systemctl restart systemd-networkd")

    def apply_wwan_settings(self):

        wwan_file_name = "/etc/systemd/network/50-wwan.network"
        os.system("rm " + wwan_file_name)
        conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
        cursor = conn.cursor()
        query = "SELECT id, type, enable, apnName, apnUsername, " \
                "apnPassword, simPin FROM cellularSettings;"
        cursor.execute(query)
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if row is not None:
            row_id, network_type, enable, apn_name, apn_user_name, apn_password, sim_pin = row
            if enable == "true":
                config_file = "[Match]\nName=wwan0\n[Network]\nDHCP=yes"
                os.system('echo \"' + config_file +
                          '\" > \"' + wwan_file_name + '\"')
                os.system("systemctl restart systemd-networkd")

                if apn_user_name != "" and apn_password != "":
                    cellular_enable_cmd = \
                        'quectel-cm -s ' + apn_name + ' ' + apn_user_name + ' ' + apn_password + ' &'
                    if sim_pin != "":
                        cellular_enable_cmd = \
                            'quectel-cm -s ' + apn_name + ' ' + apn_user_name + ' ' + apn_password + \
                            ' -p ' + sim_pin + ' &'

                elif sim_pin != "":
                    cellular_enable_cmd = 'quectel-cm -s ' + apn_name + ' -p ' + sim_pin + ' &'
                else:
                    cellular_enable_cmd = 'quectel-cm -s ' + apn_name + ' &'

                self.wwan_connection_process = \
                    subprocess.Popen(cellular_enable_cmd, stdout=subprocess.PIPE,
                                     shell=True, preexec_fn=os.setsid)
            else:
                disable_wwan = "ln -s /dev/null /etc/systemd/network/50-wwan.network"
                os.system(disable_wwan)
                os.system("systemctl restart systemd-networkd")
                if self.wwan_connection_process is not None:
                    os.killpg(os.getpgid(
                        self.wwan_connection_process.pid), signal.SIGTERM)

    def apply_wifi_settings(self):

        if self.wifi_ready():
            cmd = "/usr/lib/vestel/wpa-setup.sh disconnect"
            os.system(cmd)
            wifi_file_name = "/etc/systemd/network/30-wlan.network"
            os.system("rm " + wifi_file_name)
            conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT id, type, enable, ssid, password, securityType, IPSetting, IPAddress, " \
                    "networkMask, gateway, primaryDNS, secondaryDNS FROM " \
                    "wifiSettings;"
            cursor.execute(query)
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row is not None:
                row_id, network_type, enable, ssid, password, security_type, ip_setting, \
                ip_address, network_mask, gateway, primary_dns, secondary_dns = row
                if enable == "true":
                    if ip_setting == "Static":
                        address = ipaddress.IPv4Interface(
                            ip_address + '/' + network_mask).with_prefixlen
                        config_file = "[Match]\nName=wlan0\n[Network]\n"
                        config_file = config_file + "Address={0}\nGateway={1}\nDNS={2} {3}".format(
                            address, gateway, primary_dns, secondary_dns)
                        os.system('echo \"' + config_file +
                                  '\" > \"' + wifi_file_name + '\"')

                    else:  # DHCP
                        config_file = "[Match]\nName=wlan0\n[Network]\nDHCP=yes"
                        os.system('echo \"' + config_file +
                                  '\" > \"' + wifi_file_name + '\"')

                    os.system("systemctl restart systemd-networkd")

                    if security_type == "none":
                        connect_cmd = "/usr/lib/vestel/wpa-setup.sh connect none '{}'".format(
                            ssid)
                    else:
                        connect_cmd = "/usr/lib/vestel/wpa-setup.sh connect wpa '{}' {}".format(
                            ssid, password)

                    os.system(connect_cmd)
                else:
                    cmd = "/usr/lib/vestel/wpa-setup.sh disconnect"
                    os.system(cmd)

    def is_cellular_enabled(self):
        try:
            conn = sqlite3.connect(WEBCONFIG_DATABASE, timeout=10.0)
            cursor = conn.cursor()
            query = "SELECT enable FROM cellularSettings;"
            cursor.execute(query)
            row = cursor.fetchone()
            enabled = row[0]
            cursor.close()
            conn.close()
            if enabled == 'true':
                return True

            return False

        except Exception as e:
            logger.error("Error connecting WEBCONFIG database for cellular information: {}".format(str(e)))
            return False

    def reset_quectel_modem(self):
        logger.info("Resetting Quectel Modem..")
        try:
            pinNr = 48

            gpio_controller.export_gpio_pin(pinNr)
            gpio_controller.set_gpio_pin_direction(pinNr, 'out')

            gpio_controller.write_gpio_pin(pinNr, 1)
            time.sleep(1)
            gpio_controller.write_gpio_pin(pinNr, 0)

            for i in range(10):
                interfaceList = self.get_network_interfaces()

                if 'wwan0' in interfaceList:
                    break

                else:
                    time.sleep(6)

                self.apply_wwan_settings()

        except Exception as e:
            logger.error("Error resetting Quectel Modem: {}".format(str(e)))

        logger.info("Quectel Model is successfully reset")
        
        
class DefaultVfactory:
    MODEL = "EVC04"
    MODEL_YEAR = "2020"
    COUNTRY = "TR"
    CUSTOMER = "VESTEL"
    MODEL_CODE = "EVC04WL"
    MAINBOARD_HW = None
    DISPLAY_TYPE = None
    DISPLAY_HW = None
