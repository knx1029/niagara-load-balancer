import math
import random
import sys

SEED = 29

# generate 
# single_vip: l %output_file %n_tests %n_weights %tolerable_error
# multiple_vip: m %output_file %n_vips %n_weights %C
# update: u %output_file %n_tests %n_weights %tolerable_error %mode
# randomized traffic: randt %output_file %n_tests %n_vips
# log-shaped traffic: logt %output_file %n_tests %n_vips
# compare churn with ecmp: ea|ed %output_file %n_weights_start %n_weights_end

def normalize(ws):
  total = sum(ws)
  nws = map(lambda(x):x/total, ws)
  return nws

def bimodel_x():
    toss = random.choice((1, 2))
    if (toss == 1):
      return random.gauss(4, 1.0)
    else:
#      return random.gauss(60, 1.0)
      return random.gauss(16, 1.0)

def gaussian_(n_weights):
    or_w, total  = [], 0.0
    for j in range(n_weights):
      x = -1
      while (x < 0):
        x = random.gauss(4, 1.0)
#        x = random.gauss(4, 0.2)
      or_w.append(x)
    ws = normalize(or_w)
    return ws

def bimodel_(n_weights):
    or_w, total  = [], 0.0
    for j in range(n_weights):
      x = -1
      while (x < 0):
        x = bimodel_x()
      or_w.append(x)
    ws = normalize(or_w)
    return ws

def alloc_(n_weights):
    or_w  = [0.0] * n_weights
    l = random.randint(1, n_weights)
    J = random.sample(range(n_weights), l)

    total = 0.0
    for j in J:
      x = -1.0
      while (x < 0):
        x = bimodel_x()
      or_w[j] = x
    ws = normalize(or_w)
    return ws


if (sys.argv[1] == 'h'):
  print "single weight: w $input $e"
  print "single vip: l $input $n_tests $n_weights $e"
  print "update: u $input $n_tests $n_weights $e $mode=[g,b,a]"
  print "multiple vips: m $input $nvips $n_weights $mode=[g,b,a]"
  print "zipf traffic: zipf $input $nvips $scale"
  print "compare with ecmp churn: $e=[ea,ed] $input $n_weights_start $n_weights_end"

elif (sys.argv[1] == 'w'):
  input_file = sys.argv[2]
  tolerable_error = float(sys.argv[3])

  w1 = 0.0
  step = tolerable_error * 0.5
  ws = []
  while (w1 <= 1.0):
    w2 = 1.0 - w1
    ws.append((w1, w2))
    w1 = w1 + step

  n_tests = len(ws)
  f = open(input_file, 'w')
  f.write('l {}\n'.format(n_tests))

  for (w1, w2) in ws:
    f.write("{} {}\n".format(2, tolerable_error))
    f.write("{} {}\n".format(w1, w2))
  f.close()


elif (sys.argv[1] == 'l'):
  input_file = sys.argv[2]
  n_tests = int(sys.argv[3])
  n_weights = int(sys.argv[4])
  tolerable_error = float(sys.argv[5])

  f = open(input_file, 'w')
  f.write('l {}\n'.format(n_tests))

  random.seed(SEED)
  tests = dict()
  i = 0
  CEIL = 50

  while (True):
    if (i >= n_tests):
      break
    int_w, total = [], 0.0
    str_w = 0
    ceil = CEIL
    for j in range(n_weights):
      x = random.randint(1, ceil)
      total = total + x
      ceil = x
      int_w.append(x)
      str_w = str_w * CEIL + x
    if str_w in tests:
      continue
    tests[str_w] = True

    ws = map(lambda(x):x/total, int_w)
    f.write('{} {}\n'.format(n_weights, tolerable_error))

    for k in ws:
      f.write('{} '.format(k))
    f.write('\n')
    i = i + 1

  f.close()

