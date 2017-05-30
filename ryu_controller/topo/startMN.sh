echo "-s for server; -c for client; -t for topology"
p=12345

if [ "$2" != "" ]; then
    p=$2
fi

if [ "$1" == "-c" ]; then
    iperf -c 192.168.6.6 -p $p -u -b 1M -t 600
elif [ "$1" == "-s" ]; then
    iperf -s -p $p
elif [ "$1" == "-t" ]; then
#    python HwTopo.py
    python NgTopo.py
fi
