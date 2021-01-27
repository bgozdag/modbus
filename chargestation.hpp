#ifndef CHARGESTATION_HPP
#define CHARGESTATION_HPP

#include "chargestation.hpp"
#include "enum.hpp"
#include "json.hpp"
#include "messagecontroller.hpp"
#include "modbuscontroller.hpp"
#include "sqlite3.h"
#include <thread>
#include <unistd.h>

#define AGENT_DB_PATH "/var/lib/vestel/agent.db"
#define WEBCONFIG_DB_PATH "/var/lib/vestel/webconfig.db"
#define VFACTORY_DB_PATH "/run/media/mmcblk1p3/vfactory.db"
#define SYSTEM_DB_PATH "/usr/lib/vestel/system.db"

using json = nlohmann::json;

class ChargeSession
{
public:
  ChargeSession();
  static int callback(void *data, int argc, char **argv, char **azColName)
  {
    ChargeSession *chargeSession = (ChargeSession *)data;
    if (argv != nullptr) {
      if(argv[0] != nullptr)
      {
        chargeSession->startTime = atoi(argv[0]);
      }
      if(argv[1] != nullptr)
      {
        chargeSession->stopTime = atoi(argv[1]);
      }
      if(argv[2] != nullptr)
      {
        auto it = chargeSessionStatusTable.find(argv[2]);
        chargeSession->status = it->second;
      }
      if(argv[3] != nullptr)
      {
        chargeSession->initialEnergy = atoi(argv[3]);
      }
      if(argv[4] != nullptr)
      {
        chargeSession->lastEnergy = atoi(argv[4]);
      }
    }
    return 0;
  };
  void getChargeSession(json msg);
  int lastEnergy;
  int initialEnergy;
  int startTime;
  int stopTime;
  ChargeSessionStatus status;
};

class ChargePoint
{
public:
  ChargePoint();
  static int callback(void *data, int argc, char **argv, char **azColName)
  {
    ChargePoint *chargePoint = (ChargePoint *)data;
    if (argv != nullptr)
    {
      if(argv[0] != nullptr)
      {
        chargePoint->pilotState = atoi(argv[0]);
      }
      if(argv[1] != nullptr)
      {
        chargePoint->proximityPilotState = atoi(argv[1]);
      }
      if(argv[2] != nullptr)
      {
        auto it = chargePointStatusTable.find(argv[2]);
        chargePoint->status = it->second;
      }
      if(argv[3] != nullptr)
      {
        chargePoint->vendorErrorCode = atoi(argv[3]);
      }
      if(argv[4] != nullptr)
      {
        chargePoint->voltageP1 = atoi(argv[4]);
      }
      if(argv[5] != nullptr)
      {
        chargePoint->voltageP2 = atoi(argv[5]);
      }
      if(argv[6] != nullptr)
      {
        chargePoint->voltageP3 = atoi(argv[6]);
      }
      if(argv[7] != nullptr)
      {
        chargePoint->currentP1 = atoi(argv[7]);
      }
      if(argv[8] != nullptr)
      {
        chargePoint->currentP2 = atoi(argv[8]);
      }
      if(argv[9] != nullptr)
      {
        chargePoint->currentP3 = atoi(argv[9]);
      }
      if(argv[10] != nullptr)
      {
        chargePoint->activePowerP1 = atoi(argv[10]);
      }
      if(argv[11] != nullptr)
      {
        chargePoint->activePowerP2 = atoi(argv[11]);
      }
      if(argv[12] != nullptr)
      {
        chargePoint->activePowerP3 = atoi(argv[12]);
      }
      if(argv[13] != nullptr)
      {
        chargePoint->activeEnergyP1 = atoi(argv[13]);
      }
      if(argv[14] != nullptr)
      {
        chargePoint->activeEnergyP2 = atoi(argv[14]);
      }
      if(argv[15] != nullptr)
      {
        chargePoint->activeEnergyP3 = atoi(argv[15]);
      }
      if(argv[16] != nullptr)
      {
        auto it2 = chargePointAvailabilityTable.find(argv[16]);
        chargePoint->availability = it2->second;
      }
      if(argv[17] != nullptr)
      {
        chargePoint->minCurrent = atoi(argv[17]);
      }
      if(argv[18] != nullptr)
      {
        chargePoint->maxCurrent = atoi(argv[18]);
      }
      if(argv[19] != nullptr)
      {
        chargePoint->availableCurrent = atoi(argv[19]);
      }
      if(argv[20] != nullptr)
      {
        chargePoint->currentOfferedToEv = atoi(argv[20]);
      }
      if(argv[21] != nullptr)
      {
        chargePoint->currentOfferedToEvReason = static_cast<CurrentOfferedToEvReason>(atoi(argv[21]));
      }
      if(argv[22] != nullptr)
      {
        chargePoint->cableMaxCurrent = atoi(argv[22]);
      }
      if(argv[23] != nullptr)
      {
        chargePoint->failsafeCurrent = atoi(argv[23]);
      }
      if(argv[24] != nullptr)
      {
        chargePoint->failsafeTimeout = atoi(argv[24]);
      }
      if(argv[25] != nullptr)
      {
        chargePoint->modbusTcpCurrent = atoi(argv[25]);
      }
    }
    return 0;
  };
  void getStatusNotification(json msg);
  void getMeterValues(json msg);
  void getPilotStates(json msg);
  void getAuthorizationStatus(json msg);
  void getCurrentOffered(json msg);
  void getMinCurrent(json msg);
  void getMaxCurrent(json msg);
  void getCableMaxCurrent(json msg);
  ChargeSession chargeSession;
  ChargePointStatus status;
  AuthorizationStatus authorizationStatus;
  int vendorErrorCode;
  int pilotState;
  int proximityPilotState;
  int voltageP1;
  int voltageP2;
  int voltageP3;
  int currentP1;
  int currentP2;
  int currentP3;
  int activePowerP1;
  int activePowerP2;
  int activePowerP3;
  int activeEnergyP1;
  int activeEnergyP2;
  int activeEnergyP3;
  ChargePointAvailability availability;
  int minCurrent;
  int maxCurrent;
  int currentOfferedToEv;
  CurrentOfferedToEvReason currentOfferedToEvReason;
  int availableCurrent;
  int cableMaxCurrent;
  int failsafeCurrent;
  int failsafeTimeout;
  int modbusTcpCurrent;
};

