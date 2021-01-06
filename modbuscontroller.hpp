#ifndef MODBUSCONTROLLER_HPP
#define MODBUSCONTROLLER_HPP

#include <string>
#include "modbus.h"
#include "enum.hpp"

#define MAX_CONNECTION 1
#define CHARGEPOINT_STATE_REG 1000
#define CHARGING_STATE_REG 1001
#define CABLE_STATE_REG 1004
#define EVSE_FAULT_CODE_REG 1006

class ModbusController{
    public:
        ModbusController(std::string host, int port);
        ~ModbusController();
        void listen();
        void set_chargepoint_states(ChargePointStatus state, int vendorErrorCode);
    private:
        void set_r_register(int addr, uint16_t data);
        void set_rw_register(int addr, uint16_t data);
        modbus_t *context;
        modbus_mapping_t *map;
        std::string host;
        int port;
};

#endif