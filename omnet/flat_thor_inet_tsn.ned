package omnet;

import inet.node.inet.StandardHost;
import inet.node.tsn.TsnSwitch;
import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;

// NOTE: Eth1G channel is defined in flat_thor_inet.ned in the same package
// and is reused here.

network FlatThorInetTsn
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

        coreSwitch: TsnSwitch {
            parameters:
                @display("p=250,200;i=device/switch");
        }

        accessSwitch: TsnSwitch {
            parameters:
                @display("p=400,200;i=device/switch");
        }

        zone[numZones]: StandardHost {
            parameters:
                @display("p=600,120,row,120;i=device/pc");
        }

    connections allowunconnected:
        // Thor to core TSN switch
        thor.ethg++ <--> Eth1G <--> coreSwitch.ethg++;

        // Core TSN switch to access TSN switch
        coreSwitch.ethg++ <--> Eth1G <--> accessSwitch.ethg++;

        // Access TSN switch to each zone
        for i = 0..numZones-1 {
            zone[i].ethg++ <--> Eth1G <--> accessSwitch.ethg++;
        }
}
