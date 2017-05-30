file=$2

if [ "$1" == "t" ]; then
for host in "hwswitch" "sswitch1" "sswitch2" "be1" "be2" "client1" "client2"; do
#for host in "hwswitch" "sswitch2" "be1" "be2" "client1" "client2"; do
#for host in "client1" "be1" "be2"; do
  file1=$file
  echo  scp $file $host.niagara:bin/$file1
  scp $file $host.niagara:bin/$file1
done
fi

if [ "$1" == "f" ]; then
host="$3"
echo  scp $host.niagara:data/$file ${host}_$file
scp $host.niagara:data/$file data/${host}_${file}
fi
