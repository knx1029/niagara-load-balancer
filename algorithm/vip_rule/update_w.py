import sys
import random
import math
from vip_rule import *
from single_vip import *
from suffix_forest import SuffixTree, SuffixForest
from operator import itemgetter, attrgetter


def sum_up_tokens(tokens):
  def token_to_float((sign, exp)):
    return sign * 1.0 / (1 << exp)
  def sum_up_floats(x1, x2):
    return x1 + x2

  return reduce(sum_up_floats, map(token_to_float, tokens), 0)


def churn_from_abc(c, x_pos, x_neg, y_pos, y_neg):
  a = c + x_pos - x_neg
  b = c + y_pos - y_neg
  best_churn = abs(a - b)
  a_cap_c = max(0.0, (a + c - x_pos - x_neg) / 2.0)
  a_cup_c = a + c - a_cap_c

  extra_a = a_cap_c - y_neg
  term_y_neg = max(extra_a, 0)
  y_choice = (1.0 - a_cup_c) + max(-extra_a, 0)
  term_y_pos = max(y_pos - y_choice, 0)
  a_cap_b = term_y_neg + term_y_pos
  worst_churn = a + b - a_cap_b * 2

#  print "A = {}, B = {}, C = {}".format(a, b, c)
#  print "A n C = {}, A U C = {}, A n B = {}".format(a_cap_c, a_cup_c, a_cap_b)

  return best_churn, worst_churn

## calculate best churn and worst churn from tokens
def churn_from_tokens(X, Y, Z):
  c = sum_up_tokens(Z)
  x_pos = sum_up_tokens(filter(lambda((s,e)): s > 0, X))
  x_neg = -sum_up_tokens(filter(lambda((s,e)): s < 0, X))
  y_pos = sum_up_tokens(filter(lambda((s,e)): s > 0, Y))
  y_neg = -sum_up_tokens(filter(lambda((s,e)): s < 0, Y))

  return churn_from_abc(c, x_pos, x_neg, y_pos, y_neg)


PICK_L_ONLY = 1
PICK_R_ONLY = 2
## Given an old token list, return a list of possible new token lists that
## approximate new_w
def get_new_tokens(tokens, new_w, tolerable_error, arg):
  res = []
  olds, news = [], []

  while (len(tokens) >= 0):
    c = sum_up_tokens(tokens)
    print new_w, c
    ((l2, L2), (u2, U2)) = approximate(new_w - c, tolerable_error)

    if (arg & PICK_L_ONLY > 0):
      b, news = l2, L2
      best_churn, worst_churn = churn_from_tokens(olds, news, tokens)
      res.append((tokens + news, worst_churn - best_churn, 'L'))
    if (arg & PICK_L_ONLY > 0):
      b, news = u2, U2
      best_churn, worst_churn = churn_from_tokens(olds, news, tokens)
      res.append((tokens + news, worst_churn - best_churn, 'U'))

    if (len(tokens) > 0):
      olds.append(tokens.pop())
    else:
      break
  return res


## produce a list of tokens given a series of update
def resolve_updates(ws, tolerable_error, tolerable_churn, max_rules):
  arg = PICK_L_ONLY
  res = []
  ((l1, L1), (u1, U1)) = approximate(ws[0], tolerable_error)
  res.append((ws[0], L1[:], 0))
  tokens = L1

  for w in ws[1:]:
    cand_tokens = get_new_tokens(tokens, w, tolerable_error, arg)
    next_tokens, min_churn = None, tolerable_churn
#    print w
#    print "\n".join("{}".format(k) for k  in cand_tokens)


    while (next_tokens == None):
      for (new_t, churn_diff, _) in cand_tokens:
        if (len(new_t) <= max_rules):
          if (next_tokens == None or double_cmp(churn_diff - best_churn) < 0):
#        if (double_cmp(churn_diff - min_churn) <= 0):
#          if (next_tokens == None or len(new_t) < len(next_tokens)):
            next_tokens, best_churn = new_t, churn_diff
      min_churn = min_churn * 2

    ## sort token in increasing order
 #   next_tokens.sort(key = itemgetter(1))
    tokens = next_tokens
    res.append((w, next_tokens[:], best_churn))

  return res
 # print res
#  print "weight, lenn, best_churn, token"
#  for (w, t, c) in [res[0]] + [res[-1]]:
#    print "{}, {}, {}, {}".format(w, len(t), c, t)
  



## Compute a single update: old_w -> new_w
def update_w(old_w, new_w, tolerable_error):
  ((l1, L1), (u1, U1)) = approximate(old_w, tolerable_error)
  print l1, L1
  return []

  if (NEED_HEADER):
    print "new_w, new_w - old_w,",

    print ",".join("L{}".format(i) for i in reversed(range(len(L1) + 1))),
    print",",
    print ",".join("churn_diff{}".format(i) for i in reversed(range(len(L1) + 1))),
    print ", best_i, best_l"

  print "{0:.3f}, {1:.3f},".format(new_w, new_w - old_w),

  a = l1
  cand = [L1[:]] 
  churns, lens = [], []
  eps = 0.01
  for tokens in cand:
    res = get_new_tokens(tokens, new_w, PICK_L_ONLY)
    for (new_t, churn_diff, flag) in res:
      this_c, this_l = churn_diff, len(new_t)
      lens.append(this_l)
      churns.append(this_c)
      
      if (double_cmp(this_c - eps) <= 0 or best_i < 0):
        best_i = len(tokens)
        best_l = this_l

      if (len(tokens) > 0):
        olds.append(tokens.pop())
      else:
        break

  print ",".join("{}".format(k) for k in lens),
  print ",",
  print ",".join("{}".format(k) for k in churns),
  print ",{}, {}".format(best_i, best_l)
  



old_w = float(sys.argv[1])
new_w = float(sys.argv[2])
tolerable_error = float(sys.argv[3])
num = int(sys.argv[4])

M = 10
rs = []
min_r, max_r, avg_r = 100, 0, 0.0
for j in range(M):
  ws = [old_w]
  for i in range(num):
    k = random.randint(1, 1000) / 1000.0
    ws.append(k)
  ws.append(new_w)

  print ws

  for tolerable_churn in [0.05]:
  #  print tolerable_churn
    res = resolve_updates(ws, tolerable_error, tolerable_churn, 10)
#    rn = res[-1]
#    r = len(rn[1])
    r = max(map(lambda(x): x[2], res))
    min_r = min(min_r, r)
    max_r = max(max_r, r)
    avg_r = avg_r + r
    rs.append(r)

rs.sort()
avg_r = avg_r / M

print "min = {}, max = {}, avg = {}".format(min_r, max_r, avg_r)
#for i in range(min_r, max_r + 1):
#  print "{} : {}".format(i, rs.count(i))



#NEED_HEADER = True
#update_w(old_w, new_w, error)

#print churn_from_abc(0.2, 0.2, 0.1, 0.4, 0.2)
#print churn_from_tokens([(1,3),(-1,5)],[(1,4),(-1,4)],[(1,2)])

#print churn_from_abc(0.25, 0.05, 0, 0, 0)

#if True:
if False:
  NEED_HEADER = True
  for i in range(1, int(1/error)):
    new_w = error * i
    update_w(old_w, new_w, error)
    NEED_HEADER = False
  
