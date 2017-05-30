echo "{svip}"
folder="./res/svip/rand_int1k"
echo "$folder"

if [ "$1" == "tsvip" ]; then
  #for w in 2 3 4 .. 32
  echo "s"
  for w in 8;
  do
      t=100k
      v=100000
      e=0.001
      input="./svip_data/w8_100k"
      output="./svip_data/res_w${w}_${t}"
      echo "run ${t} of ${w} weights to ${output}"
      ./main -i r -t s -v $v -w $w -e $e < $input > $output
   done
fi



if [ "$1" == "svip" ]; then
  #for w in 2 3 4 .. 32
  echo "s"
  for w in 2 3 4 5 6 7 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32
  do
      t=100k
      v=100000
      e=0.001
      output="./svip_data/res_w${w}_${t}"
      echo "run ${t} of ${w} weights to ${output}"
      ./main -i g -t s -v $v -w $w -e $e > $output
   done
fi


if [ "$1" == "mvip" ]; then
  #for w in 2 3 4 .. 32
  echo "m"
  for w in 8; do #16; do
      for v in 500; do #100 500; do
	  for t in g a b; do
	      for f in u s; do	  
		  e=0.001
		  input="mvip_data/weight${w}/w${w}_${t}_${v}"
		  output="mvip_data/weight${w}/w${w}_${t}_${v}_ecmp_${f}.csv"
		  echo "run ${v} of ${w} weights of ${t} to ${output}"
		  echo "./main -i r -t m -v $v -w $w -d $w 3 -e $e -f $f -r 100 4001 100 < $input > $output"

		  ./main -i r -t m -v $v -w $w -d $w 3 -e $e -f $f -r 100 4001 100 < $input > $output

		  output="mvip_data/weight${w}/w${w}_${t}_${v}_none_${f}.csv"
		  echo "run ${v} of ${w} weights of ${t} to ${output}"
		  echo "./main -i r -t m -v $v -w $w -e $e -f $f -r 100 4001 100 < $input > $output"
		  ./main -i r -t m -v $v -w $w -e $e -f $f -r 100 4001 100 < $input > $output

	      done
	  done
      done
   done
fi



if [ "$1" == "group" ]; then
  #for w in 2 3 4 .. 32
  echo "g"
  for w in 16; do
      for v in 10000; do
#	  for t in g a b; do
	  for t in b; do
	      for f in s; do	  
		  e=0.001
		  vs=10k
		  input="mvip_data/weight${w}/w${w}_${t}_${vs}"
		  
		  output="mvip_data/weight${w}/w${w}_${t}_${vs}_ecmp_${f}.csv"
		  echo "run ${v} of ${w} weights of ${t} to ${output}"
		  echo "./main -i r -t m -v $v -w $w -d $w 4 -e $e -f $f -r 100 4001 100 < $input > $output"

#		  ./main -i r -t m -v $v -w $w -d $w 4 -e $e -f $f -r 100 4001 100 < $input > $output


#		  for g in 100 200 300 400 500 600; do # 100 200 300; do
		  for g in 500; do
		      output="mvip_data/weight${w}/w${w}_${t}_${vs}_ecmp_g${g}_${f}.csv"
		      echo "run ${v} of ${w} weights of ${t} to ${output}"
		      echo "./main -i r -t g -g $g -v $v -w $w -d $w 4 -e $e -f $f -r 100 4001 100 < $input > $output"
		      
#		      ./main -i r -t g -g $g -v $v -w $w -d $w 4 -e $e -f $f -r 100 4001 100 < $input > $output
		      ./main -i r -t g -g $g -v $v -w $w -d $w 4 -e $e -f $f -r 4000 4001 100 < $input
		      
		  done
	      done
	  done
      done
   done
fi


if [ "$1" == "more" ]; then
  #for w in 2 3 4 .. 32
  echo "m"
  for w in 64; do
      for v in 500; do
	  for t in b; do
	      for f in s; do	  
		  e=0.001
		  input="mvip_data/weight${w}/w${w}_${t}_${v}"

#		  for g in 10 20 30 40 50 60 70 80 90; do
		  for g in 140; do
		      output="mvip_data/weight${w}/w${w}_${t}_${vs}_ecmp_g${g}_${f}.csv"
		      echo "run ${v} of ${w} weights of ${t} to ${output}"
		      echo "./main -i r -t g -g $g -v $v -w $w -d $w 8 -e $e -f $f -r 100 4001 100 < $input > $output"
		      
#		      ./main -i r -t g -g $g -v $v -w $w -d $w 8 -e $e -f $f -r 100 4001 100 < $input > $output
		      ./main -i r -t g -g $g -v $v -w $w -d $w 6 -e $e -f $f -r 4000 4001 100 < $input
		  done
	      done
	  done
      done
   done
fi
