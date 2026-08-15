#ifndef MARL_MULTI_ENV_H
#define MARL_MULTI_ENV_H

#include "ns3/opengym-module.h"
#include "ns3/tcp-socket-base.h"
#include "ns3/packet-sink.h"
#include <vector>

namespace ns3 {

class MyMultiGymEnv : public OpenGymEnv
{
public:
  static TypeId GetTypeId (void);
  MyMultiGymEnv ();
  MyMultiGymEnv (uint32_t nAgents, Time stepTime);
  virtual ~MyMultiGymEnv () override;

  void SetSockets (std::vector<Ptr<TcpSocketBase>> sockets);
  void SetSinks (std::vector<Ptr<PacketSink>> sinks);
  void SetSimDuration (double duration);
  void Start ();   // call this after OpenGymInterface and sockets are set

  void UpdateMetrics ();

  virtual Ptr<OpenGymSpace> GetActionSpace () override;
  virtual Ptr<OpenGymSpace> GetObservationSpace () override;
  virtual Ptr<OpenGymDataContainer> GetObservation () override;
  virtual float GetReward () override;
  virtual bool ExecuteActions (Ptr<OpenGymDataContainer> action) override;
  virtual bool GetGameOver () override;
  virtual std::string GetExtraInfo () override;

private:
  void ScheduleNextStateRead ();
  uint32_t m_nAgents;
  Time m_stepTime;
  std::vector<Ptr<TcpSocketBase>> m_sockets;
  std::vector<Ptr<PacketSink>> m_sinks;
  std::vector<uint64_t> m_lastRxBytes;
  std::vector<float> m_throughputBps;
  std::vector<float> m_sRttMs;
  std::vector<float> m_lossRates;
  std::vector<float> m_cwnd;
  std::vector<float> m_minRtt;
  double m_simDuration;
  bool m_started {false};
  bool m_gameOver {false};
};

} // namespace ns3

#endif