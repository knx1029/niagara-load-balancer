import sys
from operator import *

def copy(infile, outfile):
  fin = open(infile, 'r')
  fout = open(outfile, 'w')

  while (True):
    str = fin.readline()
    if (str == None or len(str) == 0):
      break
#    strs = str.rsplit('\n')
#    for s in strs:
#      print s
    fout.write("{}".format(str))
    fout.write("{}".format(str))

  fin.close()
  fout.close()

def stair(infile, outfile):
  fin = open(infile, 'r')
  fout = open(outfile, 'w')

  first = True
  last_key = 0
  while True:
    str = fin.readline()
    if (str == None or len(str) == 0):
      break

    if not first:
      tokens = strs.rsplit(',')
      for i in range(len(tokens)):
        if i > 0:
          fout.write(",")
        if (i == key_idx):
          fout.write(last_key)
          last_key = tokens[i]
        else:
          fout.write(tokens[i])

    fout.write(str)
    first = False

  fin.close()
  fout.close()

def count(infile, outfile):
  fin = open(infile, 'r')
  fout = open(outfile, 'w')

  sample = dict()
  count = dict()
  title = fin.readline()
  total = 0
  while True:
    str = fin.readline()
    if (str == None or len(str) == 0):
      break
    tokens = str.rsplit(',')
    num = int(tokens[key_idx])
    total = total + 1
    if not(num in sample):
      sample[num] = str
      count[num] = 1
    else:
      count[num] = count[num] + 1

  fout.write("num_rules, num_tests, status, {}".format(title))
  now = 0
  for num in sorted(count):
    c = count[num]
    example = sample[num]
    now = now + c
    if (now - c < total / 2 and now >= total / 2):
      fout.write("{},{},median,{}".format(num, c, example))
    else:     
      fout.write("{},{},,{}".format(num, c, example))

  fin.close()
  fout.close()


def compare(infile1, infile2, outfile):
  fin1 = open(infile1, 'r')
  fin2 = open(infile2, 'r')
  fout = open(outfile, 'w')

  title = fin1.readline()
  fin2.readline()
  list = None
  max_diff, tie_num1 = 0, 0
  while True:
    str1 = fin1.readline()
    if (str1 == None or len(str1) == 0):
      break
    tokens1 = str1.rsplit(',')
    num1 = int(tokens1[key_idx])

    str2 = fin2.readline()
    tokens2 = str2.rsplit(',')
    num2 = int(tokens2[key_idx])

    if (num2 - num1 > max_diff or (num2 - num1 == max_diff and num1 > tie_num1)):
      max_diff = num2 - num1
      tie_num1 = num1
      list = str1

  fout.write("diff,{}".format(title))
  fout.write("{}, {}".format(max_diff, list))

  fin1.close()
  fin2.close()
  fout.close()


def merge(infiles, outfile, col):
  table = []
  fout = open(outfile, 'w')
  fout.write("#rules")
  nums = [8, 30, 50, 70] + map(lambda(x):50 * x, range(2, 40))
  for idx in range(len(infiles)):
    print infiles[idx]
    infile = infiles[idx]
    fout.write(",{}".format(infile))
    fin = open(infile, 'r')
    fin.readline()
    jdx = 0
    while True:
      str = fin.readline()
      if (str == None or len(str) == 0):
        break
      tokens = str.rsplit(',')
      num = int(tokens[col])
#      if not (num in nums): 
#        continue
      if (idx == 0):
        table.append([num])

      imb = float(tokens[col + 1])
      table[jdx].append(imb)
      jdx = jdx + 1

    fin.close()

  fout.write("\n")
  for entry in table:
    fout.write(",".join("{}".format(e) for e in entry))
    fout.write("\n")

  fout.close()


def filter(infile, outfile, c_idx, x_idx, y_idx):
  def output(fout, rec):
    (x0, y0) = rec[-1]
    y1 = y0
    for (x, y) in rec:
      if (x0 >= x and y1 >= y):
        y1 = y
    fout.write("{}, {}, {}, {}\n".format(c, x0, y0, y1))

  fout = open(outfile, 'w')
  fout.write("index, #rules0, churn0, best_churn\n")
  fin = open(infile, 'r')
  fin.readline()
  rec = []
  c = -1
  while True:
      str = fin.readline()
      if (str == None or len(str) == 0):
        break
      tokens = str.rsplit(',')
      c_ = int(tokens[c_idx])
      x = int(tokens[x_idx])
      y = float(tokens[y_idx])
      if (c == -1 or c_ == c):
        rec.append((x, y))
      else:
        output(fout, rec)
        rec = [(x, y)]
      c = c_

  output(fout, rec)
  fin.close()
  fout.close()


