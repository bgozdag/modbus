#include "chargestation.hpp"

ChargeSession::ChargeSession()
{
  startTime = 0;
  stopTime = 0;
  status = ChargeSessionStatus::Stopped;
  initialEnergy = 0;
  lastEnergy = 0;

  sqlite3 *db;
  char *zErrMsg = 0;
  int rc;
  std::string query =
      "SELECT startTime,stopTime,status,initialEnergy,lastEnergy FROM "
      "activeChargeSession";
  rc = sqlite3_open(AGENT_DB_PATH, &db);

  if (rc != SQLITE_OK)
  {
    logErr("Can't open database: %s %s\n", AGENT_DB_PATH, sqlite3_errmsg(db));
  }
  else
  {
    int check = sqlite3_exec(db, query.c_str(), callback, this, &zErrMsg);
    if (check != SQLITE_OK)
    {
      logErr("sql exec error: %s\n", sqlite3_errmsg(db));
    }
  }
  sqlite3_close(db);
}

void ChargeSession::getChargeSession(json msg)
{
  msg.at("startTime").get_to(startTime);
  if (msg["finishTime"].is_number())
  {
    msg.at("finishTime").get_to(stopTime);
  }
  else
  {
    stopTime = 0;
  }
  msg.at("initialEnergy").get_to(initialEnergy);
  msg.at("lastEnergy").get_to(lastEnergy);
  std::string stt;
  msg.at("status").get_to(stt);
  auto it = chargeSessionStatusTable.find(stt);
  status = it->second;
}

