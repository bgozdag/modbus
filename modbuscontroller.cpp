#include "modbuscontroller.hpp"
#include "log.h"
#include <unistd.h>
#include <math.h>

ModbusController::ModbusController(std::string h, int p)
{
  host = h;
  port = p;
  context = modbus_new_tcp(host.c_str(), port);
  modbus_set_debug(context, TRUE);
  map = modbus_mapping_new(0, 0, 6000, 6000);
  if (map == NULL)
  {
    logEmerg("failed to allocate the map: %s\n", modbus_strerror(errno));
    modbus_free(context);
    return;
  }
  logNotice("initialized modbus map\n");
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

void ModbusController::set_chargepoint_states(ChargePointStatus state,
                                              int vendorErrorCode)
{
  if (state == ChargePointStatus::Available)
  {
    set_r_register(uint16_t(0), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(0), CHARGING_STATE_REG);
    set_r_register(uint16_t(0), CABLE_STATE_REG);
  }
  else if (state == ChargePointStatus::Preparing)
  {
    set_r_register(uint16_t(1), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(0), CHARGING_STATE_REG);
    set_r_register(uint16_t(1), CABLE_STATE_REG);
  }
  else if (state == ChargePointStatus::Charging)
  {
    set_r_register(uint16_t(3), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(1), CHARGING_STATE_REG);
    set_r_register(uint16_t(1), CABLE_STATE_REG);
  }
  else if (state == ChargePointStatus::SuspendedEVSE)
  {
    set_r_register(uint16_t(3), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(1), CHARGING_STATE_REG);
    set_r_register(uint16_t(1), CABLE_STATE_REG);
  }
  else if (state == ChargePointStatus::SuspendedEV)
  {
    set_r_register(uint16_t(3), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(1), CHARGING_STATE_REG);
    set_r_register(uint16_t(1), CABLE_STATE_REG);
  }
  else if (state == ChargePointStatus::Finishing)
  {
    set_r_register(uint16_t(3), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(1), CHARGING_STATE_REG);
  }
  else if (state == ChargePointStatus::Reserved)
  {
    set_r_register(uint16_t(3), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(1), CHARGING_STATE_REG);
    set_r_register(uint16_t(0), CABLE_STATE_REG);
  }
  else if (state == ChargePointStatus::Faulted)
  {
    set_r_register(uint16_t(3), CHARGEPOINT_STATE_REG);
    set_r_register(uint16_t(1), CHARGING_STATE_REG);
  }

  set_r_register(uint16_t(vendorErrorCode), EVSE_FAULT_CODE_REG);
}

void ModbusController::set_r_register(uint32_t data, int addr)
{
  uint16_t arr[2];
  memcpy(arr, &data, sizeof(data));
  arr[0] = data >> 16;
  arr[1] = data;
  for (int i = 0; i<2; i++)
  {
    if (map->tab_input_registers[addr] != arr[i])
    {
      map->tab_input_registers[addr] = arr[i];
      logNotice("set r reg[%d] : %d\n", addr, map->tab_input_registers[addr]);
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
  for (int i = 0; i<2; i++)
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
  for (int i = 0; i<data.length(); i++)
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

  for (int i = 0; i<data.length(); i++)
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

void ModbusController::set_meter_values(int energy, int currentP1, int currentP2, int currentP3, int powerP1, int powerP2, int powerP3, int voltageP1, int voltageP2, int voltageP3)
{
  set_r_register(uint16_t(round((float)currentP1 / (float)1000)), CURRENT_L1_REG);
  set_r_register(uint16_t(round((float)currentP2 / (float)1000)), CURRENT_L2_REG);
  set_r_register(uint16_t(round((float)currentP3 / (float)1000)), CURRENT_L3_REG);
  set_r_register(uint16_t(round((float)voltageP1 / (float)1000)), VOLTAGE_L1_REG);
  set_r_register(uint16_t(round((float)voltageP2 / (float)1000)), VOLTAGE_L2_REG);
  set_r_register(uint16_t(round((float)voltageP3 / (float)1000)), VOLTAGE_L3_REG);
  set_r_register(uint32_t(powerP1), ACTIVE_POWER_L1_REG);
  set_r_register(uint32_t(powerP2), ACTIVE_POWER_L2_REG);
  set_r_register(uint32_t(powerP3), ACTIVE_POWER_L3_REG);
  set_r_register(uint32_t(powerP1 + powerP2 + powerP3), ACTIVE_POWER_TOTAL_REG);
}

void ModbusController::set_serial(std::string serial)
{
  logNotice("set serial: %s\n",serial.c_str());
  set_r_register(serial, SERIAL_NUMBER_REG);
}
void ModbusController::set_brand(std::string brand)
{
  logNotice("set brand: %s\n",brand.c_str());
  set_r_register(brand, BRAND_REG);
}

void ModbusController::set_model(std::string model)
{
  logNotice("set model: %s\n",model.c_str());
  set_r_register(model, MODEL_REG);
}

void ModbusController::set_phase(int phase)
{
  logNotice("set phase number: %d\n",phase);
  set_r_register((uint16_t)phase, NUMBER_OF_PHASES_REG);
}

void ModbusController::set_firmware_version(std::string version)
{
  logNotice("set fw version: %s\n",version.c_str());
  set_r_register(version, MODEL_REG);
}
