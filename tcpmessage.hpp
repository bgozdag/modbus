#ifndef TCPMESSAGE_HPP
#define TCPMESSAGE_HPP

class TcpMessage
{
public:
    TcpMessage();
    int transactionIdentifier;
    int protocolIdentifier;
    int messageLength;
    int unitIdentifier;
    int functionCode;
    int address;
    int nb;
    int dataSize;
    int data;
};
#endif