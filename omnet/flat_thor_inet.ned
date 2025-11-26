package omnet;

import inet.node.inet.StandardHost;
import inet.node.ethernet.EthernetSwitch;

// Local 1 Gbit/s Ethernet channel
channel Eth1G extends ned.DatarateChannel
{
    datarate = 1Gbps;
    delay = 0.1us;   // pick something small and sane
}

network FlatThorInet
{
    @display("bgb=600,300");

    submodules:
        thor: StandardHost {
            @display("p=100,150;i=device/pc2");
        }

        core0: EthernetSwitch {
            @display("p=250,150;i=device/switch");
        }

        access0: EthernetSwitch {
            @display("p=400,70;i=device/switch");
        }
        access1: EthernetSwitch {
            @display("p=400,150;i=device/switch");
        }
        access2: EthernetSwitch {
            @display("p=400,230;i=device/switch");
        }

        zone0: StandardHost {
            @display("p=550,70;i=device/pc2");
        }
        zone1: StandardHost {
            @display("p=550,150;i=device/pc2");
        }
        zone2: StandardHost {
            @display("p=550,230;i=device/pc2");
        }

    connections:
        thor.ethg[0] <--> Eth1G <--> core0.ethg[0];

        core0.ethg[1] <--> Eth1G <--> access0.ethg[0];
        core0.ethg[2] <--> Eth1G <--> access1.ethg[0];
        core0.ethg[3] <--> Eth1G <--> access2.ethg[0];

        access0.ethg[1] <--> Eth1G <--> zone0.ethg[0];
        access1.ethg[1] <--> Eth1G <--> zone1.ethg[0];
        access2.ethg[1] <--> Eth1G <--> zone2.ethg[0];
}
