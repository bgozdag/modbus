#ifndef MODBUSCONTROLLER_HPP
#define MODBUSCONTROLLER_HPP

#include "enum.hpp"
#include "modbus.h"
#include "log.h"
#include <unistd.h>
#include <math.h>
#include <sstream>
#include <thread>
#include <string>
#include <ctime>

#define MAX_CONNECTION 1

#define SERIAL_NUMBER_REG 100
#define CHARGEPOINT_ID_REG 130
#define BRAND_REG 190
#define MODEL_REG 210
#define FIRMWARE_VERSION_REG 230
#define DATE_REG 290
#define TIME_REG 294
#define CHARGEPOINT_POWER_REG 400
#define NUMBER_OF_PHASES_REG 404
#define CHARGEPOINT_STATE_REG 1000
#define CHARGING_STATE_REG 1001
#define EQUIPMENT_STATE_REG 1002
#define CABLE_STATE_REG 1004
#define EVSE_FAULT_CODE_REG 1006
#define CURRENT_L1_REG 1008
#define CURRENT_L2_REG 1010
#define CURRENT_L3_REG 1012
#define VOLTAGE_L1_REG 1014
#define VOLTAGE_L2_REG 1016
#define VOLTAGE_L3_REG 1018
#define ACTIVE_POWER_TOTAL_REG 1020
#define ACTIVE_POWER_L1_REG 1024
#define ACTIVE_POWER_L2_REG 1028
#define ACTIVE_POWER_L3_REG 1032
#define METER_READING_REG 1036
#define SESSION_MAX_CURRENT_REG 1100
#define EVSE_MIN_CURRENT_REG 1102
#define EVSE_MAX_CURRENT_REG 1104
#define CABLE_MAX_CURRENT_REG 1106
#define SESSION_ENERGY_REG 1502
#define SESSION_START_TIME_REG 1504
#define SESSION_DURATION_REG 1508
#define SESSION_END_TIME 1512
class ModbusController
{
public:
  ModbusController(std::string host, int port);
  ~ModbusController();
  void update_datetime();
  void set_time(int currentTime);
  void set_date(int currentDate);
  void set_chargepoint_states(ChargePointStatus state, int vendorErrorCode, int pilotState);
  void set_equipment_state(ChargeStationStatus stationStatus, ChargePointStatus pointStatus);
  void set_meter_values(int energy, int currentP1, int currentP2, int currentP3, int powerP1, int powerP2, int powerP3, int voltageP1, int voltageP2, int voltageP3);
  void set_evse_min_current(int current);
  void set_evse_max_current(int current);
  void set_cable_max_current(int current);
  void set_session_max_current(int current);
  void set_serial(std::string serial);
  void set_brand(std::string brand);
  void set_model(std::string model);
  void set_phase(int phase);
  void set_charge_session(int startTime, int stopTime, int initialEnergy, int lastEnergy, ChargeSessionStatus status);
  void set_firmware_version(std::string hmiVersion, std::string acpwVersion);
  void set_cable_state(int pilotState, int proximityState);
  void set_session_duration(int duration);
  void set_session_energy(int energy);
  void set_chargepoint_id(std::string id);
  void listen();

private:
  void set_r_register(uint16_t data, int addr);
  void set_rw_register(uint16_t data, int addr);
  void set_r_register(uint32_t data, int addr);
  void set_rw_register(uint32_t data, int addr);
  void set_r_register(std::string data, int addr);
  void set_rw_register(std::string data, int addr);

  modbus_t *context;
  modbus_mapping_t *map;
  std::string host;
  int port;
};

#endif
