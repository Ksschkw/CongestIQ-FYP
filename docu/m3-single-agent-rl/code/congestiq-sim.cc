#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/netanim-module.h"
#include "ns3/opengym-module.h"
#include "ns3/tcp-socket-base.h"
#include "my-gym-env.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("Congestiq");

int main (int argc, char *argv[])
{
  LogComponentEnable ("Congestiq", LOG_LEVEL_INFO);

  double simTime = 60.0;
  CommandLine cmd;
  cmd.AddValue ("simTime", "Simulation time", simTime);
  cmd.Parse (argc, argv);

  // Topology
  NodeContainer senders, receivers, routers;
  senders.Create (2);    // 0: RL, 1: CUBIC
  receivers.Create (2);
  routers.Create (2);

  PointToPointHelper accessLink, bottleneckLink;
  accessLink.SetDeviceAttribute ("DataRate", StringValue ("100Mbps"));
  accessLink.SetChannelAttribute ("Delay", StringValue ("1ms"));
  bottleneckLink.SetDeviceAttribute ("DataRate", StringValue ("10Mbps"));
  bottleneckLink.SetChannelAttribute ("Delay", StringValue ("20ms"));
  bottleneckLink.SetQueue ("ns3::DropTailQueue", "MaxSize", StringValue ("100p"));

  NetDeviceContainer dev0, dev1, bot, devR0, devR1;
  dev0 = accessLink.Install (senders.Get (0), routers.Get (0));
  dev1 = accessLink.Install (senders.Get (1), routers.Get (0));
  bot = bottleneckLink.Install (routers.Get (0), routers.Get (1));
  devR0 = accessLink.Install (routers.Get (1), receivers.Get (0));
  devR1 = accessLink.Install (routers.Get (1), receivers.Get (1));

  InternetStackHelper internet;
  internet.Install (senders);
  internet.Install (receivers);
  internet.Install (routers);

  Ipv4AddressHelper addr;
  Ipv4InterfaceContainer if0, if1, ifBot, ifR0, ifR1;
  addr.SetBase ("10.1.1.0", "255.255.255.0");
  if0 = addr.Assign (dev0);
  addr.SetBase ("10.1.2.0", "255.255.255.0");
  if1 = addr.Assign (dev1);
  addr.SetBase ("10.1.3.0", "255.255.255.0");
  ifBot = addr.Assign (bot);
  addr.SetBase ("10.1.4.0", "255.255.255.0");
  ifR0 = addr.Assign (devR0);
  addr.SetBase ("10.1.5.0", "255.255.255.0");
  ifR1 = addr.Assign (devR1);

  Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

  // TCP configuration: RL flow uses default TCP (we'll control cwnd via gym)
  // CUBIC for flow1
  Config::Set ("/NodeList/" + std::to_string (senders.Get (1)->GetId ()) +
               "/$ns3::TcpL4Protocol/SocketType",
               TypeIdValue (TcpSocketBase::GetTypeId ()));
  Config::Set ("/NodeList/" + std::to_string (senders.Get (1)->GetId ()) +
               "/$ns3::TcpL4Protocol/SocketList/0/CongestionOps",
               TypeIdValue (TcpCubic::GetTypeId ()));

  // Applications
  uint16_t port = 9;
  BulkSendHelper source0 ("ns3::TcpSocketFactory",
                          InetSocketAddress (ifR0.GetAddress (1), port));
  source0.SetAttribute ("MaxBytes", UintegerValue (0));
  ApplicationContainer app0 = source0.Install (senders.Get (0));
  app0.Start (Seconds (0.0));
  app0.Stop (Seconds (simTime));

  BulkSendHelper source1 ("ns3::TcpSocketFactory",
                          InetSocketAddress (ifR1.GetAddress (1), port));
  source1.SetAttribute ("MaxBytes", UintegerValue (0));
  ApplicationContainer app1 = source1.Install (senders.Get (1));
  app1.Start (Seconds (0.0));
  app1.Stop (Seconds (simTime));

  PacketSinkHelper sinkHelper ("ns3::TcpSocketFactory",
                               InetSocketAddress (Ipv4Address::GetAny (), port));
  ApplicationContainer sink0 = sinkHelper.Install (receivers.Get (0));
  sink0.Start (Seconds (0.0));
  sink0.Stop (Seconds (simTime));
  ApplicationContainer sink1 = sinkHelper.Install (receivers.Get (1));
  sink1.Start (Seconds (0.0));
  sink1.Stop (Seconds (simTime));

  // Gym environment
  Ptr<MyGymEnv> gymEnv = CreateObject<MyGymEnv> ();
  gymEnv->SetSimDuration (simTime);

  // Get the TCP socket used by the RL sender. We can retrieve it after the application starts.
  // We'll schedule a function to link the socket and sink to gymEnv.
  Simulator::Schedule (Seconds (0.1), [&]() {
    // The BulkSend application creates a socket; we can get it from the node's socket list.
    Ptr<Application> app = senders.Get (0)->GetApplication (0);
    Ptr<BulkSendApplication> bulk = DynamicCast<BulkSendApplication> (app);
    Ptr<Socket> socket = bulk->GetSocket ();
    Ptr<TcpSocketBase> tcpSocket = DynamicCast<TcpSocketBase> (socket);
    gymEnv->SetSocket (tcpSocket);

    // Sink app on receiver 0
    Ptr<Application> sinkApp = receivers.Get (0)->GetApplication (0);
    Ptr<PacketSink> sink = DynamicCast<PacketSink> (sinkApp);
    gymEnv->SetSinkApp (sink);

    // Start the gym interface after linking
    Ptr<OpenGymInterface> openGymInterface = CreateObject<OpenGymInterface> (5555, gymEnv);
    openGymInterface->NotifyCurrentState ();
  });

  // FlowMonitor and NetAnim
  FlowMonitorHelper flowmonHelper;
  Ptr<FlowMonitor> flowmon = flowmonHelper.InstallAll ();
  AnimationInterface anim ("congestiq-animation.xml");

  Simulator::Stop (Seconds (simTime));
  Simulator::Run ();
  flowmon->SerializeToXmlFile ("congestiq-flowmon.xml", false, true);
  Simulator::Destroy ();
  return 0;
}