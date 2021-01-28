#include "tcpmessage.hpp"

TcpMessage::TcpMessage()
{
    transactionIdentifier = 0;
    protocolIdentifier = 0;
    messageLength = 0;
    unitIdentifier = 0;
    functionCode = 0;
    address = 0;
    nb = 0;
    dataSize = 0;
    data = 0;
}