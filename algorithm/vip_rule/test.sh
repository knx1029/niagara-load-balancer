#"tests/multiple_vips"
#C="100 200 300 400 500 600 700 800 900 1000"
fold=mvip_data/

if [ "$1" == "packing" ]; then
arg=heu
ecmp=max
for w in b; do
for j in 256; do #5 10; do
for v in 100; do #800 300; do
for t in 300; do
   folder="${fold}weight$j"
   input="$folder/w${j}_${w}_${v}"
   traffic="$fold/v${v}_zipf${t}"
   output="$folder/w${j}_${w}_v${v}_zipf${t}_out_ecmp_prime_$arg.csv"
   debug="$folder/w${j}_${w}_v${v}_zipf${t}_debug_ecmp_prime_$arg"
   echo $input $traffic $output
   python main.py -mode multi_vip -input $input -traffic $traffic -output $output -debug $debug -ecmp $ecmp -$arg
done
done
done
done
fi

if [ "$1" == "grouping" ]; then
arg=heu
for v in 100; do #100 300 500; do
for t in 300; do
for w in b; do
for j in 256; do #128 256; do
for g in 11 13; do
   folder="${fold}weight$j"
   input="$folder/w${j}_${w}_${v}"
   traffic="${fold}v${v}_zipf${t}"
   output="$folder/w${j}_${w}_v${v}_g${g}_zipf${t}_out_prime_${arg}.csv"
   debug="$folder/w${j}_${w}_v${v}_g${g}_zipf${t}_debug_prime_${arg}"
   echo $input $traffic $output
   python main.py -mode grouping -group $g -input $input -traffic $traffic -output $output -debug $debug -$arg
done
done
done
done
done
fi

if [ "$1" == "weight" ]; then
folder=svip_data
arg=bf
for e in  0.01 0.001 0.0001; do 
   input="$folder/e_${e}"
   output="$folder/e_${e}_out.csv"
   debug="$folder/e_${e}_debug"
   echo $input $output
   python main.py -mode single_vip -input $input -output $output -debug $debug -ecmp none -$arg
done
fi


if [ "$1" == "vip" ]; then
folder=svip_data
algo_arg=heu
arg=heu
for j in  8; do # 15; do # 8; do
   input="$folder/w${j}_100k"
   output="$folder/w${j}_100k_out_$arg.csv"
   debug="$folder/w${j}_100k_debug_$arg"
   echo $input $output
   python main.py -mode single_vip -input $input -output $output -debug $debug -ecmp none -$algo_arg
done
fi

if [ "$1" == "update" ]; then
folder=svip_data/update
algo_arg=heu
for v in 10000; do
for s in del; do 
for w in b; do
for j in 16; do
for ecmp in none; do
   input=${folder}/${s}_w${j}_${w}_${v}
   output=${folder}/${s}_w${j}_${w}_${v}_${ecmp}_out_${algo_arg}.csv
   echo $input $output
   python main.py -mode update -input $input -output $output -ecmp $ecmp -$algo_arg
done
done
done
done
done
fi

if [ "$1" == "stair" ]; then
   folder=svip_data
   arg=bf
   input="$folder/w_stair"
   output="$folder/w_stair_out_$arg.csv"
   debug="$folder/w_stair_debug_$arg"
   echo $input $output
   python main.py -mode vip_stair -input $input -output $output -debug $debug -ecmp none -$arg
fi


