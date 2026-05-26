/* -*- Mode: C++; c-file-style: "gnu"; indent-tabs-mode:nil; -*- */
/*
 * dumbbell-tcp.cc
 * Milestone M1: Network Sandbox
 * 
 * This program builds a classic dumbbell topology:
 *
 *   Sender0 (Reno)                        Receiver0
 *        \                                   /
 *         \  100Mbps, 1ms    Router0-------Router1   100Mbps, 1ms
 *          +------------------| Bottleneck |------------------+
 *         /                   | 10Mbps, 20ms|                  \
 *        /                    +-------------+                   \
 *   Sender1 (CUBIC)                                       Receiver1
 *
 * PURPOSE:
 *   Observe how two different TCP congestion control algorithms
 *   (Reno and CUBIC) compete for a shared bottleneck link.
 *
 * WHAT THIS SCRIPT DOES:
 *   1. Builds the topology above
 *   2. Installs TCP Reno on Sender0, TCP CUBIC on Sender1
 *   3. Runs bulk data transfer for a fixed duration
 *   4. Attaches FlowMonitor to collect throughput, RTT, loss
 *   5. Exports FlowMonitor statistics to XML
 *   6. Exports NetAnim animation XML
 *
 * WHY THIS TOPOLOGY:
 *   The dumbbell is the simplest topology that demonstrates
 *   congestion: multiple flows converge on a single constrained
 *   link. The bottleneck link's bandwidth (10 Mbps) and delay
 *   (20 ms) are deliberately chosen to create a realistic
 *   bandwidth-delay product and visible queue dynamics.
 *
 * WHY NOT A SINGLE LINK:
 *   A single link cannot show competition. Congestion control
 *   only matters when flows share a resource.
 */

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/netanim-module.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("DumbbellTcp");

