v=$1
debug="./debug$v.txt"
config="./config$v.txt"
rules="./rules$v.txt"
id2ip="./id2ip.txt"
vip2ip="./vip2ip.txt"


echo "grep \"p:\|root\|leaf\" $debug > $config"
grep "p:\|root\|leaf" $debug > $config
echo "python u32_rules $v $config $id2ip $vip2ip $rules"
python u32_rules.py $v $config $id2ip $vip2ip $rules