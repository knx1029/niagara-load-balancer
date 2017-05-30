import sys

def  combine(f1, f2, f3, v):
  in1 = open(f1, 'r')
  in2 = open(f2, 'r')
  out = open(f3, 'w')

  in1.readline()
  in2.readline()
  out.write("version = {}\n".format(v))

  read1 = True
  str = in1.readline()
  while (read1):
    out.write(str)
    str = in1.readline()
    if ('switch' in str):
      read1 = False

  in2.readline()
  str = in2.readline()
  while (not ('switch' in str)):
    str = in2.readline()

  while (str):
    out.write(str)
    str = in2.readline()

  in1.close()
  in2.close()
  out.close()


f = "rules{}.txt"
a = sys.argv[1]
b = sys.argv[2]
c = a + b
f1 = f.format(a)
f2 = f.format(b)
f3 = f.format(c)
combine(f1, f2, f3, c)