int
main (int argc, char *argv[])
{
  // --------------------------------------------------------------
  // COMMAND-LINE ARGUMENTS
  // Allows overriding parameters without recompiling.
  // Example: ./ns3 run scratch/dumbbell-tcp -- --duration=30
  // --------------------------------------------------------------
  double duration = 60.0;          // Simulation time in seconds
  std::string bottleneckRate = "10Mbps";
  std::string bottleneckDelay = "20ms";
  std::string accessRate = "100Mbps";
  std::string accessDelay = "1ms";
  uint32_t queueSize = 100;        // Packets (DropTail queue limit)

  CommandLine cmd;
  cmd.AddValue ("duration", "Simulation duration (seconds)", duration);
  cmd.AddValue ("bottleneckRate", "Bottleneck link data rate", bottleneckRate);
  cmd.AddValue ("bottleneckDelay", "Bottleneck link delay", bottleneckDelay);
  cmd.Parse (argc, argv);

  // --------------------------------------------------------------
  // LOGGING
  // Enable informational messages so we can see flow start/stop.
  // --------------------------------------------------------------
  LogComponentEnable ("DumbbellTcp", LOG_LEVEL_INFO);
  // Uncomment the line below to see detailed packet events:
  // LogComponentEnable ("BulkSendApplication", LOG_LEVEL_INFO);

  // --------------------------------------------------------------
  // TOPOLOGY CONSTRUCTION
  // We use NodeContainer to group nodes logically.
  // --------------------------------------------------------------

  // Create the four edge nodes (2 senders, 2 receivers)
  NodeContainer senders;
  senders.Create (2);   // Index 0: Reno sender, Index 1: CUBIC sender

  NodeContainer receivers;
  receivers.Create (2); // Index 0: Reno receiver, Index 1: CUBIC receiver

  // Create the two routers that will form the bottleneck
  NodeContainer routers;
  routers.Create (2);   // Index 0: left router, Index 1: right router

  // --------------------------------------------------------------
  // LINK CONFIGURATION
  // We use PointToPointHelper to create wired links.
  // --------------------------------------------------------------

  // Helper for the high-speed access links (sender-router, router-receiver)
  PointToPointHelper accessLink;
  accessLink.SetDeviceAttribute ("DataRate", StringValue (accessRate));
  accessLink.SetChannelAttribute ("Delay", StringValue (accessDelay));

  // Helper for the bottleneck link (between the two routers)
  PointToPointHelper bottleneckLink;
  bottleneckLink.SetDeviceAttribute ("DataRate", StringValue (bottleneckRate));
  bottleneckLink.SetChannelAttribute ("Delay", StringValue (bottleneckDelay));

  // --------------------------------------------------------------
  // QUEUE CONFIGURATION
  // We explicitly set the queue type and size on the bottleneck link.
  // DropTail is the simplest queue: FIFO, drops tail when full.
  // This is critical: congestion manifests as queue overflow and loss.
  // --------------------------------------------------------------
  bottleneckLink.SetQueue ("ns3::DropTailQueue",
                           "MaxSize", StringValue (std::to_string(queueSize) + "p"));

  // --------------------------------------------------------------
  // INSTALL LINKS
  // NetDeviceContainer holds the network interfaces created for each link.
  // --------------------------------------------------------------

  // Connect sender 0 to router 0
  NetDeviceContainer sender0ToRouter0 = accessLink.Install (senders.Get (0), routers.Get (0));
  // Connect sender 1 to router 0
  NetDeviceContainer sender1ToRouter0 = accessLink.Install (senders.Get (1), routers.Get (0));

  // Connect router 0 to router 1 (THE BOTTLENECK)
  NetDeviceContainer router0ToRouter1 = bottleneckLink.Install (routers.Get (0), routers.Get (1));

  // Connect router 1 to receiver 0
  NetDeviceContainer router1ToReceiver0 = accessLink.Install (routers.Get (1), receivers.Get (0));
  // Connect router 1 to receiver 1
  NetDeviceContainer router1ToReceiver1 = accessLink.Install (routers.Get (1), receivers.Get (1));

  // --------------------------------------------------------------
  // INTERNET STACK
  // Install the TCP/IP protocol stack on all nodes.
  // --------------------------------------------------------------
  InternetStackHelper internet;
  internet.Install (senders);
  internet.Install (receivers);
  internet.Install (routers);

  // --------------------------------------------------------------
  // IP ADDRESSING
  // Assign IP addresses to each subnet.
  // --------------------------------------------------------------
  Ipv4AddressHelper address;

  // Left side subnets (sender -> router0)
  address.SetBase ("10.1.1.0", "255.255.255.0");
  Ipv4InterfaceContainer sender0Interface = address.Assign (sender0ToRouter0);
  address.SetBase ("10.1.2.0", "255.255.255.0");
  Ipv4InterfaceContainer sender1Interface = address.Assign (sender1ToRouter0);

  // Bottleneck subnet
  address.SetBase ("10.1.3.0", "255.255.255.0");
  Ipv4InterfaceContainer bottleneckInterfaces = address.Assign (router0ToRouter1);

  // Right side subnets (router1 -> receivers)
  address.SetBase ("10.1.4.0", "255.255.255.0");
  Ipv4InterfaceContainer receiver0Interface = address.Assign (router1ToReceiver0);
  address.SetBase ("10.1.5.0", "255.255.255.0");
  Ipv4InterfaceContainer receiver1Interface = address.Assign (router1ToReceiver1);

  // --------------------------------------------------------------
  // ROUTING
  // Populate routing tables. Ipv4GlobalRoutingHelper uses static
  // routes computed from the topology.
  // --------------------------------------------------------------
  Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

  // --------------------------------------------------------------
  // TCP CONFIGURATION
  // Here we select the congestion control algorithm per sender.
  // By default, ns-3 uses TCP NewReno. We will explicitly set
  // one flow to Reno and the other to CUBIC.
  //
  // IMPORTANT: We must set the congestion algorithm before creating
  // the socket, because the socket constructor reads the default
  // attributes from the TypeId.
  // --------------------------------------------------------------

  // --- Flow 0: TCP Reno ---
  // We use Config::Set to change the default socket type for Sender0.
  // "ns3::TcpL4Protocol::SocketType" is the attribute that controls
  // which congestion control variant is used.
  Config::Set ("/NodeList/" + std::to_string (senders.Get (0)->GetId ()) +
               "/$ns3::TcpL4Protocol/SocketType",
               TypeIdValue (TcpNewReno::GetTypeId ()));

  // --- Flow 1: TCP CUBIC ---
  Config::Set ("/NodeList/" + std::to_string (senders.Get (1)->GetId ()) +
               "/$ns3::TcpL4Protocol/SocketType",
               TypeIdValue (TcpCubic::GetTypeId ()));

  // --------------------------------------------------------------
  // APPLICATIONS
  // We use BulkSendApplication to model a greedy FTP-like transfer.
  // This sends data as fast as TCP allows, which is ideal for
  // studying congestion control behavior.
  // --------------------------------------------------------------

  uint16_t port = 9; // Well-known discard port (receiver will sink data)

  // --- Sender 0 (Reno) ---
  BulkSendHelper source0 ("ns3::TcpSocketFactory",
                          InetSocketAddress (receiver0Interface.GetAddress (1), port));
  source0.SetAttribute ("MaxBytes", UintegerValue (0)); // Unlimited data
  ApplicationContainer sourceApp0 = source0.Install (senders.Get (0));
  sourceApp0.Start (Seconds (0.0));
  sourceApp0.Stop (Seconds (duration));

  // --- Sender 1 (CUBIC) ---
  BulkSendHelper source1 ("ns3::TcpSocketFactory",
                          InetSocketAddress (receiver1Interface.GetAddress (1), port));
  source1.SetAttribute ("MaxBytes", UintegerValue (0));
  ApplicationContainer sourceApp1 = source1.Install (senders.Get (1));
  sourceApp1.Start (Seconds (0.0));
  sourceApp1.Stop (Seconds (duration));

  // --- Receivers (PacketSink) ---
  // PacketSink simply consumes all received packets and can log statistics.
  PacketSinkHelper sink0 ("ns3::TcpSocketFactory",
                          InetSocketAddress (Ipv4Address::GetAny (), port));
  ApplicationContainer sinkApp0 = sink0.Install (receivers.Get (0));
  sinkApp0.Start (Seconds (0.0));
  sinkApp0.Stop (Seconds (duration));

  PacketSinkHelper sink1 ("ns3::TcpSocketFactory",
                          InetSocketAddress (Ipv4Address::GetAny (), port));
  ApplicationContainer sinkApp1 = sink1.Install (receivers.Get (1));
  sinkApp1.Start (Seconds (0.0));
  sinkApp1.Stop (Seconds (duration));

  // --------------------------------------------------------------
  // FLOW MONITOR
  // FlowMonitor is ns-3's built-in statistics collection system.
  // It tracks per-flow metrics: throughput, delay, jitter, loss.
  // We install it on all nodes.
  // --------------------------------------------------------------
  FlowMonitorHelper flowmonHelper;
  Ptr<FlowMonitor> flowmon = flowmonHelper.InstallAll ();

  // --------------------------------------------------------------
  // NETANIM ANIMATION
  // AnimationInterface writes an XML file that NetAnim can read.
  // This gives us a visual playback of packet movements.
  // --------------------------------------------------------------
  std::string animFile = "dumbbell-tcp-animation.xml";
  AnimationInterface anim (animFile);

  // Optional: set descriptive labels for nodes
  anim.SetConstantPosition (senders.Get (0), 0.0, 10.0);
  anim.SetConstantPosition (senders.Get (1), 0.0, 30.0);
  anim.SetConstantPosition (routers.Get (0), 30.0, 20.0);
  anim.SetConstantPosition (routers.Get (1), 60.0, 20.0);
  anim.SetConstantPosition (receivers.Get (0), 90.0, 10.0);
  anim.SetConstantPosition (receivers.Get (1), 90.0, 30.0);

  NS_LOG_INFO ("NetAnim XML will be written to: " << animFile);

  // --------------------------------------------------------------
  // RUN THE SIMULATION
  // --------------------------------------------------------------
  NS_LOG_INFO ("Starting simulation for " << duration << " seconds...");
  Simulator::Stop (Seconds (duration));
  Simulator::Run ();
  NS_LOG_INFO ("Simulation finished.");

  // --------------------------------------------------------------
  // COLLECT AND EXPORT FLOW MONITOR STATISTICS
  // We serialize the collected data to an XML file for later
  // analysis (Python scripts, etc.).
  // --------------------------------------------------------------
//   flowmon->SerializeToXmlFile ("dumbbell-tcp-flowmon.xml", true, true);
  // flowmon->SerializeToXmlFile ("dumbbell-tcp-flowmon.xml", true, false);
  flowmon->SerializeToXmlFile ("dumbbell-tcp-flowmon.xml", false, true);
//                                     disable histograms ^^^^^   ^^^^ keep probes enabled
  NS_LOG_INFO ("FlowMonitor XML written to: dumbbell-tcp-flowmon.xml");

  // Clean up
  Simulator::Destroy ();
  return 0;
}