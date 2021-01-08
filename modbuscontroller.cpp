#include "modbuscontroller.hpp"
#include "log.h"
#include <unistd.h>

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
    set_r_register(CHARGEPOINT_STATE_REG, 0);
    set_r_register(CHARGING_STATE_REG, 0);
    set_r_register(CABLE_STATE_REG, 0);
  }
  else if (state == ChargePointStatus::Preparing)
  {
    set_r_register(CHARGEPOINT_STATE_REG, 1);
    set_r_register(CHARGING_STATE_REG, 0);
    set_r_register(CABLE_STATE_REG, 1);
  }
  else if (state == ChargePointStatus::Charging)
  {
    set_r_register(CHARGEPOINT_STATE_REG, 3);
    set_r_register(CHARGING_STATE_REG, 1);
    set_r_register(CABLE_STATE_REG, 1);
  }
  else if (state == ChargePointStatus::SuspendedEVSE)
  {
    set_r_register(CHARGEPOINT_STATE_REG, 3);
    set_r_register(CHARGING_STATE_REG, 1);
    set_r_register(CABLE_STATE_REG, 1);
  }
  else if (state == ChargePointStatus::SuspendedEV)
  {
    set_r_register(CHARGEPOINT_STATE_REG, 3);
    set_r_register(CHARGING_STATE_REG, 1);
    set_r_register(CABLE_STATE_REG, 1);
  }
  else if (state == ChargePointStatus::Finishing)
  {
    set_r_register(CHARGEPOINT_STATE_REG, 3);
    set_r_register(CHARGING_STATE_REG, 1);
  }
  else if (state == ChargePointStatus::Reserved)
  {
    set_r_register(CHARGEPOINT_STATE_REG, 3);
    set_r_register(CHARGING_STATE_REG, 1);
    set_r_register(CABLE_STATE_REG, 0);
  }
  else if (state == ChargePointStatus::Faulted)
  {
    set_r_register(CHARGEPOINT_STATE_REG, 3);
    set_r_register(CHARGING_STATE_REG, 1);
  }

  set_r_register(EVSE_FAULT_CODE_REG, vendorErrorCode);
}

void ModbusController::set_r_register(int addr, uint16_t data)
{
  if (map->tab_input_registers[addr] != data)
  {
    map->tab_input_registers[addr] = data;
    logNotice("set r reg[%d] : %d\n", addr, map->tab_input_registers[addr]);
  }
}

void ModbusController::set_rw_register(int addr, uint16_t data)
{
  if (map->tab_registers[addr] != data)
  {
    map->tab_registers[addr] = data;
    logNotice("set rw reg[%d] : %d\n", addr, map->tab_registers[addr]);
  }
}
