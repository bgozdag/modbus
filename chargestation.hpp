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
  void getStatusNotification(nlohmann::json msg);
  ChargeSession chargeSession;
  ChargePointStatus status;
  AuthorizationStatus authorizationStatus;
  int vendorErrorCode;
  int proximityPilotState;
};

class ChargeStation
{
public:
  ChargeStation();
  ~ChargeStation();
  void updateStation(nlohmann::json msg);
  ChargePoint chargePoint;
  ChargeStationStatus status;
  ModbusController *modbusController;
  MessageController *messageController;
  void start();
};

#endif
