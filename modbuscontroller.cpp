#include "modbuscontroller.hpp"

ModbusController::ModbusController(MessageController *mc)
{
  host = "127.0.0.1";
  port = 502;
  context = modbus_new_tcp(host.c_str(), port);
  this->messageController = mc;
  map = modbus_mapping_new(0, 0, 6001, 1514);
  if (map == NULL)
  {
    logEmerg("failed to allocate the map: %s\n", modbus_strerror(errno));
    modbus_free(context);
    return;
  }
  logNotice("initialized modbus map\n");
  std::thread datetimeThread(&ModbusController::updateDatetime, this);
  datetimeThread.detach();
}

ModbusController::~ModbusController()
{
  modbus_mapping_free(map);
  modbus_close(context);
  modbus_free(context);
}

void ModbusController::listen()
{
  while (1)
  {
    int s = -1;
    s = modbus_tcp_listen(context, MAX_CONNECTION);
    logNotice("listening to modbus socket: %s:%d\n", host.c_str(), port);
    modbus_tcp_accept(context, &s);
    logNotice("accepted connection\n");

    while (1)
    {
      uint8_t query[MODBUS_TCP_MAX_ADU_LENGTH];
      int rc;

      rc = modbus_receive(context, query);
      if (rc > 0)
      {
        // rc is the query size
        modbus_reply(context, query, rc, map);
        parseTcpMessage(query);

        // logDebug("rc: %d\n", rc);
        // for(int i=0;i<rc;i++)
        // {
        //   logDebug("%d\n", query[i]);
        // }
      }
      else if (rc == -1)
      {
        // Connection closed by the client or error
        break;
      }
    }
    logNotice("closed connection: %s\n", modbus_strerror(errno));
    if (s != -1)
    {
      close(s);
    }
  }
}

void ModbusController::parseTcpMessage(uint8_t data[])
{
  int i=0;
  msg.transactionIdentifier = data[i++] * 256 + data[i++];
  msg.protocolIdentifier = data[i++] * 256 + data[i++];
  msg.messageLength = data[i++] * 256 + data[i++];
  msg.unitIdentifier = data[i++];
  msg.functionCode = data[i++];
  // logNotice("function: %d\n", msg.functionCode);

  if (msg.functionCode == 6)
  {
    msg.address = data[i++] * 256 + data[i++];
    // logNotice("address: %d\n", msg.address);
    if (msg.address == FAILSAFE_CURRENT_REG)
    {
      messageController->sendFailsafeCurrent(this->map->tab_registers[FAILSAFE_CURRENT_REG]);
    }
    else if (msg.address == FAILSAFE_TIMEOUT_REG)
    {
      messageController->sendFailsafeTimeout(this->map->tab_registers[FAILSAFE_TIMEOUT_REG]);
    }
    else if (msg.address == CHARGING_CURRENT_REG)
    {
      messageController->sendModbusTcpCurrent(this->map->tab_registers[CHARGING_CURRENT_REG]);
    }
  }
  else if (msg.functionCode == 23)
  {
    i += 4;
    msg.address = data[i++] * 256 + data[i++];
    // logNotice("address: %d\n", msg.address);
    if (msg.address == FAILSAFE_CURRENT_REG)
    {
      messageController->sendFailsafeCurrent(this->map->tab_registers[FAILSAFE_CURRENT_REG]);
    }
    else if (msg.address == FAILSAFE_TIMEOUT_REG)
    {
      messageController->sendFailsafeTimeout(this->map->tab_registers[FAILSAFE_TIMEOUT_REG]);
    }
    else if (msg.address == CHARGING_CURRENT_REG)
    {
      messageController->sendModbusTcpCurrent(this->map->tab_registers[CHARGING_CURRENT_REG]);
    }
  }
  else if (msg.functionCode == 16)
  {
    msg.address = data[i++] * 256 + data[i++];
    // logNotice("address: %d\n", msg.address);
    msg.nb = data[i++] * 256 + data[i++];
    if (msg.address <= FAILSAFE_CURRENT_REG && msg.address + msg.nb >= FAILSAFE_CURRENT_REG)
    {
      messageController->sendFailsafeCurrent(this->map->tab_registers[FAILSAFE_CURRENT_REG]);
    }
    else if (msg.address <= FAILSAFE_TIMEOUT_REG && msg.address + msg.nb >= FAILSAFE_TIMEOUT_REG)
    {
      messageController->sendFailsafeTimeout(this->map->tab_registers[FAILSAFE_TIMEOUT_REG]);
    }
    else if (msg.address <= CHARGING_CURRENT_REG && msg.address + msg.nb >= CHARGING_CURRENT_REG)
    {
      messageController->sendModbusTcpCurrent(this->map->tab_registers[CHARGING_CURRENT_REG]);
    }
  }
}

