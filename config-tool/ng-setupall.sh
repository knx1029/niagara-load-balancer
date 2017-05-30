# TODO
op=$1
LOG="NG_log"
vip="192.168.124.2"

# hwswitch: 10.99.88.80
# sswitch1: 10.99.88.81
# sswitch2: 10.99.88.82
# be1:      10.99.88.83
# be2:      10.99.88.84


# transfer setup script
local_exe=ng-setup.py
exe="./bin/$local_exe"


echo "op = $op"
timestamp=$(date +%T)

if [ "$op" == "help" ]; then
  echo  op choices: 
  echo  copysetup
  echo  cleanlog
  echo  addbe/delbe
  echo  disconnsw/connsw \$vtag
  echo  installroutes \$version
  echo  installberoutes \$version
  echo  updatevipversion \$old_version \$new_version
fi

if [ "$op" == "cleanlog" ]; then
  echo "" > $LOG
fi

if [ "$op" == "copysetup" ]; then
  echo "tranferring setup script"
  for host in "hwswitch" "sswitch1" "sswitch2" "be1" "be2"; do
    scp $local_exe $host.niagara:$exe
    out=$?
    if [$out -ne 0]; then
      echo "exception $out, operation terminated.."
      exit $out
    fi
  done
fi


# invoke setup script on each machine

## connect all sw and hw
if [ "$op" == "connsw" ] || [ "$op" == "disconnsw" ]; then 
  vtag=$2
  echo "$timestamp OP >> $op $vtag" >> $LOG
  for host in "hwswitch" "sswitch1" "sswitch2"; do

    echo "      @ $host" >> $LOG

    # add tunnels between sw
    echo ssh $host.niagara "sudo python $exe $host $op $vtag"
    ssh $host.niagara "sudo python $exe $host $op $vtag"
    out=$?
    if [$out -ne 0]; then
      echo "exception $out, operation terminated.." >> $LOG
      exit $out
    fi

    # dump interface & tunnel information
    echo "         TUNNELS" >> $LOG
    echo ssh $host.niagara "sudo ifconfig | grep \"\.$vtag Link\""
    ssh $host.niagara "sudo ifconfig | grep \"\.$vtag Link\"" >> $LOG

    # dump iptable chains
    echo "         RULES" >> $LOG
    echo ssh $host.niagara "sudo iptables -L PREROUTING -n -t mangle -v"
    ssh $host.niagara "sudo iptables -L PREROUTING -n -t mangle -v" >> $LOG
    echo ssh $host.niagara "sudo iptables -L NG_RX_V$vtag -n -t mangle"
    ssh $host.niagara "sudo iptables -L NG_RX_V$vtag -n -t mangle" >> $LOG
    echo "" >> $LOG
  done
  echo "" >> $LOG
fi

## be-related actions perforemd on sw and be
if [ "$op" == "addbe" ] || [ "$op" == "delbe" ]; then
  echo "$timestamp OP >> $op" >> $LOG

  for host in "sswitch1" "sswitch2" "be1" "be2"; do
    echo "      @ $host" >> $LOG

    # add/del tunnels between sw and be
    echo ssh $host.niagara "sudo python $exe $host $op"
    ssh $host.niagara "sudo python $exe $host $op"
    out=$?
    if [$out -ne 0]; then
      echo "exception $out, operation terminated.." >> $LOG
      exit $out
    fi

    # dump interface & tunnel information
    echo "         TUNNELS" >> $LOG
    echo ssh $host.niagara "sudo ifconfig | grep \"\.0 Link\""
    ssh $host.niagara "sudo ifconfig | grep \"\.0 Link\"" >> $LOG
    echo "" >> $LOG
  done
  echo "" >> $LOG
fi

# be, installroutes eth0 $rules 1
if [ "$op" == "installroutes" ]; then
  version=$2
  local_rule="rules$version.txt"
  remote_rule="./bin/$local_rule"

  echo "$timestamp OP >> $op $version" >> $LOG
  for host in "hwswitch" "sswitch1" "sswitch2"; do
    echo "      @ $host" >> $LOG

    # transfer rules
    echo "copying rules"
    scp $local_rule $host.niagara:$remote_rule
    out=$?
    if [$out -ne 0]; then
      echo "exception $out, operation terminated.." >> $LOG
      exit $out
    fi
 
    # install rules
    echo ssh $host.niagara "sudo python $exe $host $op $remote_rule"
    ssh $host.niagara "sudo python $exe $host $op $remote_rule"
    out=$?
    if [$out -ne 0]; then
      echo "exception $out, operation terminated.." >> $LOG
      exit $out
    fi

    # dump iptables chain 
    echo "         RULES" >> $LOG
    echo ssh $host.niagara "sudo iptables -L NG_RX_V$version -n -t mangle"
    ssh $host.niagara "sudo iptables -L NG_RX_V$version -n -t mangle" >> $LOG
    echo "" >> $LOG
  done
  echo "" >> $LOG
fi


# be, installroutes eth0 $rules 1
if [ "$op" == "installberoutes" ]; then
  version=$2
  local_rule="rules$version.txt"
  remote_rule="./bin/$local_rule"

  echo "$timestamp OP >> $op $version" >> $LOG
  for host in "be1" "be2"; do
    echo "      @ $host" >> $LOG

    # transfer rules
    echo "copying rules"
    scp $local_rule $host.niagara:$remote_rule
    out=$?
    if [$out -ne 0]; then
      echo "exception $out, operation terminated.." >> $LOG
      exit $out
    fi

    # install rules
    echo ssh $host.niagara "sudo python $exe $host $op $remote_rule"
    ssh $host.niagara "sudo python $exe $host $op $remote_rule"
    out=$?
    if [$out -ne 0]; then
      echo "exception $out, operation terminated.." >> $LOG
      exit $out
    fi

    # dump
    echo "         RULES" >> $LOG
    echo ssh $host.niagara "sudo iptables -L NG_tcp_signals -n -t mangle"
    ssh $host.niagara "sudo iptables -L NG_tcp_signals -n -t mangle" >> $LOG
    echo "" >> $LOG
  done
  echo "" >> $LOG
fi


if [ "$op" == "updatevipversion" ]; then
  old_version=$2
  version=$3
  echo "$timestamp OP: $op $old_version $version" >> $LOG

  for host in "hwswitch"; do
    echo "      @ $host" >> $LOG

    echo ssh $host.niagara "sudo python $exe $host $op $vip $old_version $version"
    ssh $host.niagara "sudo python $exe $host $op $vip $old_version $version"
    out=$?
    if [$out -ne 0]; then
      echo "exception $out, operation terminated.." >> $LOG
      exit $out
    fi

    # dump match
    echo "         RULES" >> $LOG
    echo ssh $host.niagara "sudo iptables -L PREROUTING -n -t mangle -v"
    ssh $host.niagara "sudo iptables -L PREROUTING -n -t mangle -v" >> $LOG
    echo "" >> $LOG
  done
  echo "" >> $LOG
fi