elif (sys.argv[1] == 'l1'):
  input_file = sys.argv[2]
  n_tests = int(sys.argv[3])
  n_weights = int(sys.argv[4])
  tolerable_error = float(sys.argv[5])
  var = float(sys.argv[6])
  f = open(input_file, 'w')
  f.write('l {}\n'.format(n_tests))
  random.seed(SEED)
  for i in range(n_tests):
    # log individual weights
    f_ws = open(input_file+str(i), 'w')
    f_ws.write('l 1\n')

    ws, total = [], 0.0
    avg_weight = 1.0 / n_weights
    lb = avg_weight*(100.0 - var) / 100.0
    ub = avg_weight*(100.0 + var) / 100.0
    for j in range(n_weights - 1):
      x = random.uniform(lb, ub)
      total = total + x
      ws.append(x)
    # last weight has to complete previous weights to 1
    ws.append(1 - total)

    f.write('%d %f\n' % (n_weights, tolerable_error))
    f_ws.write('%d %f\n' % (n_weights, tolerable_error))
    for k in ws:
      f.write('%.3lf ' % k)
      f_ws.write('%.3lf ' % k)
    f.write('\n')

    f_ws.write('\n')
    f_ws.close()
  f.close()


elif (sys.argv[1] == 'm'):

  input_file = sys.argv[2]
  n_vips = int(sys.argv[3])
  n_weights = int(sys.argv[4])
  mode = sys.argv[5]
  C = map(lambda(x):x * 50, range(1, 40))

  f = open(input_file, 'w')
  f.write('m {} {}'.format(n_weights, n_vips))
  for c in C:
    if c >= n_vips:
      f.write(' {}'.format(c))
  f.write('\n')

  random.seed(SEED)
  for i in range(n_vips):
    or_w, total = [], 0.0
    ws = None
    if (mode == "g"):
      ws = gaussian_(n_weights)
    elif (mode == "b"):
      ws = bimodel_(n_weights)
    elif (mode =='a'):
      ws = alloc_(n_weights)
    else:
      pass

    for k in ws:
      f.write('{} '.format(k))
    f.write('\n')

  f.close()

elif (sys.argv[1] == 'u'):

  input_file = sys.argv[2]
  n_sets = int(sys.argv[3])
  n_weights = int(sys.argv[4])
  error = float(sys.argv[5])
  mode = sys.argv[6]

  f = open(input_file, 'w')
  f.write('l {}\n'.format(n_sets))

  random.seed(SEED)
  for i in range(n_sets):
    or_w, total = [], 0.0
    ws = None
    cnt = 0
    if (mode == "g"):
      ws = gaussian_(n_weights)
    elif (mode == "b"):
      ws = bimodel_(n_weights)
    elif (mode =='a'):
      while cnt <= 1:
        ws = alloc_(n_weights)
        cnt = 0
        for w in ws:
          if (w > 0):
            cnt = cnt + 1
    else:
      pass


    nws = ws[:]
    while (True):
      idx = random.randint(0, n_weights - 1)
      if (nws[idx] > 0):
        nws[idx] = 0.0
        break
    nws = normalize(nws)

    # the second set
    f.write('{} {}\n'.format(n_weights, error))
    f.write(' '.join('{}'.format(k) for k in nws))
    f.write('\n')

    # the first set
    f.write('{} {}\n'.format(n_weights, error))
    f.write(' '.join('{}'.format(k) for k in ws))
    f.write('\n')

    
    

  f.close()


elif (sys.argv[1] == 'randt'):
  input_file = sys.argv[2]
  n_tests = int(sys.argv[3])
  n_vips = int(sys.argv[4])

  f = open(input_file, 'w')
  f.write('{}\n'.format(n_tests))

  random.seed(SEED)
  for i in range(n_tests):
    int_w, total = [], 0.0
    for j in range(n_vips):
      x = random.randint(1, 30)
      total = total + x
      int_w.append(x)

    ws = map(lambda(x):x/total, int_w)

    for k in ws:
      f.write('{} '.format(k))
    f.write('\n')

  f.close()