void ModbusController::setChargepointStates(ChargePointStatus state,
                                              int vendorErrorCode, int pilotState)
{
  if (state == ChargePointStatus::Available)
  {
    set_r_register(uint16_t(0), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(0), CHARGING_STATE_REG);
  }
  else if (state == ChargePointStatus::Preparing)
  {
    set_r_register(uint16_t(1), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(0), CHARGING_STATE_REG);
  }
  else if (state == ChargePointStatus::Charging)
  {
    set_r_register(uint16_t(2), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(1), CHARGING_STATE_REG);
  }
  else if (state == ChargePointStatus::SuspendedEVSE)
  {
    set_r_register(uint16_t(3), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(0), CHARGING_STATE_REG);
  }
  else if (state == ChargePointStatus::SuspendedEV)
  {
    set_r_register(uint16_t(4), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(0), CHARGING_STATE_REG);
  }
  else if (state == ChargePointStatus::Finishing)
  {
    set_r_register(uint16_t(5), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(0), CHARGING_STATE_REG);
  }
  else if (state == ChargePointStatus::Reserved)
  {
    set_r_register(uint16_t(6), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(0), CHARGING_STATE_REG);
  }
  else if (state == ChargePointStatus::Unavailable)
  {
    set_r_register(uint16_t(7), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(0), CHARGING_STATE_REG);
  }
  else if (state == ChargePointStatus::Faulted)
  {
    set_r_register(uint16_t(8), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(0), CHARGING_STATE_REG);
  }
  set_r_register(uint16_t(vendorErrorCode), EVSE_FAULT_CODE_REG);
}

void ModbusController::setCableMaxCurrent(int current)
{
  set_r_register(uint16_t(current), CABLE_MAX_CURRENT_REG);
}

void ModbusController::setSessionMaxCurrent(int current)
{
  set_r_register(uint16_t(current), SESSION_MAX_CURRENT_REG);
}

void ModbusController::setEvseMaxCurrent(int current)
{
  set_r_register(uint16_t(current), EVSE_MAX_CURRENT_REG);
  set_r_register(uint32_t(230 * current), CHARGEPOINT_POWER_REG);
}

void ModbusController::setEvseMinCurrent(int current)
{
  set_r_register(uint16_t(current), EVSE_MIN_CURRENT_REG);
}

void ModbusController::setFailsafeCurrent(int current)
{
  set_rw_register(uint16_t(current), FAILSAFE_CURRENT_REG);
}

void ModbusController::setFailsafeTimeout(int time)
{
  set_rw_register(uint16_t(time), FAILSAFE_TIMEOUT_REG);
}

void ModbusController::setChargingCurrent(int time)
{
  set_rw_register(uint16_t(time), CHARGING_CURRENT_REG);
}

void ModbusController::setAliveRegister()
{
  set_rw_register(uint16_t(0), ALIVE_REGISTER);
}

void ModbusController::set_r_register(uint32_t data, int addr)
{
  uint16_t arr[2];
  memcpy(arr, &data, sizeof(data));
  arr[0] = data >> 16;
  arr[1] = data;
  for (int i = 0; i < 2; i++)
  {
    if (map->tab_input_registers[addr] != arr[i])
    {
      map->tab_input_registers[addr] = arr[i];
      if (addr != 295)
      {
        logNotice("set r reg[%d] : %d\n", addr, map->tab_input_registers[addr]);
      }
    }
    addr++;
  }
}

