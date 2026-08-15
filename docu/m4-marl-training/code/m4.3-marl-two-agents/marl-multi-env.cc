#include "marl-multi-env.h"
#include "ns3/simulator.h"
#include "ns3/node-list.h"
#include "ns3/packet-sink.h"
#include "ns3/tcp-socket-state.h"
#include <numeric>

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("MyMultiGymEnv");
NS_OBJECT_ENSURE_REGISTERED (MyMultiGymEnv);

TypeId
MyMultiGymEnv::GetTypeId ()
{
  static TypeId tid = TypeId ("ns3::MyMultiGymEnv")
    .SetParent<OpenGymEnv> ()
    .AddConstructor<MyMultiGymEnv> ();
  return tid;
}

MyMultiGymEnv::MyMultiGymEnv ()
  : m_nAgents (1), m_stepTime (Seconds (0.1)), m_simDuration (60.0)
{
  // Do NOT schedule state read here.
}

MyMultiGymEnv::MyMultiGymEnv (uint32_t nAgents, Time stepTime)
  : m_nAgents (nAgents), m_stepTime (stepTime), m_simDuration (60.0)
{
  // Do NOT schedule state read here.
}

MyMultiGymEnv::~MyMultiGymEnv ()
{
}

void
MyMultiGymEnv::SetSockets (std::vector<Ptr<TcpSocketBase>> sockets)
{
  m_sockets = sockets;
  m_lastRxBytes.assign (m_nAgents, 0);
  m_minRtt.assign (m_nAgents, 1e9);
}

void
MyMultiGymEnv::SetSinks (std::vector<Ptr<PacketSink>> sinks)
{
  m_sinks = sinks;
  for (uint32_t i = 0; i < sinks.size (); ++i)
    {
      if (i < m_lastRxBytes.size ())
        m_lastRxBytes[i] = sinks[i]->GetTotalRx ();
    }
}

void
MyMultiGymEnv::SetSimDuration (double duration)
{
  m_simDuration = duration;
}

void
MyMultiGymEnv::Start ()
{
  if (!m_started)
    {
      m_started = true;
      // Schedule the first state read after one step time.
      Simulator::Schedule (m_stepTime, &MyMultiGymEnv::ScheduleNextStateRead, this);
    }
}

void
MyMultiGymEnv::ScheduleNextStateRead ()
{
  Simulator::Schedule (m_stepTime, &MyMultiGymEnv::ScheduleNextStateRead, this);
  Notify ();
}

void
MyMultiGymEnv::UpdateMetrics ()
{
  if (m_sockets.size () != m_nAgents || m_sinks.size () != m_nAgents)
    return;

  m_throughputBps.assign (m_nAgents, 0.0f);
  m_sRttMs.assign (m_nAgents, 0.0f);
  m_lossRates.assign (m_nAgents, 0.0f);
  m_cwnd.assign (m_nAgents, 0.0f);

  for (uint32_t i = 0; i < m_nAgents; ++i)
    {
      if (!m_sockets[i] || !m_sinks[i])
        continue;

      uint64_t rx = m_sinks[i]->GetTotalRx ();
      uint64_t delta = rx - m_lastRxBytes[i];
      m_lastRxBytes[i] = rx;
      m_throughputBps[i] = static_cast<float>((delta * 8.0) / m_stepTime.GetSeconds ());

      Ptr<TcpSocketState> state = m_sockets[i]->GetTcpState ();
      m_cwnd[i] = static_cast<float>(state->m_cWnd.Get ());
      m_sRttMs[i] = static_cast<float>(state->m_srtt.Get ().GetSeconds () * 1000.0);
      m_lossRates[i] = 0.0f; // placeholder
    }
}

Ptr<OpenGymSpace>
MyMultiGymEnv::GetObservationSpace ()
{
  uint32_t obsPerAgent = 4; // cwnd, srtt, loss, throughput
  uint32_t total = m_nAgents * obsPerAgent;
  std::vector<float> low (total, 0.0f);
  std::vector<float> high (total, 1e9);
  std::vector<uint32_t> shape = {total};
  return CreateObject<OpenGymBoxSpace> (low, high, shape, TypeNameGet<float> ());
}

