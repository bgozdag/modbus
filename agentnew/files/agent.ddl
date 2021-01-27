
CREATE TABLE `activeChargeSession` (
	`sessionUuid`	TEXT NOT NULL UNIQUE,
	`authorizationUid`	TEXT NOT NULL,
	`startTime`	INTEGER NOT NULL,
	`stopTime`	INTEGER,
	`status`	TEXT NOT NULL,
	`chargePointId`	TEXT NOT NULL,
	`initialEnergy` INTEGER,
	`lastEnergy` INTEGER,
	PRIMARY KEY(`sessionUuid`)
);

CREATE TABLE `chargeSessions` (
	`sessionUuid` TEXT NOT NULL,
	`authorizationUid` TEXT NOT NULL,
	`startTime` INTEGER NOT NULL,
	`stopTime` INTEGER NOT NULL,
	`status` INTEGER NOT NULL,
	`chargePointId` INTEGER NOT NULL,
	`initialEnergy` INTEGER,
	`lastEnergy` INTEGER,
	PRIMARY KEY(`sessionUuid`)
);

CREATE TABLE `chargePoints` (
	`chargePointId`	INTEGER,
	`controlPilotState`	INTEGER,
	`proximityPilotState`	INTEGER,
	`status`	TEXT,
	`errorCode`	TEXT,
	`vendorErrorCode`	INTEGER,
	`voltageP1`	INTEGER,
	`voltageP2`	INTEGER,
	`voltageP3`	INTEGER,
	`currentP1`	INTEGER,
	`currentP2`	INTEGER,
	`currentP3`	INTEGER,
	`activePowerP1`	INTEGER,
	`activePowerP2`	INTEGER,
	`activePowerP3`	INTEGER,
	`activeEnergyP1`	INTEGER,
	`activeEnergyP2`	INTEGER,
	`activeEnergyP3`	INTEGER,
	`lastUpdate` INTEGER,
	`availability` TEXT,
	`minCurrent` INTEGER DEFAULT 0,
	`maxCurrent` INTEGER DEFAULT 0,
	`availableCurrent` INTEGER DEFAULT 0,
	`lockableCable` INTEGER DEFAULT 0,
	`reservationStatus` TEXT DEFAULT 'Disabled',
	`expiryDate` TEXT DEFAULT '',
	`idTag` TEXT DEFAULT '',
	`reservationId` TEXT DEFAULT '',
	`externalCharge` INTEGER DEFAULT 1,
	`currentOfferedValue` INTEGER DEFAULT 0,
	`currentOfferedReason` INTEGER DEFAULT 0,
	`proximityPilotCurrent` INTEGER DEFAULT 0,
	`failsafeCurrent` INTEGER DEFAULT 0,
	`failsafeTimeout` INTEGER DEFAULT 0,
	`modbusTcpCurrent` INTEGER DEFAULT 0,
	PRIMARY KEY(`chargePointId`)
);

CREATE TABLE `driveGreen` (
	`ID` INTEGER NOT NULL,
	`deviceUuid` TEXT,
	`userId` TEXT,
	`accessToken` TEXT,
	`serverUrl` TEXT,
	`serverPort` TEXT,
	`customer` TEXT,
	`endpoint`	TEXT,
	`port`	INTEGER,
	`jobId`	TEXT,
	PRIMARY KEY(`ID`)
);

CREATE TABLE `deviceDetails` (
	`ID`	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
	`acpwVersion`	TEXT,
	`acpwSerialNumber`	TEXT
);

CREATE TABLE `hmiDetails` (
	`ID`	INTEGER PRIMARY KEY AUTOINCREMENT,
	`imei` TEXT,
	`imsi` TEXT,
	`iccid` TEXT,
	`configured` INTEGER DEFAULT 0,
	`masterCard` TEXT
);

INSERT INTO hmiDetails
(ID, imei, imsi, iccid, configured, masterCard)
VALUES(1, NULL, NULL, NULL, 0, NULL);

CREATE TABLE `dipSwitch` (
    `ID`	INTEGER PRIMARY KEY AUTOINCREMENT,
    `dip1` INTEGER,
	`dip2` INTEGER,
	`dip3` INTEGER,
	`dip4` INTEGER,
	`dip5` INTEGER,
	`dip6` INTEGER
);

INSERT INTO dipSwitch (ID, dip1, dip2, dip3, dip4, dip5, dip6)
VALUES (1, 1, 1, 1, 1, 1, 1);

CREATE TABLE `chargeStation` (
	`ID`	            INTEGER PRIMARY KEY AUTOINCREMENT,
	`ecoChargeStatus`	TEXT DEFAULT 'Disabled',
	`ecoChargeStart`	TEXT,
	`ecoChargeStop`     TEXT,
	`delayChargeStatus`	TEXT DEFAULT 'Disabled',
	`delayChargeStart`	INTEGER,
	`delayChargeTime`   INTEGER,
	`powerOptimizerMin` INTEGER,
	`powerOptimizerMax` INTEGER,
	`powerOptimizer` INTEGER,
	`phaseType` INTEGER
);

INSERT INTO chargeStation (ID, ecoChargeStatus,ecoChargeStart,ecoChargeStop,delayChargeStatus,delayChargeStart,
powerOptimizerMin,powerOptimizerMax,powerOptimizer) 
VALUES (
1, 'Disabled',NULL,NULL,'Disabled',NULL,0, 0, 0);

CREATE TABLE `dbInfo` (
	`id`	INTEGER PRIMARY KEY AUTOINCREMENT,
	`dbVersion`	INTEGER
);

INSERT INTO `dbInfo` VALUES(1,3);

CREATE TABLE `otaStatus` (
	`ID`	INTEGER PRIMARY KEY AUTOINCREMENT,
	`previousCommitId`  TEXT,
	`currentCommitId`   TEXT,
	`pendingCommitId`   TEXT,
	`otaType`           INTEGER DEFAULT 0,
	`updateStatus`      TEXT
);

CREATE TRIGGER moveToSessionTable
   AFTER DELETE ON activeChargeSession
BEGIN
    INSERT INTO chargeSessions(
        sessionUuid,
        authorizationUid,
        startTime,
        stopTime,
        status,
        chargePointId,
        initialEnergy,
        lastEnergy
    )
VALUES
    (
        old.sessionUuid,
        old.authorizationUid,
        old.startTime,
        old.stopTime,
        old.status,
        old.chargePointId,
        old.initialEnergy,
        old.lastEnergy
    ) ;
END;
