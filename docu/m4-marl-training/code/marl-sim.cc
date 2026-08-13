#include <iostream>
#include <string>

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/point-to-point-layout-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-helper.h"
#include "ns3/ipv4-global-routing-helper.h"
#include "ns3/traffic-control-module.h"

#include "ns3/opengym-module.h"
#include "marl-rl.h"

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("RlTcpSingleFlow");

int main (int argc, char *argv[])
{
  // Enable debug logging for RL components
  // LogComponentEnable ("RlTcpSingleFlow", LOG_LEVEL_INFO);
  // LogComponentEnable ("TcpRlBase", LOG_LEVEL_INFO);
  // LogComponentEnable ("TcpRlTimeBased", LOG_LEVEL_INFO);
  // LogComponentEnable ("TcpGymEnv", LOG_LEVEL_INFO);
  // LogComponentEnable ("OpenGymInterface", LOG_LEVEL_INFO);

  uint32_t openGymPort = 5555;
  double tcpEnvTimeStep = 0.1;   // 100 ms
  double duration = 60.0;
  uint32_t run = 1;
  bool flow_monitor = true;

  std::string bottleneck_bandwidth = "10Mbps";
  std::string bottleneck_delay = "20ms";
  std::string access_bandwidth = "100Mbps";
  std::string access_delay = "1ms";

  CommandLine cmd;
  cmd.AddValue ("openGymPort", "Port for OpenGym", openGymPort);
  cmd.AddValue ("simSeed", "Random seed", run);
  cmd.AddValue ("envTimeStep", "RL decision interval [s]", tcpEnvTimeStep);
  cmd.AddValue ("bottleneck_bandwidth", "Bottleneck bandwidth", bottleneck_bandwidth);
  cmd.AddValue ("bottleneck_delay", "Bottleneck delay", bottleneck_delay);
  cmd.AddValue ("access_bandwidth", "Access bandwidth", access_bandwidth);
  cmd.AddValue ("access_delay", "Access delay", access_delay);
  cmd.AddValue ("duration", "Simulation time [s]", duration);
  cmd.Parse (argc, argv);

  SeedManager::SetSeed (1);
  SeedManager::SetRun (run);

  // OpenGym interface (global)
  Ptr<OpenGymInterface> openGymInterface = OpenGymInterface::Get(openGymPort);

  // Set RL congestion control algorithm
  Config::SetDefault ("ns3::TcpL4Protocol::SocketType", TypeIdValue (TcpRlTimeBased::GetTypeId()));
  Config::SetDefault ("ns3::TcpRlTimeBased::StepTime", TimeValue (Seconds(tcpEnvTimeStep)));

  // Build dumbbell with 1 sender (RL) and 1 receiver
  PointToPointHelper accessLink;
  accessLink.SetDeviceAttribute ("DataRate", StringValue (access_bandwidth));
  accessLink.SetChannelAttribute ("Delay", StringValue (access_delay));

  PointToPointHelper bottleneckLink;
  bottleneckLink.SetDeviceAttribute ("DataRate", StringValue (bottleneck_bandwidth));
  bottleneckLink.SetChannelAttribute ("Delay", StringValue (bottleneck_delay));
  bottleneckLink.SetQueue ("ns3::DropTailQueue", "MaxSize", StringValue ("100p"));

  PointToPointDumbbellHelper d (1, accessLink, 1, accessLink, bottleneckLink);

  InternetStackHelper stack;
  stack.InstallAll ();

  d.AssignIpv4Addresses (Ipv4AddressHelper ("10.1.1.0", "255.255.255.0"),
                         Ipv4AddressHelper ("10.2.1.0", "255.255.255.0"),
                         Ipv4AddressHelper ("10.3.1.0", "255.255.255.0"));

  Ipv4GlobalRoutingHelper::PopulateRoutingTables ();

  uint16_t port = 50000;
  Address sinkAddr (InetSocketAddress (Ipv4Address::GetAny (), port));
  PacketSinkHelper sinkHelper ("ns3::TcpSocketFactory", sinkAddr);
  ApplicationContainer sinkApp = sinkHelper.Install (d.GetRight (0));
  sinkApp.Start (Seconds (0.0));
  sinkApp.Stop (Seconds (duration));

  // RL flow
  {
    AddressValue remote (InetSocketAddress (d.GetRightIpv4Address (0), port));
    BulkSendHelper ftp ("ns3::TcpSocketFactory", Address ());
    ftp.SetAttribute ("Remote", remote);
    ftp.SetAttribute ("MaxBytes", UintegerValue (0));
    ApplicationContainer app = ftp.Install (d.GetLeft (0));
    app.Start (Seconds (0.0));
    app.Stop (Seconds (duration));
  }

  // Flow monitor
  FlowMonitorHelper flowmonHelper;
  if (flow_monitor)
    flowmonHelper.InstallAll ();

  NS_LOG_INFO ("Starting simulation...");
  Simulator::Stop (Seconds (duration));
  Simulator::Run ();

  if (flow_monitor)
    flowmonHelper.SerializeToXmlFile ("rl-single-flow.flowmon", false, true);

  openGymInterface->NotifySimulationEnd ();
  Simulator::Destroy ();
  return 0;
}