ChargeStation::ChargeStation()
{
  status = ChargeStationStatus::Normal;
  phaseType = 0;
  powerOptimizer = 0;
  powerOptimizerMin = 0;
  powerOptimizerMax = 0;
  serial = "";
  brand = "";
  model = "";
  hmiVersion = "";
  acpwVersion = "";
  modbusController = new ModbusController("127.0.0.1", 502);
  messageController = new MessageController("MODBUSTCP");

  readVfactoryDb();
  readAgentDb();
  readSystemDb();
  readWebconfigDb();

  // logDebug("serial: %s\n",serial.c_str());
  // logDebug("chargePointId: %s\n", chargePointId.c_str());
  // logDebug("model: %s\n",model.c_str());
  // logDebug("brand: %s\n",brand.c_str());
  // logDebug("hmiVersion: %s\n",hmiVersion.c_str());
  // logDebug("acpwVersion: %s\n",acpwVersion.c_str());
  // logDebug("ChargeStationStatus: %d\n",status);
  // logDebug("phaseType: %d\n",phaseType);
  // logDebug("powerOptimizer: %d\n",powerOptimizer);
  // logDebug("powerOptimizerMin: %d\n",powerOptimizerMin);
  // logDebug("powerOptimizerMax: %d\n",powerOptimizerMax);
  // logDebug("ChargePointStatus: %d\n",chargePoint.status);
  // logDebug("pilotState: %d\n",chargePoint.pilotState);
  // logDebug("proximityPilotState: %d\n",chargePoint.proximityPilotState);
  // logDebug("vendorErrorCode: %d\n",chargePoint.vendorErrorCode);
  // logDebug("voltageP1: %d\n",chargePoint.voltageP1);
  // logDebug("voltageP2: %d\n",chargePoint.voltageP2);
  // logDebug("voltageP3: %d\n",chargePoint.voltageP3);
  // logDebug("currentP1: %d\n",chargePoint.currentP1);
  // logDebug("currentP2: %d\n",chargePoint.currentP2);
  // logDebug("currentP3: %d\n",chargePoint.currentP3);
  // logDebug("activePowerP1: %d\n",chargePoint.activePowerP1);
  // logDebug("activePowerP2: %d\n",chargePoint.activePowerP2);
  // logDebug("activePowerP3: %d\n",chargePoint.activePowerP3);
  // logDebug("activeEnergyP1: %d\n",chargePoint.activeEnergyP1);
  // logDebug("activeEnergyP2: %d\n",chargePoint.activeEnergyP2);
  // logDebug("activeEnergyP3: %d\n",chargePoint.activeEnergyP3);
  // logDebug("availability: %d\n",chargePoint.availability);
  // logDebug("minCurrent: %d\n",chargePoint.minCurrent);
  // logDebug("maxCurrent: %d\n",chargePoint.maxCurrent);
  // logDebug("availableCurrent: %d\n",chargePoint.availableCurrent);
  // logDebug("authorizationStatus: %d\n",chargePoint.authorizationStatus);
  // logDebug("ChargeSessionStatus: %d\n",chargePoint.chargeSession.status);
  // logDebug("startTime: %d\n",chargePoint.chargeSession.startTime);
  // logDebug("stopTime: %d\n",chargePoint.chargeSession.stopTime);
  // logDebug("initialEnergy: %d\n",chargePoint.chargeSession.initialEnergy);
  // logDebug("lastEnergy: %d\n",chargePoint.chargeSession.lastEnergy);
  // logNotice("initialized charge station\n");
  this->modbusController->set_serial(serial);
  this->modbusController->set_equipment_state(status, chargePoint.status);
  this->modbusController->set_cable_state(chargePoint.pilotState, chargePoint.proximityPilotState);
  this->modbusController->set_charge_session(chargePoint.chargeSession.startTime,
        chargePoint.chargeSession.stopTime, chargePoint.chargeSession.initialEnergy,
        chargePoint.chargeSession.lastEnergy, chargePoint.chargeSession.status);
  this->modbusController->set_brand(brand);
  this->modbusController->set_model(model);
  this->modbusController->set_phase(phaseType);
  this->modbusController->set_firmware_version(hmiVersion, acpwVersion);
  this->modbusController->set_chargepoint_id(chargePointId);
  this->modbusController->set_cable_state(chargePoint.pilotState, chargePoint.proximityPilotState);
  this->modbusController->set_chargepoint_states(
        chargePoint.status, chargePoint.vendorErrorCode, chargePoint.pilotState);
  this->modbusController->set_meter_values(chargePoint.activeEnergyP1,
        chargePoint.currentP1, chargePoint.currentP2, chargePoint.currentP3,
        chargePoint.activePowerP1, chargePoint.activePowerP2, chargePoint.activePowerP3,
        chargePoint.voltageP1, chargePoint.voltageP2, chargePoint.voltageP3);

  std::thread sessionThread(&ChargeStation::updateChargeSession, this);
  sessionThread.detach();
}

void ChargeStation::readAgentDb()
{
  sqlite3 *db;
  char *zErrMsg = 0;
  int rc;
  std::string query =
      "SELECT chargeStation.phaseType,chargeStation.powerOptimizer,chargeStation.powerOptimizerMin,"
      "chargeStation.powerOptimizerMax,deviceDetails.acpwSerialNumber, deviceDetails.acpwVersion "
      "FROM chargeStation INNER JOIN deviceDetails USING(ID)";
  rc = sqlite3_open(AGENT_DB_PATH, &db);

  if (rc != SQLITE_OK)
  {
    logErr("Can't open database: %s %s\n", AGENT_DB_PATH, sqlite3_errmsg(db));
  }
  else
  {
    int check = sqlite3_exec(db, query.c_str(), agent_callback, this, &zErrMsg);
    if (check != SQLITE_OK)
    {
      logErr("sql exec error: %s\n", sqlite3_errmsg(db));
    }
  }
  sqlite3_close(db);
}

void ChargeStation::readSystemDb()
{
  sqlite3 *db;
  char *zErrMsg = 0;
  int rc;
  std::string query =
      "SELECT hmiVersion FROM deviceInfo WHERE ID=1";
  rc = sqlite3_open(SYSTEM_DB_PATH, &db);

  if (rc != SQLITE_OK)
  {
    logErr("Can't open database: %s %s\n", SYSTEM_DB_PATH, sqlite3_errmsg(db));
  }
  else
  {
    int check = sqlite3_exec(db, query.c_str(), system_callback, this, &zErrMsg);
    if (check != SQLITE_OK)
    {
      logErr("sql exec error: %s\n", sqlite3_errmsg(db));
    }
  }
  sqlite3_close(db);
}

