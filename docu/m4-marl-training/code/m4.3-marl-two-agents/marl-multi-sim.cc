#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-helper.h"
#include "ns3/ipv4-global-routing-helper.h"
#include "ns3/opengym-module.h"
#include "ns3/netanim-module.h"
#include "ns3/tcp-socket-base.h"
#include "marl-multi-env.h"
#include <memory>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("MarlMulti");

// ----------------------------------------------------------------------
// No-op TCP congestion control.
// This disables ns-3's own cwnd growth/reduction so that only the
// RL agent (through MyMultiGymEnv::ExecuteActions) controls cwnd.
// ----------------------------------------------------------------------
class NoOpTcpCongestion : public TcpCongestionOps
{
public:
  static TypeId GetTypeId (void)
  {
    static TypeId tid = TypeId ("ns3::NoOpTcpCongestion")
      .SetParent<TcpCongestionOps> ()
      .AddConstructor<NoOpTcpCongestion> ()
    ;
    return tid;
  }

  NoOpTcpCongestion () : TcpCongestionOps () {}
  NoOpTcpCongestion (const NoOpTcpCongestion &other) : TcpCongestionOps (other) {}
  ~NoOpTcpCongestion () override {}

  std::string GetName () const override { return "NoOpTcpCongestion"; }

  uint32_t GetSsThresh (Ptr<const TcpSocketState> tcb, uint32_t /*bytesInFlight*/) override
  {
    // Keep the current cwnd as ssThresh (no change)
    return tcb->m_cWnd.Get ();
  }

  void IncreaseWindow (Ptr<TcpSocketState> tcb, uint32_t /*segmentsAcked*/) override
  {
    // Do nothing. The RL agent sets cwnd directly.
  }

  Ptr<TcpCongestionOps> Fork () override
  {
    return CopyObject<NoOpTcpCongestion> (this);
  }
};

