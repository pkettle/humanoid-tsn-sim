package omnet;

import inet.node.inet.StandardHost;
import inet.node.ethernet.EthernetSwitch;
import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;

// Simple 1 Gbps Ethernet channel
channel Eth1G extends ned.DatarateChannel
{
    datarate = 1Gbps;
    delay    = 0.5us;
}

network FlatThorInet
{
    parameters:
        int numZones = default(2);  // number of humanoid zones

    submodules:
        configurator: Ipv4NetworkConfigurator {
            parameters:
                @display("p=100,50");
        }

        thor: StandardHost {
            parameters:
                @display("p=100,200;i=device/server");
        }

        coreSwitch: EthernetSwitch {
            parameters:
                @display("p=250,200;i=device/switch");
        }

        accessSwitch: EthernetSwitch {
            parameters:
                @display("p=400,200;i=device/switch");
        }

        zone[numZones]: StandardHost {
            parameters:
                @display("p=600,120,row,120;i=device/pc");
        }

    connections allowunconnected:
        // Thor to core switch
        thor.ethg++ <--> Eth1G <--> coreSwitch.ethg++;

        // Core to access switch
        coreSwitch.ethg++ <--> Eth1G <--> accessSwitch.ethg++;

        // Access switch to each zone
        for i = 0..numZones-1 {
            zone[i].ethg++ <--> Eth1G <--> accessSwitch.ethg++;
        }
}
