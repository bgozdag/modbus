#include "chargestation.hpp"

ChargeSession::ChargeSession(){
    sqlite3* db;
    char* zErrMsg = 0;
    int rc;
    std::string query = "SELECT startTime,stopTime,status,initialEnergy,lastEnergy FROM activeChargeSession WHERE id = 1";
    rc = sqlite3_open(AGENT_DB_PATH, &db);

    if (rc != SQLITE_OK) {
        logErr("Can't open database: %s %s\n", AGENT_DB_PATH, sqlite3_errmsg(db));
    } else {
        sqlite3_exec(db, query.c_str(), callback, nullptr, &zErrMsg);
    }
    sqlite3_close(db);
}

ChargeStation::ChargeStation(){
    status = ChargeStationStatus::Initializing;
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
            chargePoint.getStatusNotification(msg);
            this->modbusController->set_chargepoint_states(chargePoint.status, chargePoint.vendorErrorCode);
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
    status = ChargePointStatus::Available;
}

void ChargePoint::getStatusNotification(nlohmann::json msg){
    std::string status;
    msg.at("status").get_to(status);
    auto it = chargePointStatusTable.find(status);
    status = it->second;
    msg.at("vendorErrorCode").get_to(vendorErrorCode);
}