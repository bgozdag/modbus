#include "messagecontroller.hpp"

MessageController::MessageController(std::string id)
{
  context = zmq_ctx_new();
  dealer = zmq_socket(context, ZMQ_DEALER);
  zmq_setsockopt(dealer, ZMQ_IDENTITY, id.c_str(), id.length());
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
  return string_msg;
}

nlohmann::json MessageController::parse(std::string msg)
{
  return nlohmann::json::parse(msg);
}