void ModbusController::set_rw_register(uint32_t data, int addr)
{
  uint16_t arr[2];
  memcpy(arr, &data, sizeof(data));
  arr[0] = data >> 16;
  arr[1] = data;
  for (int i = 0; i < 2; i++)
  {
    if (map->tab_registers[addr] != arr[i])
    {
      map->tab_registers[addr] = arr[i];
      logNotice("set r reg[%d] : %d\n", addr, map->tab_registers[addr]);
    }
    addr++;
  }
}

void ModbusController::set_r_register(std::string data, int addr)
{
  for (int i = 0; i < data.length(); i++)
  {
    uint16_t temp = (uint16_t)data.at(i);
    if (map->tab_input_registers[addr] != temp)
    {
      map->tab_input_registers[addr] = temp;
      logNotice("set r reg[%d] : %d\n", addr, map->tab_input_registers[addr]);
    }
    addr++;
  }
}

void ModbusController::set_rw_register(std::string data, int addr)
{

  for (int i = 0; i < data.length(); i++)
  {
    uint16_t temp = (uint16_t)data.at(i);
    if (map->tab_registers[addr] != temp)
    {
      map->tab_registers[addr] = temp;
      logNotice("set r reg[%d] : %d\n", addr, map->tab_registers[addr]);
    }
    addr++;
  }
}

void ModbusController::set_r_register(uint16_t data, int addr)
{
  if (map->tab_input_registers[addr] != data)
  {
    map->tab_input_registers[addr] = data;
    logNotice("set r reg[%d] : %d\n", addr, map->tab_input_registers[addr]);
  }
}

void ModbusController::set_rw_register(uint16_t data, int addr)
{
  if (map->tab_registers[addr] != data)
  {
    map->tab_registers[addr] = data;
    logNotice("set rw reg[%d] : %d\n", addr, map->tab_registers[addr]);
  }
}

void ModbusController::setEquipmentState(ChargeStationStatus stationStatus, ChargePointStatus pointStatus)
{
  if (stationStatus == ChargeStationStatus::Initializing)
  {
    set_r_register(uint16_t(0), EQUIPMENT_STATE_REG);
  }
  else if (pointStatus == ChargePointStatus::Faulted)
  {
    set_r_register(uint16_t(2), EQUIPMENT_STATE_REG);
  }
  else if (stationStatus == ChargeStationStatus::InstallingFirmware)
  {
    set_r_register(uint16_t(4), EQUIPMENT_STATE_REG);
  }
  else if (pointStatus == ChargePointStatus::Unavailable)
  {
    set_r_register(uint16_t(3), EQUIPMENT_STATE_REG);
  }
  else
  {
    set_r_register(uint16_t(1), EQUIPMENT_STATE_REG);
  }
}

void ModbusController::setMeterValues(int energy, int currentP1, int currentP2, int currentP3, int powerP1, int powerP2, int powerP3, int voltageP1, int voltageP2, int voltageP3)
{
  set_r_register(uint32_t(round((float)energy / 10000.0)), METER_READING_REG);
  set_r_register(uint16_t(currentP1), CURRENT_L1_REG);
  set_r_register(uint16_t(currentP2), CURRENT_L2_REG);
  set_r_register(uint16_t(currentP3), CURRENT_L3_REG);
  set_r_register(uint16_t(round((float)voltageP1 / 1000.0)), VOLTAGE_L1_REG);
  set_r_register(uint16_t(round((float)voltageP2 / 1000.0)), VOLTAGE_L2_REG);
  set_r_register(uint16_t(round((float)voltageP3 / 1000.0)), VOLTAGE_L3_REG);
  set_r_register(uint32_t(powerP1), ACTIVE_POWER_L1_REG);
  set_r_register(uint32_t(powerP2), ACTIVE_POWER_L2_REG);
  set_r_register(uint32_t(powerP3), ACTIVE_POWER_L3_REG);
  set_r_register(uint32_t(powerP1 + powerP2 + powerP3), ACTIVE_POWER_TOTAL_REG);
}

void ModbusController::setChargepointId(std::string id)
{
  set_r_register(id, CHARGEPOINT_ID_REG);
}

