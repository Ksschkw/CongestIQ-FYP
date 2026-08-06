#ifndef MY_GYM_ENV_H
#define MY_GYM_ENV_H

#include "ns3/opengym-module.h"
#include "ns3/tcp-socket-base.h"

namespace ns3 {

class MyGymEnv : public OpenGymEnv
{
public:
  static TypeId GetTypeId (void);
  MyGymEnv ();
  virtual ~MyGymEnv ();

  void SetSocket (Ptr<TcpSocketBase> socket);
  void SetSinkApp (Ptr<PacketSink> sink);   // to track received bytes
  void SetSimDuration (double duration);
  void UpdateMetrics ();                     // call every decision interval

  // OpenGymEnv interface
  virtual Ptr<OpenGymSpace> GetActionSpace () override;
  virtual Ptr<OpenGymSpace> GetObservationSpace () override;
  virtual Ptr<OpenGymDataContainer> GetObservation () override;
  virtual float GetReward () override;
  virtual bool ExecuteActions (Ptr<OpenGymDataContainer> action) override;
  virtual bool GetGameOver () override;
  virtual std::string GetExtraInfo () override;

private:
  Ptr<TcpSocketBase> m_socket;
  Ptr<PacketSink> m_sink;
  Time m_lastUpdateTime;
  uint64_t m_lastRxBytes;
  double m_currentThroughputKbps;
  double m_sRttMs;
  double m_lossRate;

  // Decaying maximums for reward
  double m_maxThroughput;
  double m_maxRttMs;
  double m_minRttMs;
  double m_decay;

  double m_simDuration;
  bool m_gameOver;
};

} // namespace ns3

#endif /* MY_GYM_ENV_H */