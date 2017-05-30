from mininet.topo import Topo
from mininet.node import RemoteController, Host
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.log import setLogLevel, info, debug
import shlex, subprocess

HSWITCH = "hswitch"
SSWITCH1 = "sswitch1"
SSWITCH2 = "sswitch2"
S1 = "s1"
S2 = "s2"
CLIENT1 = "client1"
CLIENT2 = "client2"
SERVER1 = "server1"
SERVER2 = "server2"


class NiagaraTopo(Topo):

    def __init__(self):

        Topo.__init__(self)
        print "AAaaaa"

        self.nSwitches = 3
        self.nHostPerSwitch = 2

        sswitch1 = self.addHost(SSWITCH1)
        sswitch2 = self.addHost(SSWITCH2)
        client1 = self.addHost(CLIENT1)
        client2 = self.addHost(CLIENT2)
        server1 = self.addHost(SERVER1)
        server2 = self.addHost(SERVER2)

        hswitch = self.addSwitch(HSWITCH, dpid = "0000000000000001")
        s1 = self.addSwitch(S1, dpid = "0000000000000002")
        s2 = self.addSwitch(S2, dpid = "0000000000000003")

        self.addLink(client1, hswitch)
        self.addLink(client2, hswitch)
        self.addLink(sswitch1, s1)
        self.addLink(server1, s1)
        self.addLink(sswitch2, s2)
        self.addLink(server2, s2)
        self.addLink(hswitch, s1)
        self.addLink(hswitch, s2)

def niagaraPing(net):

    ipMap = {CLIENT1:['10.0.1.1'], CLIENT2:['10.1.1.1'],
             SERVER1:['10.2.1.1'], SERVER2:['10.3.1.1'],
             SSWITCH1:['10.4.1.1'], SSWITCH2:['10.5.1.1']}
#             HSWITCH:['10.0.1.2', '10.0.1.3', '192.168.0.1', '192.168.1.1'],
#             S1:['10.2.1.2', '10.4.1.2', '192.168.0.2'],
#             S2:['10.3.1.2', '10.5.1.2', '192.168.1.2']}

    for host in net.hosts:
        info('%s \t -> \t' % host.name)
        for key,value in ipMap.items():
            if (key != host.name):
                for ip in value:
                    result = host.cmd("ping -c 1 %s" % ip)
                    sent, received = net._parsePing(result)
                    if received > sent:
                        info('*** Error: receive too many icmp packets')
                    info('%s:%d\t' % (key, received))
        info('\n')

def NiagaraNet():
    topo = NiagaraTopo()
    net = Mininet(topo=NiagaraTopo(),
#                  host = CPULimitedHost,
                  controller=lambda name:RemoteController(name,ip='127.0.0.1'));

    info('****Starting network\n')
    net.start()
    
    hostName = [CLIENT1, CLIENT2, SSWITCH1, SSWITCH2, SERVER1, SERVER2]
    hswitch = net.get(HSWITCH)

    # config host ip
    info('****config host ip\n')
#    for hostname in hostName:
#        host = net.getHost(hostname)
    for host in net.hosts:
        hostname = host.name
        host.cmdPrint("bash /home/niagara/ipHosts.sh %s" % hostname)

    # set openflow protocol
    info('****set openflow protocol\n')
    hswitch.cmdPrint("bash /home/niagara/brSwitches.sh")

    # start controller
#    info('****start controller')
    # hswitch.cmdPrint("./startRyu.sh " + "rest_router")
#    subprocess.call(["bash /home/niagara/startRyu.sh","rest_router"], shell=True)
    # config switch ip
    info('****config switch ip\n')
    hswitch.cmdPrint("bash /home/niagara/ipSwitches.sh")

    # config host routes
    info('****config host routes\n')
#    for hostname in hostName:
#        host = net.getHost(hostname)
    for host in net.hosts:
        hostname = host.name
        host.cmdPrint("bash /home/niagara/routeHosts.sh %s" % hostname)

    # set switch gw
    info('****set switch gw\n')
    hswitch.cmdPrint("bash /home/niagara/gwSwitches.sh")
    # set switch route
    info('****config switch routes\n')
    hswitch.cmdPrint("bash /home/niagara/routeSwitches.sh")

    info('****Starting terms for every node\n')
    net.startTerms()

    info('****Test connectivity\n')
    niagaraPing(net)

    info('****Runing CLI\n')
    CLI(net)
    net.stop()



topos = { 'niagaratopo': (lambda: NiagaraTopo()) }

if __name__ == '__main__':
    setLogLevel('info')
    NiagaraNet()