elif (sys.argv[1] == 'zipf'):
  input_file = sys.argv[2]
  n_vips = int(sys.argv[3])
  first_last_gap = float(sys.argv[4])

  f = open(input_file, 'w')
  f.write('1\n')

  rank = dict()
  random.seed(SEED)

  # more 
  hits, total = [], 0.0
  hits_rank_last = 1e3
  hits_rank_first = hits_rank_last * first_last_gap
  rank_vips = 1000

  a = math.log10(hits_rank_first / hits_rank_last)
  b = math.log10(rank_vips)
  c = b * math.log10(hits_rank_first)
  print "traffic pattern: {}x + {}y = {}".format(a, b, c)
  for i in range(n_vips):
    rank[i] = i
    # formulate traffic pattern
    x = math.log10((i + 1) * 1.0)
    y = math.pow(10, (c - a * x) / b)
    total = total + y
    hits.append(y)
    
  ws = map(lambda(x):x/total, hits)

  # permutation
#  for j in range(n_vips * 10):
#    x = random.randint(0, n_vips - 2)
#    y = random.randint(x + 1, n_vips - 1)
#    rx, ry = rank[x], rank[y]
#    rank[x], rank[y] = ry, rx


  for j in range(n_vips):
    f.write('{} '.format(ws[rank[j]]))
    if (rank[j] == 0): 
      print j
  f.write('\n')

  f.close()


elif (sys.argv[1] == 'pareto'):
  input_file = sys.argv[2]
  n_tests = int(sys.argv[3])
  n_vips = int(sys.argv[4])

  f = open(input_file, 'w')
  f.write('{}\n'.format(n_tests))

  random.seed(SEED)
 
  rank = dict()
  # bigger alpha expands the discrepancy among weights
  # bigger beta limits the number of bigger weights
  alpha, beta = 3.0, 1.0
  hits, total = [], 0.0

  print "traffic pattern: alpha = {}, beta = {}".format(alpha, beta)
  for i in range(n_vips):
    rank[i] = i
    y = random.paretovariate(alpha)
    # formulate traffic pattern
#    x = random.random() * beta + 1.0
#    y =  math.pow(1/x, alpha)
    total = total + y
    hits.append(y)
  
  hits.sort(reverse = True)

  print hits
  ws = map(lambda(x):x/total, hits)
  print ws

  for i in range(n_tests):
    # permutation
    for j in range(n_vips * 10):
      x = random.randint(0, n_vips - 2)
      y = random.randint(x + 1, n_vips - 1)
      rx, ry = rank[x], rank[y]
      rank[x], rank[y] = ry, rx

    print rank

    for j in range(n_vips):
      f.write('{} '.format(ws[rank[j]]))
    f.write('\n')

  f.close()

elif (sys.argv[1] == "ea" or sys.argv[2] == "ed"):
  input_file = sys.argv[2]
  n_weights_s = int(sys.argv[3])
  n_weights_e = int(sys.argv[4])

  f = open(input_file, 'w')
  tests = []
  for n_weights in range(n_weights_s, n_weights_e + 1):
    ws = [1.0] * n_weights
    ws = normalize(ws)
    for idx in range(0, n_weights):
      nws = ws[:]
      nws[idx] = 0.0
      nws = normalize(nws)
      if (sys.argv[1] == "ea"):
        # the second set
        tests.append(nws)
        # the first set
        tests.append(ws)
      else:
        # the first set
        tests.append(ws)
        # the second set
        tests.append(nws)


  f.write('l {}\n'.format(len(tests)))
  error = 0.001
  for test in tests:
    f.write('{} {}\n'.format(len(test), error))
    f.write(' '.join('{}'.format(k) for k in test))
    f.write('\n')


  f.close()

else:
  pass
