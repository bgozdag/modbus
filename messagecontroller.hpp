#ifndef MESSAGE_CONTROLLER_HPP
#define MESSAGE_CONTROLLER_HPP

#include "json.hpp"
#include "log.h"
#include <string>
#include <zmq.h>

#define zmqDealerIPC "ipc:///var/lib/routing.ipc"

using json = nlohmann::json;

class MessageController
{
public:
  MessageController();
  ~MessageController();
  std::string receive();
  void send(std::string);
  void sendFailsafeCurrent(int current);
  void sendFailsafeTimeout(int current);
  void sendModbusTcpCurrent(int current);
  json parse(std::string);

private:
  void *context;
  void *dealer;
};

#endif
