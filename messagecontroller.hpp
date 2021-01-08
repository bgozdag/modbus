#ifndef MESSAGE_CONTROLLER_HPP
#define MESSAGE_CONTROLLER_HPP

#include "json.hpp"
#include "log.h"
#include <string>
#include <zmq.h>

#define zmqDealerIPC "ipc:///var/lib/routing.ipc"

class MessageController
{
public:
  MessageController(std::string id);
  ~MessageController();
  std::string receive();
  void send(std::string);
  nlohmann::json parse(std::string);

private:
  void *context;
  void *dealer;
};

#endif