class ChargeStation
{
public:
  ChargeStation();
  ~ChargeStation();
  static int agent_callback(void *data, int argc, char **argv, char **azColName)
  {
    ChargeStation *chargeStation = (ChargeStation *)data;
    if (argv != nullptr) {
      if(argv[0] != nullptr)
      {
        chargeStation->phaseType = atoi(argv[0]);
      }
      if(argv[1] != nullptr)
      {
        chargeStation->powerOptimizer = atoi(argv[1]);
      }
      if(argv[2] != nullptr)
      {
        chargeStation->powerOptimizerMin = atoi(argv[2]);
      }
      if(argv[3] != nullptr)
      {
        chargeStation->powerOptimizerMax = atoi(argv[3]);
      }
      if(argv[4] != nullptr)
      {
        chargeStation->serial = argv[4];
      }
      if(argv[5] != nullptr)
      {
        chargeStation->acpwVersion = argv[5];
      }
    }
    return 0;
  };
  static int vfactory_callback(void *data, int argc, char **argv, char **azColName)
  {
    ChargeStation *chargeStation = (ChargeStation *)data;
    if (argv != nullptr) {
      if(argv[0] != nullptr)
      {
        chargeStation->model = argv[0];
      }
      if(argv[1] != nullptr)
      {
        chargeStation->brand = argv[1];
      }
    }
    return 0;
  };
  static int system_callback(void *data, int argc, char **argv, char **azColName)
  {
    ChargeStation *chargeStation = (ChargeStation *)data;
    if (argv != nullptr) {
      if(argv[0] != nullptr)
      {
        chargeStation->hmiVersion = argv[0];
      }
    }
    return 0;
  };
  static int webconfig_callback(void *data, int argc, char **argv, char **azColName)
  {
    ChargeStation *chargeStation = (ChargeStation *)data;
    if (argv != nullptr) {
      if(argv[0] != nullptr)
      {
        chargeStation->chargePointId = argv[0];
      }
    }
    return 0;
  };
  void updateStation(json msg);
  void getStatusNotification(json msg);
  void readAgentDb();
  void readSystemDb();
  void readWebconfigDb();
  void readVfactoryDb();
  void getSerial(json msg);
  void getPhase(json msg);
  void getPowerOptimizer(json msg);
  void getPowerOptimizerLimits(json msg);
  void updateChargeSession();
  void start();
  ModbusController *modbusController;
  MessageController *messageController;
  ChargePoint chargePoint;
  ChargeStationStatus status;
  int phaseType;
  int powerOptimizer;
  int powerOptimizerMin;
  int powerOptimizerMax;
  std::string serial;
  std::string brand;
  std::string model;
  std::string hmiVersion;
  std::string acpwVersion;
  std::string chargePointId;
};

#endif
