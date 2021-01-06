#ifndef CHARGESTATION_HPP
#define CHARGESTATION_HPP

#include "enum.hpp"
#include "json.hpp"
#include "modbuscontroller.hpp"
#include "messagecontroller.hpp"
#include "chargestation.hpp"
#include "sqlite3.h"
#include <thread>

#define AGENT_DB_PATH "/var/lib/vestel/webconfig.db"

class ChargeSession{
    public:
        ChargeSession();
        static int callback(void* data, int argc, char** argv, char** azColName){
            
        };
        int lastEnergy;
        int initialEnergy;
        int startTime;
        ChargeSessionStatus status;
};

class ChargePoint{
    public:
        ChargePoint();
        void getStatusNotification(nlohmann::json msg);
        ChargeSession chargeSession;
        ChargePointStatus status;
        AuthorizationStatus authorizationStatus;
        int vendorErrorCode;
};

class ChargeStation{
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