void ChargeStation::readVfactoryDb()
{
  sqlite3 *db;
  char *zErrMsg = 0;
  int rc;
  std::string query =
      "SELECT model,customer FROM deviceDetails WHERE id=1";
  rc = sqlite3_open(VFACTORY_DB_PATH, &db);

  if (rc != SQLITE_OK)
  {
    logErr("Can't open database: %s %s\n", VFACTORY_DB_PATH, sqlite3_errmsg(db));
  }
  else
  {
    int check = sqlite3_exec(db, query.c_str(), vfactory_callback, this, &zErrMsg);
    if (check != SQLITE_OK)
    {
      logErr("sql exec error: %s\n", sqlite3_errmsg(db));
    }
  }
  sqlite3_close(db);
}

void ChargeStation::readWebconfigDb()
{
  sqlite3 *db;
  char *zErrMsg = 0;
  int rc;
  std::string query =
      "SELECT chargePointId FROM ocppSettings WHERE ID=1";
  rc = sqlite3_open(WEBCONFIG_DB_PATH, &db);

  if (rc != SQLITE_OK)
  {
    logErr("Can't open database: %s %s\n", WEBCONFIG_DB_PATH, sqlite3_errmsg(db));
  }
  else
  {
    int check = sqlite3_exec(db, query.c_str(), webconfig_callback, this, &zErrMsg);
    if (check != SQLITE_OK)
    {
      logErr("sql exec error: %s\n", sqlite3_errmsg(db));
    }
  }
  sqlite3_close(db);
}

ChargeStation::~ChargeStation()
{
  delete messageController;
  delete modbusController;
}

void ChargeStation::updateStation(json msg)
{
  std::string type;
  if (msg["type"].is_string())
  {
    msg.at("type").get_to(type);
    // logDebug("received: %s\n", msg.dump().c_str());
    if (type.compare("StatusNotification") == 0)
    {
      chargePoint.getStatusNotification(msg);
      this->modbusController->set_chargepoint_states(
          chargePoint.status, chargePoint.vendorErrorCode, chargePoint.pilotState);
      this->modbusController->set_equipment_state(status, chargePoint.status);
    }
    else if (type.compare("MeterValues") == 0)
    {
      chargePoint.getMeterValues(msg);
      this->modbusController->set_meter_values(chargePoint.activeEnergyP1,
        chargePoint.currentP1, chargePoint.currentP2, chargePoint.currentP3,
        chargePoint.activePowerP1, chargePoint.activePowerP2, chargePoint.activePowerP3,
        chargePoint.voltageP1, chargePoint.voltageP2, chargePoint.voltageP3);
    }
    else if (type.compare("pilotState") == 0 || type.compare("proximityState") == 0)
    {
      chargePoint.getPilotStates(msg);
      this->modbusController->set_cable_state(chargePoint.pilotState, chargePoint.proximityPilotState);
    }
    else if (type.compare("ChargeStationStatusNotification") == 0)
    {
      getStatusNotification(msg);
      this->modbusController->set_equipment_state(status, chargePoint.status);
    }
    else if (type.compare("ChargeSessionStatus") == 0)
    {
      chargePoint.chargeSession.getChargeSession(msg);
      this->modbusController->set_charge_session(chargePoint.chargeSession.startTime, chargePoint.chargeSession.stopTime,
        chargePoint.chargeSession.initialEnergy, chargePoint.chargeSession.lastEnergy, chargePoint.chargeSession.status);
    }
    else if (type.compare("serialNumber") == 0)
    {
      getSerial(msg);
      this->modbusController->set_serial(serial);
    }
    else if (type.compare("phaseType") == 0)
    {
      getPhase(msg);
      this->modbusController->set_phase(phaseType);
    }
    else if (type.compare("powerOptimizer") == 0)
    {
      getPowerOptimizer(msg);
    }
    else if (type.compare("powerOptimizerLimits") == 0)
    {
      getPowerOptimizerLimits(msg);
    }
    else if (type.compare("ocppUpdate") == 0)
    {
      readWebconfigDb();
      this->modbusController->set_chargepoint_id(chargePointId);
    }
    else if (type.compare("AuthorizationStatus") == 0)
    {
      chargePoint.getAuthorizationStatus(msg);
    }
  }
  else
  {
    // logWarning("received invalid msg type\n");
  }
}

