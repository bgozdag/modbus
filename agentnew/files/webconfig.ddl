BEGIN TRANSACTION;
CREATE TABLE "account" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"username"	TEXT DEFAULT 'admin',
	"password"	TEXT DEFAULT 'admin',
	"firstLogin"	TEXT DEFAULT 'true'
);
INSERT INTO "account" VALUES(1,'admin','admin','true');
CREATE TABLE "authorizationMode" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"mode"	TEXT,
	"localList"	BLOB
);
INSERT INTO "authorizationMode" VALUES(1,NULL,NULL);
CREATE TABLE "cellularSettings" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"type"	TEXT DEFAULT 'Cellular',
	"enable"	TEXT DEFAULT 'false',
	"apnName"	TEXT,
	"apnUsername"	TEXT,
	"apnPassword"	TEXT,
	"simPin"	TEXT
);
INSERT INTO "cellularSettings" VALUES(1,'Cellular','false',NULL,NULL,NULL,NULL);
CREATE TABLE "dbInfo" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"dbVersion"	INTEGER
);
INSERT INTO "dbInfo" VALUES(1,12);
CREATE TABLE "ethernetSettings" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"type"	TEXT,
	"enable"	TEXT,
	"IPSetting"	TEXT,
	"IPAddress"	TEXT,
	"networkMask"	TEXT,
	"gateway"	TEXT,
	"primaryDNS"	TEXT,
	"secondaryDNS"	TEXT
);
INSERT INTO "ethernetSettings" VALUES(1,'LAN','true','DHCP',NULL, NULL, NULL, NULL, NULL);
CREATE TABLE "generalSettings" (
	"id"	INTEGER NOT NULL DEFAULT 1 PRIMARY KEY AUTOINCREMENT UNIQUE,
	"displayLanguage"	TEXT DEFAULT 'en',
	"backlightDimming"	TEXT,
	"backlightDimmingLevel"	TEXT,
	"webconfigLanguage"	TEXT DEFAULT 'en',
	"contactInfo" 		TEXT,
	"uiTheme" 		TEXT DEFAULT 'darkblue'
);
INSERT INTO "generalSettings" VALUES(1,'en',NULL,NULL,'en',NULL,'darkblue');
CREATE TABLE "ocppConfigurations" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"FreeModeActive"	TEXT DEFAULT 'FALSE',
	"FreeModeRFID"	TEXT DEFAULT 0,
	"AllowOfflineTxForUnknownId"	TEXT DEFAULT 'FALSE',
	"AuthorizationCacheEnabled"	TEXT DEFAULT 'FALSE',
	"AuthorizeRemoteTxRequests"	TEXT DEFAULT 'FALSE',
	"BlinkRepeat"	NUMERIC DEFAULT 0,
	"ChargeProfileMaxStackLevel"	NUMERIC DEFAULT 3,
	"ChargingScheduleAllowedChargingRateUnit"	TEXT DEFAULT 'Current',
	"ChargingScheduleMaxPeriods"	NUMERIC DEFAULT 5,
	"ClockAlignedDataInterval"	NUMERIC DEFAULT 0,
	"ConnectionTimeOut"	NUMERIC DEFAULT 30,
	"ConnectorPhaseRotation"	NUMERIC DEFAULT 0,
	"ConnectorPhaseRotationMaxLength"	NUMERIC DEFAULT 0,
	"ConnectorSwitch3to1PhaseSupported"	TEXT DEFAULT 'FALSE',
        "ContinueChargingAfterPowerLoss" 	TEXT DEFAULT 'FALSE',
	"GetConfigurationMaxKeys"	NUMERIC DEFAULT 1,
	"HeartbeatInterval"	NUMERIC DEFAULT 240,
	"LightIntensity"	NUMERIC DEFAULT 0,
	"LocalAuthListEnabled"	BLOB DEFAULT 'TRUE',
	"LocalAuthListMaxLength"	NUMERIC DEFAULT 10000,
	"LocalAuthorizeOffline"	TEXT DEFAULT 'TRUE',
	"LocalPreAuthorize"	TEXT DEFAULT 'FALSE',
	"MaxChargingProfilesInstalled"	NUMERIC DEFAULT 5,
	"MaxEnergyOnInvalidId"	NUMERIC DEFAULT 0,
	"MeterValuesAlignedData"	NUMERIC DEFAULT 0,
	"MeterValuesAlignedDataMaxLength"	NUMERIC DEFAULT 100,
	"MeterValuesSampledData"	TEXT DEFAULT 'Energy.Active.Import.Register',
	"MeterValuesSampledDataMaxLength"	NUMERIC DEFAULT 4,
	"MeterValueSampleInterval"	NUMERIC DEFAULT 60,
	"MinimumStatusDuration"	NUMERIC DEFAULT 60,
	"NumberOfConnectors"	NUMERIC DEFAULT 1,
	"ReserveConnectorZeroSupported"	TEXT DEFAULT 'TRUE',
	"ResetRetries"	NUMERIC DEFAULT 3,
	"SendLocalListMaxLength"	NUMERIC DEFAULT 10000,
	"SendTotalPowerValue"	TEXT DEFAULT 'FALSE',
	"StopTransactionOnEVSideDisconnect"	TEXT DEFAULT 'TRUE',
	"StopTransactionOnInvalidId"	NUMERIC DEFAULT 'TRUE',
	"StopTxnAlignedData"	NUMERIC DEFAULT 0,
	"StopTxnAlignedDataMaxLength"	NUMERIC DEFAULT 0,
	"StopTxnSampledData"	NUMERIC DEFAULT 0,
	"StopTxnSampledDataMaxLength"	NUMERIC DEFAULT 0,
	"SupportedFeatureProfiles"	TEXT DEFAULT 'Core,FirmwareManagement,LocalAuthListManagement,Reservation,SmartCharging,RemoteTrigger',
	"SupportedFeatureProfilesMaxLength"	NUMERIC DEFAULT 120,
	"TransactionMessageAttempts"	NUMERIC DEFAULT 3,
	"TransactionMessageRetryInterval"	NUMERIC DEFAULT 20,
	"UnlockConnectorOnEVSideDisconnect"	TEXT DEFAULT 'TRUE',
	"WebSocketPingInterval"	NUMERIC DEFAULT 10
);
INSERT INTO "ocppConfigurations" VALUES
(1,'FALSE','0','FALSE','FALSE','FALSE',0,3,'Current',5,0,30,0,0,'FALSE','FALSE',1,240,0,'TRUE',10000,'TRUE','FALSE',5,0,0,100,'Energy.Active.Import.Register',4,60,60,1,'TRUE',3,10000,'FALSE','TRUE','TRUE',0,0,0,0,'Core,FirmwareManagement,LocalAuthListManagement,Reservation,SmartCharging,RemoteTrigger',120,3,20,'TRUE',10);
CREATE TABLE "ocppSettings" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"ocppVersion"	TEXT,
	"centralSystemAddress"	TEXT,
	"chargePointId"	TEXT
);
INSERT INTO "ocppSettings" VALUES(1,NULL,NULL,NULL);
CREATE TABLE "wifiSettings" (
	"id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	"type"	TEXT DEFAULT 'WLAN',
	"enable"	TEXT DEFAULT 'false',
	"ssid"	TEXT,
	"password"	TEXT,
	"securityType"	TEXT,
	"IPSetting"	TEXT,
	"IPAddress"	TEXT,
	"networkMask"	TEXT,
	"gateway"	TEXT,
	"primaryDNS"	TEXT,
	"secondaryDNS"	TEXT
);
INSERT INTO "wifiSettings" VALUES(1,'WLAN','false',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
COMMIT;