int main (int argc, char *argv[])
{
  uint32_t nAgents = 2;
  double stepTime = 0.1;
  double duration = 60.0;
  uint32_t port = 5555;
  uint32_t run = 1;
  bool flowMon = true;
  bool anim = false;

  CommandLine cmd;
  cmd.AddValue ("nAgents", "Number of RL agents", nAgents);
  cmd.AddValue ("stepTime", "Gym step time", stepTime);
  cmd.AddValue ("duration", "Simulation duration", duration);
  cmd.AddValue ("openGymPort", "Port", port);
  cmd.AddValue ("simSeed", "Seed", run);
  cmd.AddValue ("flowmon", "Write FlowMonitor XML (disable during training)", flowMon);
  cmd.AddValue ("anim", "Write a NetAnim XML trace", anim);
  cmd.Parse (argc, argv);

  SeedManager::SetSeed (1);
  SeedManager::SetRun (run);

  FlowMonitorHelper flowmonHelper;

  // ------------------------------------------------------------------
  // IMPORTANT: the RL policy, not ns-3, must own cwnd.
  //
  // In this ns-3 tree the TcpL4Protocol "SocketType" attribute holds the
  // TypeId of the congestion control ops that every newly created socket
  // receives.  It must therefore be set to a TcpCongestionOps subclass,
  // and it must be set *after* InternetStackHelper::Install, because the
  // TcpL4Protocol object does not exist before that point.  Config::Set
  // silently does nothing when its path matches no object, which is how
  // the earlier version of this file fell back to the default TcpCubic.
  // ------------------------------------------------------------------

  // Create nodes
  NodeContainer senders, receivers, routers;
  senders.Create (nAgents);
  receivers.Create (nAgents);
  routers.Create (2);

  // Links
  PointToPointHelper accessLink;
  accessLink.SetDeviceAttribute ("DataRate", StringValue ("100Mbps"));
  accessLink.SetChannelAttribute ("Delay", StringValue ("1ms"));

  PointToPointHelper bottleneckLink;
  bottleneckLink.SetDeviceAttribute ("DataRate", StringValue ("10Mbps"));
  bottleneckLink.SetChannelAttribute ("Delay", StringValue ("20ms"));
  bottleneckLink.SetQueue ("ns3::DropTailQueue", "MaxSize", StringValue ("100p"));

  std::vector<NetDeviceContainer> senderDevs (nAgents);
  for (uint32_t i = 0; i < nAgents; ++i)
    senderDevs[i] = accessLink.Install (senders.Get (i), routers.Get (0));

  NetDeviceContainer bottleDev = bottleneckLink.Install (routers.Get (0), routers.Get (1));

  std::vector<NetDeviceContainer> recvDevs (nAgents);
  for (uint32_t i = 0; i < nAgents; ++i)
    recvDevs[i] = accessLink.Install (routers.Get (1), receivers.Get (i));

  InternetStackHelper stack;
  stack.Install (senders);
  stack.Install (receivers);
  stack.Install (routers);

  // Now that the TcpL4Protocol exists on every sender node, replace ns-3's
  // congestion control with the no-op class.  SetFailSafe returns false if
  // the path matched nothing, so a silent fallback to TcpCubic is impossible.
  for (uint32_t i = 0; i < senders.GetN (); ++i)
    {
      std::string path = "/NodeList/" + std::to_string (senders.Get (i)->GetId ()) +
                         "/$ns3::TcpL4Protocol/SocketType";
      bool ok = Config::SetFailSafe (path, TypeIdValue (NoOpTcpCongestion::GetTypeId ()));
      NS_ABORT_MSG_UNLESS (ok, "Could not attach NoOpTcpCongestion at " << path
                           << "; the RL policy would not own cwnd.");
    }

  Ipv4AddressHelper addr;
  std::vector<Ipv4InterfaceContainer> senderIfs (nAgents), recvIfs (nAgents);
  for (uint32_t i = 0; i < nAgents; ++i)
    {
      std::ostringstream subnet;
      subnet << "10.1." << (i + 1) << ".0";
      addr.SetBase (subnet.str ().c_str (), "255.255.255.0");
      senderIfs[i] = addr.Assign (senderDevs[i]);

      std::ostringstream subnet2;
      subnet2 << "10.2." << (i + 1) << ".0";
      addr.SetBase (subnet2.str ().c_str (), "255.255.255.0");
      recvIfs[i] = addr.Assign (recvDevs[i]);
    }
  addr.SetBase ("10.3.0.0", "255.255.255.0");
  addr.Assign (bottleDev);

  Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

  uint16_t portBase = 50000;
  std::vector<Ptr<PacketSink>> sinks;

  // Install sinks
  for (uint32_t i = 0; i < nAgents; ++i)
    {
      PacketSinkHelper sinkHelper ("ns3::TcpSocketFactory",
                                   InetSocketAddress (Ipv4Address::GetAny (), portBase + i));
      ApplicationContainer sinkApp = sinkHelper.Install (receivers.Get (i));
      sinkApp.Start (Seconds (0.0));
      sinkApp.Stop (Seconds (duration));
      Ptr<PacketSink> sink = DynamicCast<PacketSink> (sinkApp.Get (0));
      sinks.push_back (sink);
    }

  // Install sources
  for (uint32_t i = 0; i < nAgents; ++i)
    {
      BulkSendHelper source ("ns3::TcpSocketFactory",
                             InetSocketAddress (recvIfs[i].GetAddress (1), portBase + i));
      source.SetAttribute ("MaxBytes", UintegerValue (0));
      ApplicationContainer app = source.Install (senders.Get (i));
      app.Start (Seconds (0.0));
      app.Stop (Seconds (duration));
    }

  // Create gym environment, but do not start scheduling yet
  Ptr<MyMultiGymEnv> gymEnv = CreateObject<MyMultiGymEnv> (nAgents, Seconds (stepTime));
  gymEnv->SetSinks (sinks);
  gymEnv->SetSimDuration (duration);

  Ptr<OpenGymInterface> openGymInterface = CreateObject<OpenGymInterface> (port);

  // Schedule socket retrieval and environment start after socket creation
  Simulator::Schedule (Seconds (0.1), [&] () {
    std::vector<Ptr<TcpSocketBase>> sockets;
    for (uint32_t i = 0; i < nAgents; ++i)
      {
        Ptr<TcpL4Protocol> tcp = senders.Get (i)->GetObject<TcpL4Protocol> ();
        ObjectVectorValue socketVec;
        tcp->GetAttribute ("SocketList", socketVec);
        Ptr<Object> sockObj = socketVec.Get (socketVec.GetN () - 1);
        Ptr<TcpSocketBase> tcpSocket = DynamicCast<TcpSocketBase> (sockObj);
        NS_ABORT_MSG_UNLESS (tcpSocket, "Sender " << i << " has no TcpSocketBase");

        // Runtime proof that ns-3's own congestion control is not attached.
        std::string caName = tcpSocket->GetCongestionControlAlgorithm ()->GetName ();
        std::cout << "[MarlMulti] sender " << i << " congestion control = " << caName
                  << std::endl;
        NS_ABORT_MSG_UNLESS (caName == "NoOpTcpCongestion",
                             "Sender " << i << " is controlled by " << caName
                             << ", not by the RL policy.");

        sockets.push_back (tcpSocket);
      }

    gymEnv->SetSockets (sockets);
    gymEnv->SetOpenGymInterface (openGymInterface);
    gymEnv->Start ();
    openGymInterface->NotifyCurrentState ();
  });

  if (flowMon)
    {
      flowmonHelper.InstallAll ();
    }

  // Optional NetAnim trace. The object must stay alive until after
  // Simulator::Run, because the XML is written when it is destroyed.
  std::unique_ptr<AnimationInterface> animator;
  if (anim)
    {
      animator = std::make_unique<AnimationInterface> ("marl-multi-animation.xml");
      animator->SetConstantPosition (senders.Get (0), 0.0, 10.0);
      animator->SetConstantPosition (senders.Get (1), 0.0, 30.0);
      animator->SetConstantPosition (routers.Get (0), 30.0, 20.0);
      animator->SetConstantPosition (routers.Get (1), 60.0, 20.0);
      animator->SetConstantPosition (receivers.Get (0), 90.0, 10.0);
      animator->SetConstantPosition (receivers.Get (1), 90.0, 30.0);
    }

  Simulator::Stop (Seconds (duration));
  Simulator::Run ();

  if (flowMon)
    {
      flowmonHelper.SerializeToXmlFile ("marl-multi-flowmon.xml", false, true);
    }
  animator.reset ();
  openGymInterface->NotifySimulationEnd ();
  Simulator::Destroy ();
  return 0;
}