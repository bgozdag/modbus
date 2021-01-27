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
  MessageController(std::string id);
  ~MessageController();
  std::string receive();
  void send(std::string);
  json parse(std::string);

private:
  void *context;
  void *dealer;
};

#endif