def transform(infile, outfile, c_idx, x_idx, y_idx, idxs):
  def output(fout, rec):
    rec.sort(key = itemgetter(0))
    (cx, cy, cz) = rec[0]
    ly = 100
    for (x, y, z) in rec:
      if (x > cx):
        #if (cy < ly):
          #fout.write("{}, {}, {}, {}\n".format(c, cx, cy, cz))
        cx = x
        ly = cy
      if (cx > 0.01):
        break
      if (y < cy):
        cy = y
    fout.write("{}, {}, {}, {}\n".format(c, cx, cy, cz))


  fout = open(outfile, 'w')
  fout.write("index, imbalance, churn, other_info\n")
  fin = open(infile, 'r')
  fin.readline()
  rec = []
  c = -1
  while True:
      str = fin.readline()
      if (str == None or len(str) == 0):
        break
      tokens = str.rsplit(',')
      c_ = int(tokens[c_idx])
      x = float(tokens[x_idx])
      y = float(tokens[y_idx])
      z = ','.join("{}".format(tokens[k]) for k in idxs)
      if (c == -1 or c_ == c):
        rec.append((x, y, z))
      else:
        output(fout, rec)
        rec = [(x, y, z)]
      c = c_

  output(fout, rec)

  fin.close()
  fout.close()

def extract(infile, outfile, from_idx, to_idx):
  fin = open(infile, 'r')
  fout = open(outfile, 'w')
  fin.readline()
  fout.write("index, best_churn, min_churn\n")
  for idx in range(from_idx, to_idx + 1):
    best_churn = 2.0
    min_churn = 0.0
    for c in range(0, idx):
      str = fin.readline()
      tokens = str.rsplit(',')
      churn = float(tokens[2])
      min_churn = float(tokens[3])
      if (churn < best_churn):
        best_churn = churn
    fout.write("{}, {}, {}\n".format(idx, best_churn, min_churn))
  fin.close()
  fout.close()



option = sys.argv[1]
if option == 'help':
  print "copy $infile $outfile"
  print "stair $infile $outfile [key_idx]"
  print "count $infile $outfile [key_idx]"
  print "compare $infile $outfile [key_idx]"
  print "merge $folder $outfile"
  print "filter $infile $outfile"
  print "transform $infile $outfile"
  print "extract $infile $index_file $outfile"

elif option == 'copy':
  infile = sys.argv[2]
  outfile = sys.argv[3]
  copy(infile, outfile)

elif option == 'copy':
  infile = sys.argv[2]
  outfile = sys.argv[3]
  if (len(sys.argv) > 4):
    key_idx = int(sys.argv[4])
  else:
    key_idx = 3
  stair(infile, outfile)

elif option == 'count':
  infile = sys.argv[2]
  outfile = sys.argv[3]
  if (len(sys.argv) > 4):
    key_idx = int(sys.argv[4])
  else:
    key_idx = 1
  count(infile, outfile)

elif option == 'compare':
  infile1 = sys.argv[2]
  infile2 = sys.argv[3]
  outfile = sys.argv[4]
  if (len(sys.argv) > 5):
    key_idx = int(sys.argv[5])
  else:
    key_idx = 1
  compare(infile1, infile2, outfile)


elif option == 'merge':
  ws = [64]
  vs = [500]
  ts = ["300"] 
  gs = [50, 100, 125, 150, 200]
  algos = ["heu"]
  ds = ["b"]
#  template = sys.argv[2]+"w{}_{}_v{}_zipf{}_out_ecmp_{}.csv"
#  template = sys.argv[2]+"w{}_{}_v{}_zipf{}_out_ecmp_prime_{}.csv"
  template = sys.argv[2]+"w{}_{}_v{}_g{}_zipf{}_out_prime_{}.csv"
#  template = sys.argv[2]+"w{}_{}_v{}_zipf{}_out_{}.csv"
  outfile = sys.argv[3]

  infiles = []
  for v in vs:
   for d in ds:
    for algo in algos:
     for w in ws:
      for t in ts:
       for g in gs:
#        infile = template.format(w, d, v, t, algo)
        infile = template.format(w, d, v, g, t, algo)
        infiles.append(infile)
        print infile

#  merge(infiles, outfile, 3)
  merge(infiles, outfile, 4)

elif option == "filter":
  infile = sys.argv[2]
  outfile = sys.argv[3]
  filter(infile, outfile, 0, 4, 5)


elif option == "transform":
  infile = sys.argv[2]
  outfile = sys.argv[3]
  transform(infile, outfile, 0, 8, 9, [6])
#  transform(infile, outfile, 0, 7, 8,  [])

elif option == "extract":
  infile = sys.argv[2]
  outfile = sys.argv[3]
  extract(infile, outfile, 2, 32)

else: 
  pass

