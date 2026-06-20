/* -*- Mode: C++; c-file-style: "gnu"; indent-tabs-mode:nil; -*- */
/*
 * multi-flow-bottleneck.cc
 * Milestone M2: Congestion Dynamics Deep Dive
 *
 * Topology (dumbbell):
 *   Sender0 (Reno)  ─┐
 *   Sender1 (CUBIC) ─┤
 *   Sender2 (BBR)   ─┼── Router0 ═══ Router1 ──┬── Receiver0
 *   Sender3 (CUBIC) ─┘                          ├── Receiver1
 *                                                ├── Receiver2
 *                                                └── Receiver3
 *
 * Bottleneck: 10 Mbps, 20 ms delay, DropTail queue of 100 packets.
 * Access links: 100 Mbps, 1 ms.
 *
 * WHAT THIS SCRIPT ADDS OVER M1:
 *   - 4 concurrent flows (Reno, CUBIC, BBR, CUBIC)
 *   - Traces the bottleneck queue occupancy (packets) over time
 *   - Still exports FlowMonitor and NetAnim XML
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/netanim-module.h"
#include <fstream>
#include <string>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("MultiFlowBottleneck");

// Global trace file for queue occupancy
static std::ofstream g_queueTrace;
// static uint64_t g_queuePackets = 0;

// Trace callback: when the queue changes, we log (time, new queue size)
static void
QueueTrace (uint32_t oldSize, uint32_t newSize)
{
  // Use Simulator::Now() to get the current simulation time
  double now = Simulator::Now().GetSeconds();
  g_queueTrace << now << "," << newSize << std::endl;
}

int
main (int argc, char *argv[])
{
  double duration = 60.0;
  std::string bottleneckRate = "10Mbps";
  std::string bottleneckDelay = "20ms";
  std::string accessRate = "100Mbps";
  std::string accessDelay = "1ms";
  uint32_t queueSize = 100;   // packets

  CommandLine cmd;
  cmd.AddValue ("duration", "Simulation duration (seconds)", duration);
  cmd.Parse (argc, argv);

  LogComponentEnable ("MultiFlowBottleneck", LOG_LEVEL_INFO);

  // --- Create nodes ---
  NodeContainer senders;
  senders.Create (4);   // 0:Reno, 1:CUBIC, 2:BBR, 3:CUBIC
  NodeContainer receivers;
  receivers.Create (4);
  NodeContainer routers;
  routers.Create (2);   // 0:left, 1:right

  // --- Link helpers ---
  PointToPointHelper accessLink;
  accessLink.SetDeviceAttribute ("DataRate", StringValue (accessRate));
  accessLink.SetChannelAttribute ("Delay", StringValue (accessDelay));

  PointToPointHelper bottleneckLink;
  bottleneckLink.SetDeviceAttribute ("DataRate", StringValue (bottleneckRate));
  bottleneckLink.SetChannelAttribute ("Delay", StringValue (bottleneckDelay));
  bottleneckLink.SetQueue ("ns3::DropTailQueue",
                           "MaxSize", StringValue (std::to_string(queueSize) + "p"));

  // --- Install links ---
  NetDeviceContainer senderDevices[4];
  for (uint32_t i = 0; i < 4; i++)
    {
      senderDevices[i] = accessLink.Install (senders.Get (i), routers.Get (0));
    }

  NetDeviceContainer bottleneckDevices = bottleneckLink.Install (routers.Get (0), routers.Get (1));

  NetDeviceContainer receiverDevices[4];
  for (uint32_t i = 0; i < 4; i++)
    {
      receiverDevices[i] = accessLink.Install (routers.Get (1), receivers.Get (i));
    }

  // --- Internet stack ---
  InternetStackHelper internet;
  internet.Install (senders);
  internet.Install (receivers);
  internet.Install (routers);

  // --- IP addresses ---
  Ipv4AddressHelper address;
  Ipv4InterfaceContainer senderInterfaces[4];
  Ipv4InterfaceContainer receiverInterfaces[4];
  Ipv4InterfaceContainer bottleneckInterfaces;

  for (uint32_t i = 0; i < 4; i++)
    {
      std::ostringstream subnet;
      subnet << "10.1." << (i+1) << ".0";
      address.SetBase (subnet.str ().c_str (), "255.255.255.0");
      senderInterfaces[i] = address.Assign (senderDevices[i]);
    }
  address.SetBase ("10.1.10.0", "255.255.255.0");
  bottleneckInterfaces = address.Assign (bottleneckDevices);
  for (uint32_t i = 0; i < 4; i++)
    {
      std::ostringstream subnet;
      subnet << "10.2." << (i+1) << ".0";
      address.SetBase (subnet.str ().c_str (), "255.255.255.0");
      receiverInterfaces[i] = address.Assign (receiverDevices[i]);
    }

  Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

  // --- TCP configuration per sender ---
  // Reno on sender 0
  Config::Set ("/NodeList/" + std::to_string (senders.Get (0)->GetId ()) +
               "/$ns3::TcpL4Protocol/SocketType",
               TypeIdValue (TcpNewReno::GetTypeId ()));
  // CUBIC on sender 1
  Config::Set ("/NodeList/" + std::to_string (senders.Get (1)->GetId ()) +
               "/$ns3::TcpL4Protocol/SocketType",
               TypeIdValue (TcpCubic::GetTypeId ()));
  // BBR on sender 2
  Config::Set ("/NodeList/" + std::to_string (senders.Get (2)->GetId ()) +
               "/$ns3::TcpL4Protocol/SocketType",
               TypeIdValue (TcpBbr::GetTypeId ()));
  // CUBIC on sender 3
  Config::Set ("/NodeList/" + std::to_string (senders.Get (3)->GetId ()) +
               "/$ns3::TcpL4Protocol/SocketType",
               TypeIdValue (TcpCubic::GetTypeId ()));

  // --- Applications ---
  uint16_t port = 9;
  for (uint32_t i = 0; i < 4; i++)
    {
      BulkSendHelper source ("ns3::TcpSocketFactory",
                             InetSocketAddress (receiverInterfaces[i].GetAddress (1), port));
      source.SetAttribute ("MaxBytes", UintegerValue (0));
      ApplicationContainer sourceApp = source.Install (senders.Get (i));
      sourceApp.Start (Seconds (0.0));
      sourceApp.Stop (Seconds (duration));

      PacketSinkHelper sink ("ns3::TcpSocketFactory",
                             InetSocketAddress (Ipv4Address::GetAny (), port));
      ApplicationContainer sinkApp = sink.Install (receivers.Get (i));
      sinkApp.Start (Seconds (0.0));
      sinkApp.Stop (Seconds (duration));
    }

  // --- Trace the bottleneck queue occupancy ---
  g_queueTrace.open ("multi-flow-queue.csv", std::ios::out);
  g_queueTrace << "Time,QueuePackets" << std::endl;

  // Hook the "PacketsInQueue" trace source of the bottleneck device's queue
  // We need to access the queue on the device. We'll use the NetDevice on the bottleneck.
  Ptr<NetDevice> bottleneckLeftDevice = bottleneckDevices.Get (0); // router0 side
  PointerValue ptr;
  bottleneckLeftDevice->GetAttribute ("TxQueue", ptr);   // TxQueue is the transmission queue
  Ptr<Queue<Packet>> txQueue = ptr.Get<Queue<Packet>> ();
  txQueue->TraceConnectWithoutContext ("PacketsInQueue", MakeCallback (&QueueTrace));

  // Also trace the right device? The bottleneck is symmetrical; one trace is enough.
  // If we trace the left device's TxQueue, it's the queue feeding the bottleneck link.

  // --- FlowMonitor and NetAnim ---
  FlowMonitorHelper flowmonHelper;
  Ptr<FlowMonitor> flowmon = flowmonHelper.InstallAll ();

  std::string animFile = "multi-flow-animation.xml";
  AnimationInterface anim (animFile);

  // Set positions for better layout (optional)
  anim.SetConstantPosition (senders.Get (0), 0.0, 5.0);
  anim.SetConstantPosition (senders.Get (1), 0.0, 15.0);
  anim.SetConstantPosition (senders.Get (2), 0.0, 25.0);
  anim.SetConstantPosition (senders.Get (3), 0.0, 35.0);
  anim.SetConstantPosition (routers.Get (0), 30.0, 20.0);
  anim.SetConstantPosition (routers.Get (1), 60.0, 20.0);
  anim.SetConstantPosition (receivers.Get (0), 90.0, 5.0);
  anim.SetConstantPosition (receivers.Get (1), 90.0, 15.0);
  anim.SetConstantPosition (receivers.Get (2), 90.0, 25.0);
  anim.SetConstantPosition (receivers.Get (3), 90.0, 35.0);

  NS_LOG_INFO ("Starting simulation...");
  Simulator::Stop (Seconds (duration));
  Simulator::Run ();
  Simulator::Destroy ();
  NS_LOG_INFO ("Simulation finished.");

  flowmon->SerializeToXmlFile ("multi-flow-flowmon.xml", false, true);
  g_queueTrace.close ();
  NS_LOG_INFO ("FlowMonitor XML and queue trace written.");

  return 0;
}