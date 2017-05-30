./ng-vlan installberoutes eth0 rules${1}.txt
iptables -D PREROUTING -t mangle -j NG_tcp_signals
iptables -I PREROUTING -t mangle -j NG_tcp_signals
