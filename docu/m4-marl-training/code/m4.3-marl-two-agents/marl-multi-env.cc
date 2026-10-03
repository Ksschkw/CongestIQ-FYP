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
  // Joint discrete action space. Each agent has five window actions, so the
  // joint space has 5^nAgents values. Agent 0 is the least significant digit.
  //
  // The earlier version exposed a continuous box action space of one value per
  // agent, which was rounded to five levels in Python. With a continuous space
  // the Stable Baselines3 policy kept its output mean near the lower bound and
  // relied on exploration noise, so the deterministic policy did not choose the
  // window increases that the reward favoured. A discrete space makes the
  // deterministic action a real choice (the most likely action).
  uint32_t jointActions = 1;
  for (uint32_t i = 0; i < m_nAgents; ++i)
    {
      jointActions *= 5;
    }
  return CreateObject<OpenGymDiscreteSpace> (jointActions);
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
    {
      totalThroughputMbps += m_throughputBps[i] / 1000000.0f;
    }

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

  // Average queueing delay above the lowest smoothed RTT seen so far.
  // A smoothed RTT of zero means no sample exists yet, so it must not be
  // allowed to set the minimum, otherwise the base propagation delay would be
  // charged as queueing delay for the rest of the run.
  float avgQueueDelayMs = 0.0f;
  for (uint32_t i = 0; i < m_nAgents; ++i)
    {
      float rtt = m_sRttMs[i];
      if (rtt > 0.0f && m_minRtt[i] > rtt)
        {
          m_minRtt[i] = rtt;
        }
      float queueDelay = 0.0f;
      if (m_minRtt[i] < 1.0e8f)
        {
          queueDelay = rtt - m_minRtt[i];
          if (queueDelay < 0.0f)
            {
              queueDelay = 0.0f;
            }
        }
      avgQueueDelayMs += queueDelay;
    }
  avgQueueDelayMs /= m_nAgents;

  float avgLoss = 0.0f;
  for (uint32_t i = 0; i < m_nAgents; ++i)
    {
      avgLoss += m_lossRates[i];
    }
  avgLoss /= m_nAgents;

  // Average congestion window in bytes.
  float avgCwndBytes = 0.0f;
  for (uint32_t i = 0; i < m_nAgents; ++i)
    {
      avgCwndBytes += m_cwnd[i];
    }
  avgCwndBytes /= m_nAgents;

  // Reward balance, revised after several corrected training runs.
  //
  // The version documented in the report gave throughput up to 20 points and
  // charged 1 point per millisecond of queueing delay. A constant-action
  // experiment showed that this made "hold cwnd" the best behaviour.
  //
  // Later versions gave throughput 60 points, but a light delay charge made a
  // policy that raised the window at every step the best one it could find.
  // That policy filled the router queue and produced a mean delay near 142 ms.
  //
  // The weights below add a direct congestion window charge, because the delay
  // charge alone was not enough to pull the policy away from the flooding
  // behaviour. A hand-coded reference controller that raises the window to about
  // 25 KB and then holds it earns about 73 points per step, so the good
  // operating point is reachable. With a window charge of 0.0005 points per
  // byte, a window of 25 KB costs about 12 points per step, a held 5 KB window
  // costs about 3, and a flooded 500 KB window costs 250. Throughput remains
  // worth up to 60 points and fairness up to 20, the queueing delay charge is
  // 0.3 points per millisecond, and loss costs 20 points per unit loss rate.
  float throughputScore = totalThroughputMbps / 10.0f;
  if (throughputScore > 1.0f)
    {
      throughputScore = 1.0f;
    }

  return 60.0f * throughputScore
         + 20.0f * fairness
         - 0.3f * avgQueueDelayMs
         - 20.0f * avgLoss
         - 0.0005f * avgCwndBytes;
}

bool
MyMultiGymEnv::ExecuteActions (Ptr<OpenGymDataContainer> action)
{
  Ptr<OpenGymDiscreteContainer> discrete = DynamicCast<OpenGymDiscreteContainer> (action);
  if (!discrete)
    return false;

  // Decode the joint action. Agent 0 is the least significant digit.
  uint32_t joint = discrete->GetValue ();

  for (uint32_t i = 0; i < m_nAgents; ++i)
    {
      if (!m_sockets[i])
        {
          joint /= 5;
          continue;
        }

      uint32_t act = joint % 5;
      joint /= 5;

      // Action ordering follows the project report: 0 keeps the window and the
      // other values raise or lower it.
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