Ptr<OpenGymSpace>
MyMultiGymEnv::GetActionSpace ()
{
  // Box action space, shape [nAgents], each value 0..4
  std::vector<float> low (m_nAgents, 0.0f);
  std::vector<float> high (m_nAgents, 4.0f);
  std::vector<uint32_t> shape = {m_nAgents};
  return CreateObject<OpenGymBoxSpace> (low, high, shape, TypeNameGet<uint32_t> ());
}

Ptr<OpenGymDataContainer>
MyMultiGymEnv::GetObservation ()
{
  UpdateMetrics ();
  uint32_t obsPerAgent = 4;
  std::vector<uint32_t> shape = {m_nAgents * obsPerAgent};
  Ptr<OpenGymBoxContainer<float>> box = CreateObject<OpenGymBoxContainer<float>> (shape);
  for (uint32_t i = 0; i < m_nAgents; ++i)
    {
      box->AddValue (m_cwnd[i]);
      box->AddValue (m_sRttMs[i]);
      box->AddValue (m_lossRates[i]);
      box->AddValue (m_throughputBps[i]);
    }
  return box;
}

float
MyMultiGymEnv::GetReward ()
{
  float totalThroughputMbps = 0.0f;
  for (uint32_t i = 0; i < m_nAgents; ++i)
    totalThroughputMbps += m_throughputBps[i] / 1000000.0f;

  float sum = 0.0f;
  float sumSq = 0.0f;
  for (uint32_t i = 0; i < m_nAgents; ++i)
    {
      float t = m_throughputBps[i] / 1000000.0f;
      sum += t;
      sumSq += t * t;
    }
  float fairness = (m_nAgents > 0 && sumSq > 0)
                   ? (sum * sum) / (m_nAgents * sumSq)
                   : 0.0f;

  float avgDelayPenalty = 0.0f;
  for (uint32_t i = 0; i < m_nAgents; ++i)
    {
      float rtt = m_sRttMs[i];
      if (m_minRtt[i] > rtt) m_minRtt[i] = rtt;
      float queueDelay = (rtt - m_minRtt[i]) / 10.0f;
      avgDelayPenalty += queueDelay;
    }
  avgDelayPenalty /= m_nAgents;

  float lossPenalty = 0.0f;
  for (uint32_t i = 0; i < m_nAgents; ++i)
    lossPenalty += m_lossRates[i];

  return (20.0f * totalThroughputMbps / 10.0f)
         + (20.0f * fairness)
         - avgDelayPenalty
         - lossPenalty;
}

bool
MyMultiGymEnv::ExecuteActions (Ptr<OpenGymDataContainer> action)
{
  auto box = DynamicCast<OpenGymBoxContainer<uint32_t>> (action);
  if (!box)
    return false;

  for (uint32_t i = 0; i < m_nAgents; ++i)
    {
      if (!m_sockets[i])
        continue;

      uint32_t act = box->GetValue (i);
      double mult = 1.0;
      switch (act) {
        case 0: mult = 1.0; break;
        case 1: mult = 1.1; break;
        case 2: mult = 0.9; break;
        case 3: mult = 1.2; break;
        case 4: mult = 0.8; break;
      }

      Ptr<TcpSocketState> state = m_sockets[i]->GetTcpState ();
      uint32_t currentCwnd = state->m_cWnd.Get ();
      uint32_t newCwnd = static_cast<uint32_t>(currentCwnd * mult);
      uint32_t segSize = state->m_segmentSize;
      if (newCwnd < segSize)
        newCwnd = segSize;
      state->m_cWnd = newCwnd;
    }
  return true;
}

bool
MyMultiGymEnv::GetGameOver ()
{
  m_gameOver = (Simulator::Now ().GetSeconds () >= m_simDuration);
  return m_gameOver;
}

std::string
MyMultiGymEnv::GetExtraInfo ()
{
  return "";
}

} // namespace ns3