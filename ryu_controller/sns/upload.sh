
file1=tbd.summary
file2=tbd.ecmp
file3=tbd.flow
while [ true ];
do
scp -i ~/.ssh/nkang_sns52_simple mininet@192.168.56.101:/home/niagara/ecmp_router/analysis/$file1 ./$file1
scp -i ~/.ssh/nkang_sns52_simple ./$file1 nkang@cycles.cs.princeton.edu:public_html/backdoor/$file1

scp -i ~/.ssh/nkang_sns52_simple mininet@192.168.56.101:/home/niagara/ecmp_router/analysis/$file2 ./$file2
scp -i ~/.ssh/nkang_sns52_simple ./$file2 nkang@cycles.cs.princeton.edu:public_html/backdoor/$file2

scp -i ~/.ssh/nkang_sns52_simple mininet@192.168.56.101:/home/niagara/ecmp_router/analysis/$file3 ./$file3
scp -i ~/.ssh/nkang_sns52_simple ./$file3 nkang@cycles.cs.princeton.edu:public_html/backdoor/$file3

sleep 15
done