void ModbusController::setChargeSession(int startTime, int stopTime, int initialEnergy, int lastEnergy, ChargeSessionStatus status)
{
  std::stringstream ss;
  char data[3];
  int energy = lastEnergy - initialEnergy;
  setSessionEnergy(energy);
  if (startTime != 0)
  {
    time_t startEpoch = startTime;
    tm *startDateTime = localtime(&startEpoch);
    snprintf(data, 3, "%02d", startDateTime->tm_hour);
    ss << data;
    snprintf(data, 3, "%02d", startDateTime->tm_min);
    ss << data;
    snprintf(data, 3, "%02d", startDateTime->tm_sec);
    ss << data;
    set_r_register(uint32_t(atoi(ss.str().c_str())), SESSION_START_TIME_REG);
    ss.clear();
    ss.str("");
  }
  if (stopTime == 0)
  {
    set_r_register(uint32_t(0), SESSION_END_TIME);
  }
  else
  {
    time_t stopEpoch = stopTime;
    tm *stopDateTime = localtime(&stopEpoch);
    snprintf(data, 3, "%02d", stopDateTime->tm_hour);
    ss << data;
    snprintf(data, 3, "%02d", stopDateTime->tm_min);
    ss << data;
    snprintf(data, 3, "%02d", stopDateTime->tm_sec);
    ss << data;
    set_r_register(uint32_t(atoi(ss.str().c_str())), SESSION_END_TIME);
  }
}

void ModbusController::setSerial(std::string serial)
{
  set_r_register(serial, SERIAL_NUMBER_REG);
}
void ModbusController::setBrand(std::string brand)
{
  set_r_register(brand, BRAND_REG);
}

void ModbusController::setModel(std::string model)
{
  set_r_register(model, MODEL_REG);
}

void ModbusController::setPhase(int phase)
{
  set_r_register((uint16_t)phase, NUMBER_OF_PHASES_REG);
}

void ModbusController::setFirmwareVersion(std::string hmiVersion, std::string acpwVersion)
{
  set_r_register(hmiVersion + acpwVersion, FIRMWARE_VERSION_REG);
}

void ModbusController::updateDatetime()
{
  time_t currentTime;
  tm *dateTime;
  std::stringstream ss;
  char data[3];
  while (1)
  {
    currentTime = time(0);
    dateTime = localtime(&currentTime);
    snprintf(data, 3, "%02d", dateTime->tm_year - 100);
    ss << data;
    snprintf(data, 3, "%02d", dateTime->tm_mon + 1);
    ss << data;
    snprintf(data, 3, "%02d", dateTime->tm_mday);
    ss << data;
    setDate(atoi(ss.str().c_str()));
    ss.clear();
    ss.str("");
    snprintf(data, 3, "%02d", dateTime->tm_hour);
    ss << data;
    snprintf(data, 3, "%02d", dateTime->tm_min);
    ss << data;
    snprintf(data, 3, "%02d", dateTime->tm_sec);
    ss << data;
    setTime(atoi(ss.str().c_str()));
    ss.clear();
    ss.str("");
    sleep(1);
  }
}

void ModbusController::setSessionDuration(int duration)
{
  set_r_register(uint32_t(duration), SESSION_DURATION_REG);
}

void ModbusController::setSessionEnergy(int energy)
{
  set_r_register(uint32_t(energy), SESSION_ENERGY_REG);
}

void ModbusController::setTime(int currentTime)
{
  set_r_register(uint32_t(currentTime), TIME_REG);
}

void ModbusController::setDate(int currentDate)
{
  set_r_register(uint32_t(currentDate), DATE_REG);
}

void ModbusController::setCableState(int pilotState, int proximityState)
{
  if (proximityState == 1)
  {
    set_r_register(uint16_t(0), CABLE_STATE_REG);
  }
  else
  {
    if (pilotState == 0)
    {
      set_r_register(uint16_t(1), CABLE_STATE_REG);
    }
    else if (pilotState == 1)
    {
      set_r_register(uint16_t(1), CABLE_STATE_REG);
    }
    else if (pilotState == 2)
    {
      set_r_register(uint16_t(2), CABLE_STATE_REG);
    }
    else if (pilotState == 3)
    {
      set_r_register(uint16_t(3), CABLE_STATE_REG);
    }
    else if (pilotState == 4)
    {
      set_r_register(uint16_t(2), CABLE_STATE_REG);
    }
    else if (pilotState == 5)
    {
      set_r_register(uint16_t(3), CABLE_STATE_REG);
    }
  }
}