void ChargeStation::updateChargeSession()
{
  time_t currentTime;
  int duration;
  while (1)
  {
    if (chargePoint.chargeSession.status != ChargeSessionStatus::Stopped)
    {
      currentTime = time(0);
      modbusController->set_session_energy(chargePoint.activeEnergyP1 + chargePoint.activeEnergyP2 + chargePoint.activeEnergyP3 - chargePoint.chargeSession.initialEnergy);
      duration = currentTime - chargePoint.chargeSession.startTime;
      modbusController->set_session_duration(duration);
    }
    sleep(1);
  }
}

void ChargeStation::getStatusNotification(json msg)
{
  std::string status;
  msg.at("status").get_to(status);
  auto it = chargeStationStatusTable.find(status);
  this->status = it->second;
}

void ChargeStation::getSerial(json msg)
{
  msg.at("data").at("value").get_to(serial);
}

void ChargeStation::getPhase(json msg)
{
  msg.at("data").at("value").get_to(phaseType);
}

void ChargeStation::getPowerOptimizer(json msg)
{
  msg.at("data").at("value").get_to(powerOptimizer);
}

void ChargeStation::getPowerOptimizerLimits(json msg)
{
  msg.at("data").at("min").get_to(powerOptimizerMin);
  msg.at("data").at("max").get_to(powerOptimizerMax);
}

void ChargeStation::start()
{
  std::string msg;
  json json;
  std::thread modbusListener(&ModbusController::listen, modbusController);
  modbusListener.detach();

  while (1)
  {
    msg = this->messageController->receive();
    json = this->messageController->parse(msg);
    updateStation(json);
    json.clear();
  }
}

ChargePoint::ChargePoint()
{
  status = ChargePointStatus::Available;
  authorizationStatus = AuthorizationStatus::Finish;
  vendorErrorCode = 0;
  pilotState = 0;
  proximityPilotState = 1;
  voltageP1 = 0;
  voltageP2 = 0;
  voltageP3 = 0;
  currentP1 = 0;
  currentP2 = 0;
  currentP3 = 0;
  activePowerP1 = 0;
  activePowerP2 = 0;
  activePowerP3 = 0;
  activeEnergyP1 = 0;
  activeEnergyP2 = 0;
  activeEnergyP3 = 0;
  availability = ChargePointAvailability::Operative;
  minCurrent = 0;
  maxCurrent = 0;
  availableCurrent = 0;

  sqlite3 *db;
  char *zErrMsg = 0;
  int rc;
  std::string query =
      "SELECT controlPilotState,proximityPilotState,status,vendorErrorCode,voltageP1,"
      "voltageP2,voltageP3,currentP1,currentP2,currentP3,activePowerP1,"
      "activePowerP2,activePowerP3,activeEnergyP1,activeEnergyP2,activeEnergyP3,"
      "availability,minCurrent,maxCurrent,availableCurrent "
      "FROM chargePoints WHERE chargePointId=1";
  rc = sqlite3_open(AGENT_DB_PATH, &db);

  if (rc != SQLITE_OK)
  {
    logErr("Can't open database: %s %s\n", AGENT_DB_PATH, sqlite3_errmsg(db));
  }
  else
  {
    int check = sqlite3_exec(db, query.c_str(), callback, this, &zErrMsg);
    if (check != SQLITE_OK)
    {
      logErr("sql exec error: %s\n", sqlite3_errmsg(db));
    }
  }
  sqlite3_close(db);
}

