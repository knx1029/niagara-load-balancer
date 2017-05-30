op=$1

if [ "$op" == "help" ]; then
  echo "startserver port_begin port_end"
  echo "showswitch port_begin port_end"
  echo "clearswitch port_begin port_end"
  echo "updateversion old_version new_version t1 t2"
fi

if [ "$op" == "startserver" ]; then
  start=$2
  end=$3
  for ((i=$start; i<=$end; i++)) do
    echo "iperf3 -s --daemon -p $i"
    iperf3 -s --daemon -p $i
  done
fi

if [ "$op" == "clearserver" ]; then
   echo "show id"
   ps aux | grep iperf3
fi


if [ "$op" == "showswitch" ]; then
  start=$2
  end=$3
  for ((i=$start; i<=$end; i++)) do
    echo "conntrack -L -p tcp --dport=$i"
    conntrack -L -p tcp --dport=${i}
  done
fi

if [ "$op" == "clearswitch" ]; then
  start=$2
  end=$3
  for ((i=$start; i<=$end; i++)) do
    echo "conntrack -D -p tcp --dport=$i"
    conntrack -D -p tcp --dport=${i}
  done
fi

if [ "$op" == "updateversion" ]; then
  a=$2
  b=$3
  t1=$4
  t2=$5
  sleep $t1
  ./ng-setupall.sh updatevipversion "$a" "$a$b"
  sleep $t2
  ./ng-setupall.sh updatevipversion "$a$b" "$b"
fi
