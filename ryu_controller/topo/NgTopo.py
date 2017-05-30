from mininet.topo import Topo, SingleSwitchTopo, LinearTopo
from mininet.node import RemoteController, Host
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info, debug
import shlex, subprocess

HSWITCH = "s1"
GWSWITCH = "s2"
CONFIG = "/home/niagara/ecmp_router/topo/initMN.sh"


class NiagaraTopo(Topo):
    "Niagara topology of 2 switches: s1 connects all backends; s2 connects all clients"

    def build(self, nclients = 4, nservers = 4):
        self.m_nclients = nclients
        self.m_nservers = nservers

        ## A trick here to name the hosts
        ## Mininet allocates IP 10.0.0.0/24 to hosts based on the order of the hostname
        ## So we put clients (e.g., "gwh1") ahead of servers (e.g., "hwh1")
        ## This saves effort in ifconfig clients
        def gen_host_name(s, h):
            if s == 1:
                return 'hwh%d' % h
            elif s == 2:
                return 'gwh%d' % h

        def gen_sw_name(s):
            return 's%d' % s

        hw_id = 1
        gw_id = 2
        hw_switch = self.addSwitch(gen_sw_name(hw_id))
        gw_switch = self.addSwitch(gen_sw_name(gw_id))

        ## create client
        for i in range(1, nclients + 1):
            host = self.addHost(gen_host_name(gw_id, i))
            self.addLink(gw_switch, host)

        ## create server
        for i in range(1, nservers + 1):
            host = self.addHost(gen_host_name(hw_id, i))
            self.addLink(hw_switch, host)

        self.addLink(gw_switch, hw_switch)


    def is_server(self, hostname):
        return ("hw" in hostname)

    def is_client(self, hostname, a = 0, b = 0):
        if ("gw" in hostname):
            if (not a) and (not b):
                return True
            else:
                range_hosts = map(lambda x: ("gwh%d" % x), range(a, b))
                return hostname in range_hosts

class NiagaraNet(Mininet):

    def __init__(self, topo, controller):
        Mininet.__init__(self, topo = topo, controller = controller)
        self.iperf_s = {}
        self.iperf_c = {}

    def iperf_server(self, port = 0):
        def command(port):
            if (port):
                return "bash ./startMN.sh -s %d" % port
            else:
                return "bash ./startMN.sh -s"

        if port not in self.iperf_s:
            self.iperf_s[port] = []
        ps = self.iperf_s[port]

        if (ps):
            info("---iperf server already starts\n")
            return
        info("----- start iperf server\n")
        for host in self.hosts:
            hostname = host.name
            if self.topo.is_server(hostname):
                x = host.popen(command(port))
                print x
                ps.append(x)

    def iperf_client(self, port = 0, a = 0, b = 0):
        def command(port):
            if (port):
                return "bash ./startMN.sh -c %d" % port
            else:
                return "bash ./startMN.sh -c"

        if port not in self.iperf_c:
            self.iperf_c[port] = []

        ps = self.iperf_c[port]
        info("-----wait for iperf client finish\n")
        for x in ps:
            print "return = ", x.wait()

        ps = []
        self.iperf_c[port] = ps
        info("----- start iperf client\n")
        for host in self.hosts:
            hostname = host.name
            if self.topo.is_client(hostname, a, b):
                x = host.popen(command(port))
                print x
                ps.append(x)
        

def CreateNet():

#    net = Mininet(topo = LinearTopo(2, 4),
#                  controller = lambda name:RemoteController(name,ip='127.0.0.1'));
    topo = NiagaraTopo()
    topo.build(64, 4)
    net = NiagaraNet(topo = topo,
                     controller = lambda name:RemoteController(name, ip='127.0.0.1'))

    info('****Starting network\n')
    net.start()
    
    hswitch = net.get(HSWITCH)

    # config host ip
    info('****config host ip\n')
    for host in net.hosts:
        hostname = host.name
        if net.topo.is_client(hostname):
            host.cmdPrint("bash %s %s ip" % (CONFIG, "client"))
        else:
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
        if net.topo.is_client(hostname):
            host.cmdPrint("bash %s %s rt" % (CONFIG, "client"))
        else:
            host.cmdPrint("bash %s %s rt" % (CONFIG, hostname))

    # config switch routes
    info('****config switch routes\n')
    for switch in net.switches:
        switch_name = switch.name
        switch.cmdPrint("bash %s %s rt" % (CONFIG, switch_name))

    # config hswitch hw_nat_be
    info('****apply 1:1 hw_nat_be to the first vip(192.168.6.6, 12345) flow\n')
    for switch in net.switches:
        switch.cmdPrint("bash %s nat_policy" % CONFIG)
        switch.cmdPrint("bash %s flows" % CONFIG)
        switch.cmdPrint("bash %s apply 3 2" % CONFIG)
        break


    info('****Starting terms for every node\n')

    info('****Runing CLI\n')
    CLI(net)
    net.stop()



if __name__ == '__main__':
    setLogLevel('info')
    CreateNet()
