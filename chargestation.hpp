#ifndef CHARGESTATION_HPP
#define CHARGESTATION_HPP

#include "enum.hpp"
#include "json.hpp"
#include "modbuscontroller.hpp"
#include "messagecontroller.hpp"
#include "chargestation.hpp"
#include <thread>

class ChargePoint{
    public:
        ChargePoint();
        void setChargePointStatus(nlohmann::json msg);
        ChargePointStatus chargePointStatus;
};

class ChargeStation{
    public:
        ChargeStation();
        ~ChargeStation();
        void updateStation(nlohmann::json msg);
        ChargePoint chargePoint;
        ChargeStationStatus chargeStationStatus;
        ModbusController *modbusController;
        MessageController *messageController;
        void start();
};

#endif