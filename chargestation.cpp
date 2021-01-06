#include "chargestation.hpp"

ChargeStation::ChargeStation(){
    chargeStationStatus = ChargeStationStatus::Initializing;
    modbusController = new ModbusController("127.0.0.1", 502);
    messageController  = new MessageController("modbus");
}

ChargeStation::~ChargeStation(){
    delete messageController;
    delete modbusController;
}

void ChargeStation::updateStation(nlohmann::json msg){
    std::string type;
    if (msg["type"].is_string()){
        msg.at("type").get_to(type);
        logInfo("received: %s\n", type.c_str());
        if (type.compare("StatusNotification") == 0){
            chargePoint.setChargePointStatus(msg);
            this->modbusController->set_chargepoint_state(chargePoint.chargePointStatus);
        }
    }
    else {
        logWarning("received invalid msg type\n");
    }
}

void ChargeStation::start(){
    std::string msg;
    nlohmann::json json;
    std::thread modbusListener(&ModbusController::listen, modbusController);

    while(1){
        msg = this->messageController->receive();
        json = this->messageController->parse(msg);
        updateStation(json);
        json.clear();
    }
}

ChargePoint::ChargePoint(){
    chargePointStatus = ChargePointStatus::Available;
}

void ChargePoint::setChargePointStatus(nlohmann::json msg){
    std::string status;
    msg.at("status").get_to(status);
    auto it = chargePointStatusTable.find(status);
    chargePointStatus = it->second;
}