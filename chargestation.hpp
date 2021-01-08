#ifndef CHARGESTATION_HPP
#define CHARGESTATION_HPP

#include "chargestation.hpp"
#include "enum.hpp"
#include "json.hpp"
#include "messagecontroller.hpp"
#include "modbuscontroller.hpp"
#include "sqlite3.h"
#include <thread>

#define AGENT_DB_PATH "/var/lib/vestel/agent.db"
#define VFACTORY_DB_PATH "/run/media/mmcblk1p3/vfactory.db"
#define SYSTEM_DB_PATH "/usr/lib/vestel/system.db"

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
            chargeSession->stopTime = atoi(argv[1]);
            auto it = chargeSessionStatusTable.find(argv[2]);
            chargeSession->status = it->second;
            chargeSession->initialEnergy = atoi(argv[3]);
            chargeSession->lastEnergy = atoi(argv[4]);
        }
    }
    return 0;
  };
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
    if (argv != nullptr) {
        if(argv[0] != nullptr)
        {
            chargePoint->proximityPilotState = atoi(argv[0]);
            auto it = chargePointStatusTable.find(argv[1]);
            chargePoint->status = it->second;
            chargePoint->vendorErrorCode = atoi(argv[2]);
            chargePoint->voltageP1 = atoi(argv[3]);
            chargePoint->voltageP2 = atoi(argv[4]);
            chargePoint->voltageP3 = atoi(argv[5]);
            chargePoint->currentP1 = atoi(argv[6]);
            chargePoint->currentP2 = atoi(argv[7]);
            chargePoint->currentP3 = atoi(argv[8]);
            chargePoint->activePowerP1 = atoi(argv[9]);
            chargePoint->activePowerP2 = atoi(argv[10]);
            chargePoint->activePowerP3 = atoi(argv[11]);
            chargePoint->activeEnergyP1 = atoi(argv[12]);
            chargePoint->activeEnergyP2 = atoi(argv[13]);
            chargePoint->activeEnergyP3 = atoi(argv[14]);
            auto it2 = chargePointAvailabilityTable.find(argv[15]);
            chargePoint->availability = it2->second;
            chargePoint->minCurrent = atoi(argv[16]);
            chargePoint->maxCurrent = atoi(argv[17]);
            chargePoint->availableCurrent = atoi(argv[18]);
            auto it3 = authorizationStatusTable.find(argv[19]);
            chargePoint->authorizationStatus = it3->second;
        }
    }
    return 0;
  };
  void getStatusNotification(nlohmann::json msg);
  ChargeSession chargeSession;
  ChargePointStatus status;
  AuthorizationStatus authorizationStatus;
  int vendorErrorCode;
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
  int availableCurrent;
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
        chargeStation->powerOptimizer = atoi(argv[1]);
        chargeStation->powerOptimizerMin = atoi(argv[2]);
        chargeStation->powerOptimizerMax = atoi(argv[3]);
        chargeStation->serial = argv[4];
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
        chargeStation->fwVersion = argv[0];
      }
    }
    return 0;
  };
  void updateStation(nlohmann::json msg);
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
  std::string fwVersion;
};

#endif
