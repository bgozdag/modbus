// arm-linux-gnueabihf-gcc log.c -o log.o -c
// arm-linux-gnueabihf-gcc sqlite3.c -o sqlite3.o -c -ldl
// arm-linux-gnueabihf-g++ modbustcp.cpp messagecontroller.cpp modbuscontroller.cpp chargestation.cpp log.o sqlite3.o -o modbustcp -lzmq -no-pie -lmodbus -lpthread -ldl -L/usr/local/arm-zmq_modbus_sqlite/lib/ -std=c++11

#include "chargestation.hpp"
#include "log.h"

int main()
{
  logInit("/var/log/modbus", 5);
  logNotice("initialized logging\n");
  ChargeStation chargeStation;
  chargeStation.start();
}
