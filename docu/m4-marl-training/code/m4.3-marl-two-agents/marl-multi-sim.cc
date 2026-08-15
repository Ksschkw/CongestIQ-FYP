#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-helper.h"
#include "ns3/ipv4-global-routing-helper.h"
#include "ns3/opengym-module.h"
#include "marl-multi-env.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("MarlMulti");

int main (int argc, char *argv[])
{
  uint32_t nAgents = 2;
  double stepTime = 0.1;
  double duration = 60.0;
  uint32_t port = 5555;
  uint32_t run = 1;

  CommandLine cmd;
  cmd.AddValue ("nAgents", "Number of RL agents", nAgents);
  cmd.AddValue ("stepTime", "Gym step time", stepTime);
  cmd.AddValue ("duration", "Simulation duration", duration);
  cmd.AddValue ("openGymPort", "Port", port);
  cmd.AddValue ("simSeed", "Seed", run);
  cmd.Parse (argc, argv);

  SeedManager::SetSeed (1);
  SeedManager::SetRun (run);

  NodeContainer senders, receivers, routers;
  senders.Create (nAgents);
  receivers.Create (nAgents);
  routers.Create (2);

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
        sockets.push_back (tcpSocket);
      }

    gymEnv->SetSockets (sockets);
    gymEnv->SetOpenGymInterface (openGymInterface);
    gymEnv->Start ();
    openGymInterface->NotifyCurrentState ();
  });

  FlowMonitorHelper flowmonHelper;
  flowmonHelper.InstallAll ();

  Simulator::Stop (Seconds (duration));
  Simulator::Run ();

  flowmonHelper.SerializeToXmlFile ("marl-multi-flowmon.xml", false, true);
  openGymInterface->NotifySimulationEnd ();
  Simulator::Destroy ();
  return 0;
}