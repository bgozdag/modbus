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

ChargeStation::ChargeStation()
{
  status = ChargeStationStatus::Initializing;
  phaseType = 0;
  powerOptimizer = 0;
  powerOptimizerMin = 0;
  powerOptimizerMax = 0;
  serial = "";
  brand = "";
  model = "";
  fwVersion = "";
  modbusController = new ModbusController("127.0.0.1", 502);
  messageController = new MessageController("modbus");

  sqlite3 *db;
  char *zErrMsg = 0;
  int rc;
  std::string query =
      "SELECT chargeStation.phaseType,chargeStation.powerOptimizer,chargeStation.powerOptimizerMin,"
      "chargeStation.powerOptimizerMax,deviceDetails.acpwSerialNumber "
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

  query =
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

  query =
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

  logDebug("serial: %s\n",serial.c_str());
  logDebug("model: %s\n",model.c_str());
  logDebug("brand: %s\n",brand.c_str());
  logDebug("fwVersion: %s\n",fwVersion.c_str());
  logDebug("ChargeStationStatus: %d\n",status);
  logDebug("phaseType: %d\n",phaseType);
  logDebug("powerOptimizer: %d\n",powerOptimizer);
  logDebug("powerOptimizerMin: %d\n",powerOptimizerMin);
  logDebug("powerOptimizerMax: %d\n",powerOptimizerMax);
  logDebug("ChargePointStatus: %d\n",chargePoint.status);
  logDebug("proximityPilotState: %d\n",chargePoint.proximityPilotState);
  logDebug("vendorErrorCode: %d\n",chargePoint.vendorErrorCode);
  logDebug("voltageP1: %d\n",chargePoint.voltageP1);
  logDebug("voltageP2: %d\n",chargePoint.voltageP2);
  logDebug("voltageP3: %d\n",chargePoint.voltageP3);
  logDebug("currentP1: %d\n",chargePoint.currentP1);
  logDebug("currentP2: %d\n",chargePoint.currentP2);
  logDebug("currentP3: %d\n",chargePoint.currentP3);
  logDebug("activePowerP1: %d\n",chargePoint.activePowerP1);
  logDebug("activePowerP2: %d\n",chargePoint.activePowerP2);
  logDebug("activePowerP3: %d\n",chargePoint.activePowerP3);
  logDebug("activeEnergyP1: %d\n",chargePoint.activeEnergyP1);
  logDebug("activeEnergyP2: %d\n",chargePoint.activeEnergyP2);
  logDebug("activeEnergyP3: %d\n",chargePoint.activeEnergyP3);
  logDebug("availability: %d\n",chargePoint.availability);
  logDebug("minCurrent: %d\n",chargePoint.minCurrent);
  logDebug("maxCurrent: %d\n",chargePoint.maxCurrent);
  logDebug("availableCurrent: %d\n",chargePoint.availableCurrent);
  logDebug("authorizationStatus: %d\n",chargePoint.authorizationStatus);
  logDebug("ChargeSessionStatus: %d\n",chargePoint.chargeSession.status);
  logDebug("startTime: %d\n",chargePoint.chargeSession.startTime);
  logDebug("stopTime: %d\n",chargePoint.chargeSession.stopTime);
  logDebug("initialEnergy: %d\n",chargePoint.chargeSession.initialEnergy);
  logDebug("lastEnergy: %d\n",chargePoint.chargeSession.lastEnergy);
  logNotice("initialized charge station\n");
}

ChargeStation::~ChargeStation()
{
  delete messageController;
  delete modbusController;
}

void ChargeStation::updateStation(nlohmann::json msg)
{
  std::string type;
  if (msg["type"].is_string())
  {
    msg.at("type").get_to(type);
    logInfo("received: %s\n", type.c_str());
    if (type.compare("StatusNotification") == 0)
    {
      chargePoint.getStatusNotification(msg);
      this->modbusController->set_chargepoint_states(
          chargePoint.status, chargePoint.vendorErrorCode);
    }
  }
  else
  {
    logWarning("received invalid msg type\n");
  }
}

void ChargeStation::start()
{
  std::string msg;
  nlohmann::json json;
  std::thread modbusListener(&ModbusController::listen, modbusController);

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
  proximityPilotState = 0;
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
      "SELECT proximityPilotState,status,vendorErrorCode,voltageP1,"
      "voltageP2,voltageP3,currentP1,currentP2,currentP3,activePowerP1,"
      "activePowerP2,activePowerP3,activeEnergyP1,activeEnergyP2,activeEnergyP3,"
      "availability,minCurrent,maxCurrent,availableCurrent,authorizationStatus "
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

void ChargePoint::getStatusNotification(nlohmann::json msg)
{
  std::string status;
  msg.at("status").get_to(status);
  auto it = chargePointStatusTable.find(status);
  status = it->second;
  msg.at("vendorErrorCode").get_to(vendorErrorCode);
}
