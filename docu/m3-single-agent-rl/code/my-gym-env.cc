#include "my-gym-env.h"
#include "ns3/tcp-socket-state.h"
#include "ns3/packet-sink.h"
#include "ns3/simulator.h"

NS_LOG_COMPONENT_DEFINE ("MyGymEnv");
NS_OBJECT_ENSURE_REGISTERED (MyGymEnv);

TypeId
MyGymEnv::GetTypeId ()
{
  static TypeId tid = TypeId ("MyGymEnv")
    .SetParent<OpenGymEnv> ()
    .AddConstructor<MyGymEnv> ();
  return tid;
}

MyGymEnv::MyGymEnv ()
  : m_socket (0),
    m_sink (0),
    m_lastUpdateTime (Seconds (0.0)),
    m_lastRxBytes (0),
    m_currentThroughputKbps (0.0),
    m_sRttMs (0.0),
    m_lossRate (0.0),
    m_maxThroughput (1.0),
    m_maxRttMs (1.0),
    m_minRttMs (1e9),
    m_decay (0.98),
    m_simDuration (60.0),
    m_gameOver (false)
{
}

MyGymEnv::~MyGymEnv () {}

void
MyGymEnv::SetSocket (Ptr<TcpSocketBase> socket)
{
  m_socket = socket;
}

void
MyGymEnv::SetSinkApp (Ptr<PacketSink> sink)
{
  m_sink = sink;
  m_lastRxBytes = sink->GetTotalRx ();
}

void
MyGymEnv::SetSimDuration (double duration)
{
  m_simDuration = duration;
}

void
MyGymEnv::UpdateMetrics ()
{
  if (!m_socket || !m_sink) return;

  // Time since last update
  Time now = Simulator::Now ();
  double intervalSec = (now - m_lastUpdateTime).GetSeconds ();
  if (intervalSec <= 0) intervalSec = 1e-9;

  // Throughput
  uint64_t currentRxBytes = m_sink->GetTotalRx ();
  uint64_t bytesReceived = currentRxBytes - m_lastRxBytes;
  double throughputBps = (bytesReceived * 8.0) / intervalSec;
  m_currentThroughputKbps = throughputBps / 1000.0;
  m_lastRxBytes = currentRxBytes;

  // RTT
  Ptr<TcpSocketState> tcb = m_socket->GetTcb ();
  m_sRttMs = tcb->m_srtt.Get ().GetSeconds () * 1000.0;

  // Loss rate: bytes sent vs bytes received estimate
  uint32_t txBytes = tcb->m_nextTxSequence - tcb->m_highTxMark; // not exact, but ok
  // Better: use tcb->m_lostOut (lost segments)
  uint32_t lostSegments = tcb->m_lostOut;
  uint32_t txSegments = tcb->m_nextTxSequence / tcb->m_segmentSize; // rough
  if (txSegments > 0)
    m_lossRate = (double)lostSegments / txSegments;
  else
    m_lossRate = 0.0;
  m_lossRate = std::min (m_lossRate, 1.0);

  m_lastUpdateTime = now;
}

Ptr<OpenGymSpace>
MyGymEnv::GetActionSpace ()
{
  return CreateObject<OpenGymDiscreteSpace> (5);
}

Ptr<OpenGymSpace>
MyGymEnv::GetObservationSpace ()
{
  // 4 elements: cwnd (packets), sRTT (ms), loss_rate (0-1), throughput (kbps)
  return CreateObject<OpenGymBoxSpace> (4, 0, 1e9);
}

Ptr<OpenGymDataContainer>
MyGymEnv::GetObservation ()
{
  uint32_t cwnd = m_socket ? m_socket->GetTcb ()->m_cWnd : 0;
  std::vector<float> obs = {
    static_cast<float>(cwnd),
    static_cast<float>(m_sRttMs),
    static_cast<float>(m_lossRate),
    static_cast<float>(m_currentThroughputKbps)
  };
  return CreateObject<OpenGymBoxContainer<float>> (obs);
}

float
MyGymEnv::GetReward ()
{
  double T = m_currentThroughputKbps;
  double s = m_sRttMs;
  double L = m_lossRate;

  // Update trackers
  m_maxThroughput = std::max (T, m_maxThroughput * m_decay);
  if (m_maxThroughput < 1.0) m_maxThroughput = 1.0;
  double thr_reward = std::min (T / m_maxThroughput, 1.0);

  m_minRttMs = std::min (s, m_minRttMs);
  m_maxRttMs = std::max (s, m_maxRttMs * m_decay);
  double denom = m_maxRttMs - m_minRttMs;
  double delay_pen = 0.0;
  if (denom > 1e-9)
    delay_pen = std::max (0.0, std::min ((s - m_minRttMs) / denom, 1.0));

  double loss_pen = L;

  double alpha = 1.0, beta = 0.5, gamma = 2.0;
  return alpha * thr_reward - beta * delay_pen - gamma * loss_pen;
}

bool
MyGymEnv::ExecuteActions (Ptr<OpenGymDataContainer> action)
{
  auto disc = DynamicCast<OpenGymDiscreteContainer> (action);
  uint32_t act = disc->GetValue ();
  if (m_socket)
    {
      uint32_t cwnd = m_socket->GetTcb ()->m_cWnd;
      double mult = 1.0;
      switch (act)
        {
        case 0: mult = 1.0; break;
        case 1: mult = 1.1; break;
        case 2: mult = 0.9; break;
        case 3: mult = 1.2; break;
        case 4: mult = 0.8; break;
        }
      uint32_t newCwnd = static_cast<uint32_t>(cwnd * mult);
      uint32_t segSize = m_socket->GetSegSize ();
      if (newCwnd < segSize) newCwnd = segSize;
      m_socket->SetCwnd (newCwnd);
    }
  UpdateMetrics ();
  return true;
}

bool
MyGymEnv::GetGameOver ()
{
  m_gameOver = (Simulator::Now ().GetSeconds () >= m_simDuration);
  return m_gameOver;
}

std::string
MyGymEnv::GetExtraInfo () { return ""; }