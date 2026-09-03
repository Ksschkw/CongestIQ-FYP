/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * two-flow-baseline.cc
 * M5: Two flows of the same TCP variant sharing a bottleneck.
 * Uses per-node Config::Set to guarantee the right congestion ops.
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/ipv4-global-routing-helper.h"
#include "ns3/traffic-control-module.h"
#include "ns3/tcp-socket-base.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("TwoFlowBaseline");

int main (int argc, char *argv[])
{
  std::string tcpVariant = "TcpCubic";
  double duration = 60.0;

  CommandLine cmd;
  cmd.AddValue ("tcp", "TCP variant (TcpNewReno, TcpCubic, TcpBbr)", tcpVariant);
  cmd.AddValue ("duration", "Simulation duration (seconds)", duration);
  cmd.Parse (argc, argv);

  // Create nodes
  NodeContainer senders;
  senders.Create (2);
  NodeContainer receivers;
  receivers.Create (2);
  NodeContainer routers;
  routers.Create (2);

  // Links
  PointToPointHelper accessLink;
  accessLink.SetDeviceAttribute ("DataRate", StringValue ("100Mbps"));
  accessLink.SetChannelAttribute ("Delay", StringValue ("1ms"));

  PointToPointHelper bottleneckLink;
  bottleneckLink.SetDeviceAttribute ("DataRate", StringValue ("10Mbps"));
  bottleneckLink.SetChannelAttribute ("Delay", StringValue ("20ms"));
  bottleneckLink.SetQueue ("ns3::DropTailQueue",
                           "MaxSize", StringValue ("100p"));

  NetDeviceContainer dev0, dev1, bot, devR0, devR1;
  dev0 = accessLink.Install (senders.Get (0), routers.Get (0));
  dev1 = accessLink.Install (senders.Get (1), routers.Get (0));
  bot  = bottleneckLink.Install (routers.Get (0), routers.Get (1));
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

  // Resolve TCP variant TypeId
  TypeId tcpTid;
  NS_ABORT_MSG_UNLESS (TypeId::LookupByNameFailSafe ("ns3::" + tcpVariant, &tcpTid),
                       "TypeId ns3::" << tcpVariant << " not found");

  // Set the congestion control algorithm on each sender's TCP sockets
  for (uint32_t i = 0; i < senders.GetN (); ++i)
    {
      Ptr<Node> sender = senders.Get (i);
      Config::Set ("/NodeList/" + std::to_string (sender->GetId ()) +
                   "/$ns3::TcpL4Protocol/SocketType",
                   TypeIdValue (tcpTid));
    }

  uint16_t port = 50000;
  // Sinks
  PacketSinkHelper sinkHelper ("ns3::TcpSocketFactory",
                               InetSocketAddress (Ipv4Address::GetAny (), port));
  ApplicationContainer sink0 = sinkHelper.Install (receivers.Get (0));
  sink0.Start (Seconds (0.0));
  sink0.Stop (Seconds (duration));
  ApplicationContainer sink1 = sinkHelper.Install (receivers.Get (1));
  sink1.Start (Seconds (0.0));
  sink1.Stop (Seconds (duration));

  // Sources
  BulkSendHelper source0 ("ns3::TcpSocketFactory",
                          InetSocketAddress (ifR0.GetAddress (1), port));
  source0.SetAttribute ("MaxBytes", UintegerValue (0));
  ApplicationContainer app0 = source0.Install (senders.Get (0));
  app0.Start (Seconds (0.0));
  app0.Stop (Seconds (duration));

  BulkSendHelper source1 ("ns3::TcpSocketFactory",
                          InetSocketAddress (ifR1.GetAddress (1), port));
  source1.SetAttribute ("MaxBytes", UintegerValue (0));
  ApplicationContainer app1 = source1.Install (senders.Get (1));
  app1.Start (Seconds (0.0));
  app1.Stop (Seconds (duration));

  // FlowMonitor
  FlowMonitorHelper flowmonHelper;
  Ptr<FlowMonitor> flowmon = flowmonHelper.InstallAll ();

  Simulator::Stop (Seconds (duration));
  Simulator::Run ();

  std::string outFile = "two-flow-" + tcpVariant + ".flowmon";
  flowmon->SerializeToXmlFile (outFile, false, true);
  NS_LOG_INFO ("FlowMonitor XML written to " << outFile);

  Simulator::Destroy ();
  return 0;
}