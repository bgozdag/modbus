// arm-linux-gnueabihf-gcc log.c -o log.o -c
// arm-linux-gnueabihf-g++ modbus.cpp messagecontroller.cpp modbuscontroller.cpp chargestation.cpp log.o -o modbus -lzmq -lmodbus -lpthread -L/usr/local/arm-zmq_modbus_sqlite/lib/ -std=c++11

#include "log.h"
#include "chargestation.hpp"

int main(){
    logInit("/var/log/modbus", 5);
    logNotice("initialized logging\n");
    ChargeStation chargeStation;
    chargeStation.start();
}