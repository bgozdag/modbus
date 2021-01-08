#ifndef ENUM_H
#define ENUM_H

#include <unordered_map>

enum ChargeStationStatus
{
  Normal,
  Initializing,
  WaitingForConfiguration,
  InstallingFirmware,
  WaitingForMasterAddition,
  AddedUserCard,
  RemovedUserCard,
  WaitingForConnection
};
std::unordered_map<std::string,
                   ChargeStationStatus> const chargeStationStatusTable = {
    {"Normal", ChargeStationStatus::Normal},
    {"Initializing", ChargeStationStatus::Initializing},
    {"WaitingForConfiguration", ChargeStationStatus::WaitingForConfiguration},
    {"InstallingFirmware", ChargeStationStatus::InstallingFirmware},
    {"WaitingForMasterAddition", ChargeStationStatus::WaitingForMasterAddition},
    {"AddedUserCard", ChargeStationStatus::AddedUserCard},
    {"RemovedUserCard", ChargeStationStatus::RemovedUserCard},
    {"WaitingForConnection", ChargeStationStatus::WaitingForConnection}};

enum ChargePointStatus
{
  Available,
  Preparing,
  Charging,
  SuspendedEVSE,
  SuspendedEV,
  Finishing,
  Reserved,
  Unavailable,
  Faulted
};
std::unordered_map<std::string, ChargePointStatus> const
    chargePointStatusTable = {
        {"Available", ChargePointStatus::Available},
        {"Preparing", ChargePointStatus::Preparing},
        {"Charging", ChargePointStatus::Charging},
        {"SuspendedEVSE", ChargePointStatus::SuspendedEVSE},
        {"SuspendedEV", ChargePointStatus::SuspendedEV},
        {"Finishing", ChargePointStatus::Finishing},
        {"Reserved", ChargePointStatus::Reserved},
        {"Unavailable", ChargePointStatus::Unavailable},
        {"Faulted", ChargePointStatus::Faulted}};

enum AuthorizationStatus
{
  Timeout,
  Start,
  Finish
};
std::unordered_map<std::string, AuthorizationStatus> const
    authorizationStatusTable = {{"Timeout", AuthorizationStatus::Timeout},
                                {"Start", AuthorizationStatus::Start},
                                {"Finish", AuthorizationStatus::Finish}};

enum ChargeSessionStatus
{
  Started,
  Stopped,
  Paused,
  Suspended
};
std::unordered_map<std::string, ChargeSessionStatus> const
    chargeSessionStatusTable = {{"Started", ChargeSessionStatus::Started},
                                {"Stopped", ChargeSessionStatus::Stopped},
                                {"Paused", ChargeSessionStatus::Paused},
                                {"Suspended", ChargeSessionStatus::Suspended}};

#endif
