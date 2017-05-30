from mininet.topo import Topo, SingleSwitchTopo, LinearTopo
from mininet.node import RemoteController, Host
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info, debug
import shlex, subprocess

HSWITCH = "s1"
GWSWITCH = "s2"
CLIENT1 = "h1s2"
CLIENT2 = "h2s2"
CLIENT3 = "h3s2"
CLIENT4 = "h4s2"
SERVER1 = "h1s1"
SERVER2 = "h2s1"
SSWITCH1 = "h3s1"
SSWITCH2 = "h4s1"
CONFIG = "/home/niagara/ecmp_router/topo/config.sh"

SERVERS = [SERVER1, SERVER2]
CLIENTS = [CLIENT1, CLIENT2, CLIENT3, CLIENT4]
SSWITCHES = [SSWITCH1, SSWITCH2]


class NiagaraNet(Mininet):

    def __init__(self, topo, controller):
        Mininet.__init__(self, topo = topo, controller = controller)
        self.iperf_s = []
        self.iperf_c = []

    def iperf_server(self):
        if (self.iperf_s):
            info("---iperf server already starts\n")
            return
        info("----- start iperf server\n")
        for host in self.hosts:
            hostname = host.name
            if hostname in SERVERS:
#                x = host.sendCmd("bash ./startMN.sh -s", printPid=True)
                x = host.popen("bash ./startMN.sh -s")
                print x
                self.iperf_s.append(x)

    def iperf_client(self):
        info("-----wait for iperf client finish\n")
        for x in self.iperf_c:
            print "return = ", x.wait()
        self.iperf_c = []
        info("----- start iperf client\n")
        for host in self.hosts:
            hostname = host.name
            if hostname in CLIENTS:
#                x = host.sendCmd("bash ./startMN.sh -c", printPid=True)
                x = host.popen("bash ./startMN.sh -c")
                print x
                self.iperf_c.append(x)
        

def CreateNet():

#    net = Mininet(topo = LinearTopo(2, 4),
#                  controller = lambda name:RemoteController(name,ip='127.0.0.1'));
    net = NiagaraNet(topo = LinearTopo(2, 4),
                     controller = lambda name:RemoteController(name, ip='127.0.0.1'))

    info('****Starting network\n')
    net.start()
    
    hswitch = net.get(HSWITCH)

    # config host ip
    info('****config host ip\n')
    for host in net.hosts:
        hostname = host.name
        host.cmdPrint("bash %s %s ip" % (CONFIG, hostname))

    # set openflow protocol
    info('****set openflow protocol\n')
    for switch in net.switches:
        switch_name = switch.name
        switch.cmdPrint("bash %s %s br" % (CONFIG, switch_name))

    # config switch ip
    info('****config switch ip\n')
    for switch in net.switches:
        switch_name = switch.name
        switch.cmdPrint("bash %s %s ip" % (CONFIG, switch_name))

    # config host routes
    info('****config host routes\n')
    for host in net.hosts:
        hostname = host.name
        host.cmdPrint("bash %s %s rt" % (CONFIG, hostname))

    # config switch routes
    info('****config switch routes\n')
    for switch in net.switches:
        switch_name = switch.name
        switch.cmdPrint("bash %s %s rt" % (CONFIG, switch_name))

    # config sswitch nat
    info('****config host routes\n')
    for host in net.hosts:
        hostname = host.name
        vip = "192.168.6.6"
        host.cmdPrint("bash %s %s nat %s" % (CONFIG, hostname, vip))

    # config hswitch hw_nat_be
    info('****apply 1:1 hw_nat_be to the first vip(192.168.6.6) flow\n')
    for switch in net.switches:
        switch.cmdPrint("bash %s hw_nat_be" % CONFIG)
        switch.cmdPrint("bash %s hw_fwd_sww" % CONFIG)
        switch.cmdPrint("bash %s flows" % CONFIG)
        switch.cmdPrint("bash %s apply 5 2" % CONFIG)
        break


    info('****Starting terms for every node\n')
#    net.startTerms()

    info('****Runing CLI\n')
    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    CreateNet()
