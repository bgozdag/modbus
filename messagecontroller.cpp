#include "messagecontroller.hpp"

MessageController::MessageController()
{
  context = zmq_ctx_new();
  dealer = zmq_socket(context, ZMQ_DEALER);
  zmq_setsockopt(dealer, ZMQ_IDENTITY, "MODBUSTCP", 9);
  zmq_connect(dealer, zmqDealerIPC);
  logNotice("zmq dealer is connected\n");
}

MessageController::~MessageController()
{
  zmq_close(&dealer);
  zmq_ctx_destroy(&context);
}

std::string MessageController::receive()
{
  zmq_msg_t msg;
  zmq_msg_init(&msg);
  zmq_msg_recv(&msg, dealer, 0);
  std::string string_msg =
      std::string(static_cast<char *>(zmq_msg_data(&msg)), zmq_msg_size(&msg));
  zmq_msg_close(&msg);
  // logDebug("received: %s\n", string_msg.c_str());
  return string_msg;
}

json MessageController::parse(std::string msg)
{
  return json::parse(msg);
}

void MessageController::send(std::string msg)
{
  // logDebug("sending: %s\n", msg.c_str());
  zmq_send(dealer, msg.c_str(), msg.size(), 0);
}

void MessageController::sendFailsafeCurrent(int current)
{
  json j;
  j["type"] = "failsafeCurrent";
  j["data"]["value"] = current;
  send(j.dump());
  logNotice("sent failsafeCurrent: %d\n", current);
}

void MessageController::sendFailsafeTimeout(int time)
{
  json j;
  j["type"] = "failsafeTimeout";
  j["data"]["value"] = time;
  send(j.dump());
  logNotice("sent failsafeTimeout: %d\n", time);
}

void MessageController::sendModbusTcpCurrent(int current)
{
  json j;
  j["type"] = "modbusTcpCurrent";
  j["data"]["value"] = current;
  send(j.dump());
  logNotice("sent modbusTcpCurrent: %d\n", current);
}