void ChargePoint::getAuthorizationStatus(json msg)
{
  std::string status;
  msg.at("status").get_to(status);
  auto it = authorizationStatusTable.find(status);
  this->authorizationStatus = it->second;
}

void ChargePoint::getStatusNotification(json msg)
{
  std::string status;
  msg.at("status").get_to(status);
  auto it = chargePointStatusTable.find(status);
  this->status = it->second;
  msg.at("vendorErrorCode").get_to(vendorErrorCode);
}

void ChargePoint::getPilotStates(json msg)
{
  std::string type;
  int value;
  msg.at("type").get_to(type);
  msg.at("data").at("value").get_to(value);
  if (type.compare("pilotState") == 0)
  {
    pilotState = value;
  }
  else if(type.compare("proximityState") == 0)
  {
    proximityPilotState = value;
  }
}

void ChargePoint::getMeterValues(json msg)
{
  auto const meterValue = msg.find("meterValue");
  for (auto const& node1 : *meterValue)
    {
      auto const sampledValue = node1.find("sampledValue");
      for (auto const& node2 : *sampledValue)
        {
          std::string measurand;
          std::string value;
          std::string phase;
          node2.at("measurand").get_to(measurand);
          if (measurand.compare("Energy.Active.Import.Register") == 0)
          {
            node2.at("value").get_to(value);
            activeEnergyP1 = atoi(value.c_str());
            // logDebug("activeEnergyP1: %d\n",activeEnergyP1);
          }
          else{
            node2.at("phase").get_to(phase);
            if (measurand.compare("Current.Import") == 0)
              {
                if (phase.compare("L1") == 0)
                {
                  node2.at("value").get_to(value);
                  currentP1 = atoi(value.c_str());
                  // logDebug("currentP1: %d\n",currentP1);
                }
                else if (phase.compare("L2") == 0)
                {
                  node2.at("value").get_to(value);
                  currentP2 = atoi(value.c_str());
                  // logDebug("currentP2: %d\n",currentP2);
                }
                else if (phase.compare("L3") == 0)
                {
                  node2.at("value").get_to(value);
                  currentP3 = atoi(value.c_str());
                  // logDebug("currentP3: %d\n",currentP3);
                }
              }
              else if (measurand.compare("Power.Active.Import") == 0)
              {
                if (phase.compare("L1") == 0)
                {
                  node2.at("value").get_to(value);
                  activePowerP1 = atoi(value.c_str());
                  // logDebug("activePowerP1: %d\n",activePowerP1);
                }
                else if (phase.compare("L2") == 0)
                {
                  node2.at("value").get_to(value);
                  activePowerP2 = atoi(value.c_str());
                  // logDebug("activePowerP2: %d\n",activePowerP2);
                }
                else if (phase.compare("L3") == 0)
                {
                  node2.at("value").get_to(value);
                  activePowerP3 = atoi(value.c_str());
                  // logDebug("activePowerP3: %d\n",activePowerP3);
                }
              }
              else if (measurand.compare("Voltage") == 0)
              {
                if (phase.compare("L1") == 0)
                {
                  node2.at("value").get_to(value);
                  voltageP1 = atoi(value.c_str());
                  // logDebug("voltageP1: %d\n",voltageP1);
                }
                else if (phase.compare("L2") == 0)
                {
                  node2.at("value").get_to(value);
                  voltageP2 = atoi(value.c_str());
                  // logDebug("voltageP2: %d\n",voltageP2);
                }
                else if (phase.compare("L3") == 0)
                {
                  node2.at("value").get_to(value);
                  voltageP3 = atoi(value.c_str());
                  // logDebug("voltageP3: %d\n",voltageP3);
                }
              }
            }
        }
    }
}
