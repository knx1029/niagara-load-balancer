import sys
import random
import math
import copy
from suffix_forest import *
from operator import itemgetter, attrgetter

INFINITY = (1<<32)
EPS = 1e-9
BITS = 32
NON_ECMP_Range = 3
NAIVE = False

# whether imbalance counts sum|w^H - w'|
# otherwise, counts sum|w^H - w|
OPT_W_PRIME = False

# flags to denote the strategy for selecting L & U
BF = 1
HEU = 2
FIXED = 4

# compare float
def double_cmp(x):
  if (x > EPS):
    return 1
  if (x < -EPS):
    return -1
  return 0  


# add one more rule to an existing approximation

USE_L_ONLY = 4
USE_R_ONLY = 8
USE_ALL = USE_L_ONLY | USE_R_ONLY
APPROX_L_ONLY = 1
APPROX_R_ONLY = 2
APPROX_ALL = APPROX_L_ONLY | APPROX_R_ONLY
ARG_ALL = USE_ALL | APPROX_ALL
def approximate_w_more(w, lower_bound, L, upper_bound, U, arg = ARG_ALL):

  # return exp such that 2^(-exp) <= target < 2^-(exp-1)
  def find_exponent(base, target):
    if double_cmp(target) == 0:
      return (0, 0, 0, 0)
    a = 0
    two_exp_a = 1.0
    while double_cmp(two_exp_a - target) > 0:
      a = a + 1
      two_exp_a /= base

    if (double_cmp(two_exp_a - target) == 0):
      return (a, two_exp_a, a, two_exp_a)
    else:
      return (a, two_exp_a, a - 1, two_exp_a * 2)


  # function logic starts here
  (a, two_exp_a, a2, two_exp_a2) = find_exponent(2, w - lower_bound)
  (b, two_exp_b, b2, two_exp_b2) = find_exponent(2, upper_bound - w)

  lower_bound_new, L_new, upper_bound_new, U_new = lower_bound, [], upper_bound, []

  # generate new lower_bound
  if ((arg & APPROX_L_ONLY) > 0):
    cmp_res = double_cmp((lower_bound + two_exp_a) - (upper_bound - two_exp_b2))
#    l_wins = (cmp_res > 0 or (cmp_res == 0 and len(L) <= len(U)))
    l_wins = cmp_res >= 0
    if (arg & USE_R_ONLY == 0) or ((arg & USE_L_ONLY > 0) and l_wins):
      # L' = L :: (+, a)
      L_new = L[:]
      if (two_exp_a >= 0):
        L_new.append((1, a))
        lower_bound_new = lower_bound + two_exp_a
    else:
      # L' = U :: (-, b - 1)
      L_new = U[:]
      if (two_exp_b >= 0):
        L_new.append((-1, b2))
        lower_bound_new = upper_bound - two_exp_b2


  # generate new upper_bound
  if ((arg & APPROX_R_ONLY) > 0):
    cmp_res = double_cmp((lower_bound + two_exp_a2) - (upper_bound - two_exp_b))
#    l_wins = (cmp_res < 0 or (cmp_res == 0 and len(L) <= len(U)))
    l_wins = cmp_res < 0
    if (arg & USE_R_ONLY == 0) or ((arg & USE_L_ONLY > 0) and l_wins):
      # U' = L :: (+, a - 1)
      U_new = L[:]
      if (two_exp_a >= 0):
        U_new.append((1, a2))
        upper_bound_new = lower_bound + two_exp_a2
    else:
      # U' = U :: (-, b)
      U_new = U[:]
      if (two_exp_b >= 0):
        U_new.append((-1, b))
        upper_bound_new = upper_bound - two_exp_b

  return (lower_bound_new, L_new, upper_bound_new, U_new)


# generate a list of valid approximations to weight w
def approximate(w, tolerable_error):
  old_w = w
  w = abs(w)

  if (double_cmp(w) == 0):
    return ((0.0, []), (0.0, []))

  # start approximation
  lower_bound, upper_bound = 0.0, 1.0
  L, U = [], [(1, 0)]
  error = max(w - lower_bound, upper_bound - w)
  results = []
  use_arg = USE_L_ONLY
  while (double_cmp(error - tolerable_error) > 0):

    approx_arg = 0
    if (double_cmp((w - lower_bound) - tolerable_error) > 0):
      approx_arg = approx_arg | APPROX_L_ONLY

    if (double_cmp((upper_bound - w) - tolerable_error) > 0):
      approx_arg = approx_arg | APPROX_R_ONLY

    res = approximate_w_more(w, lower_bound, L, upper_bound, U, approx_arg | use_arg)

    use_arg = 0
    if (approx_arg & APPROX_L_ONLY > 0):
      use_arg = use_arg | USE_L_ONLY
      lower_bound, L = res[0], res[1]

    if (approx_arg & APPROX_R_ONLY > 0):
      use_arg = use_arg | USE_R_ONLY
      upper_bound, U = res[2], res[3]

    if NAIVE:
      use_arg = USE_L_ONLY

    error = max(upper_bound - w, w - lower_bound)

  if (old_w < 0):
    def inverse_sign((sign, exp)): return (-sign, exp)
    return ((-upper_bound, map(inverse_sign, U)), (-lower_bound, map(inverse_sign, L)))
  else: 
    return ((lower_bound, L), (upper_bound, U))


# give the #rules needed from token_list
def get_num_rules_from_token(token_list):
  exp_old = -1
  num_rules = 0
  num_exp_rules_neg = 0
  num_exp_rules_pos = 0
  for (op, exp, idx) in token_list:
    if (exp != exp_old):
      num_rules = num_rules + max(num_exp_rules_pos, num_exp_rules_neg)
      num_exp_rules_pos, num_exp_rules_neg = 0, 0

    exp_old = exp
    if (op < 0):
      num_exp_rules_neg = num_exp_rules_neg + 1
    else:
      num_exp_rules_pos = num_exp_rules_pos + 1

  num_rules = num_rules + max(num_exp_rules_pos, num_exp_rules_neg)
  return num_rules


# expand value_lists to include idx and concatenate all
def get_token_list(value_list):
  def add(x, y): return x + y
  def expand((idx, w, v, vlist)): return map(lambda((x, y)): (x, y, idx), vlist)

  expanded_value_list = map(expand, value_list)
  return reduce(add, expanded_value_list, [])



# give the #rules needed from value_list
def get_num_rules_from_value(value_list):
  token_list = get_token_list(value_list)
  token_list.sort(key = itemgetter(1))
  return get_num_rules_from_token(token_list)


# compute the imbalance and error of a given value list
def compute_vip_imbalance(value_list, eps):
  if (OPT_W_PRIME):
    return imbalance_minus_eps(value_list, eps)
  else:
    return abs_vip_imbalance(value_list)

def abs_vip_imbalance(value_list):

  def diff(v): return v[1] - v[2]
  def max_abs(v1, v2): return max(abs(v1), abs(v2))
  def sum_abs(v1, v2): return abs(v1) + abs(v2)

  errors = map(diff, value_list)
  pool_error = -sum(errors)
  error = max(abs(pool_error), reduce(max_abs, errors, 0.0))

  pool_imb = abs(pool_error)
  imbalance = (reduce(sum_abs, errors, 0.0) + pool_imb) * 0.5

  return (imbalance, error, pool_error)


## compute the imbalance with consideration of eps
def imbalance_minus_eps(value_list, eps):

  def diff(v): return v[1] - v[2]
  def max_abs(v1, v2): return max(abs(v1), abs(v2))
  def minus_eps(v): return max(- v - eps, 0.0)

  errors = map(diff, value_list)
  pool_error = -sum(errors)
  error = max(abs(pool_error), reduce(max_abs, errors, 0.0))

  pool_imb = minus_eps(pool_error)
  imbs = map(minus_eps, errors)
  imbalance = (sum(imbs) + pool_imb)


  return (imbalance, error, pool_error)



# k's binary representation: 0 for L, 1 for U
def get_value_list_from_choice(approx_list, choice):
  tmp = choice
  value_list = []
  for (idx, w, L, U) in approx_list:
    if (tmp % 2 == 0):
      value_list.append((idx , w, L[0], L[1]))
    else:
      value_list.append((idx, w, U[0], U[1]))
    tmp = tmp / 2
  return value_list

# use the given choice toe solve P2: Given tolerable_error, minimize num rules
def fixed_pick_values(approx_list, choice):

  value_list = get_value_list_from_choice(approx_list, choice)
  num_rules = get_num_rules_from_value(value_list)
  return (num_rules, value_list)


# brute force solve P2: Given tolerable_error, minimize num rules
def bf_pick_values(approx_list, weight_map, pool_idx, tolerable_error):
  # brute force search
  min_num_rules = (1<<32)
  min_value_list = []
  min_error = 0.0

  # k's binary representation: 0 for L, 1 for U
  for k in range(0, (1<<len(approx_list))):
    value_list = get_value_list_from_choice(approx_list, k)
    (imbalance, error, _) = compute_vip_imbalance(value_list, tolerable_error)
    if (double_cmp(error - tolerable_error) <= 0):
#        num_rules = get_num_rules_from_value(value_list)
      num_rules = get_number_rules(value_list, weight_map, pool_idx)
      if (num_rules < 0):
        continue

      if (num_rules < min_num_rules or (num_rules == min_num_rules and error < min_error)):
        min_num_rules, min_error, min_value_list = num_rules, error, value_list

  return (min_num_rules, min_value_list)


# heuristics solve P2: Given tolerable_error, minimize num rules
def heu_pick_values(approx_list, tolerable_error):

  PICK_L_ONLY = 1
  PICK_U_ONLY = 2
  def pick_up_one_value(approx_list, value_list, arg):
    best_value = None
    best_approx = None
    min_num_rules = INFINITY
    
    for approx in approx_list:
      (idx, w, L, U) = approx
      if (arg & PICK_L_ONLY > 0):
        value_list.append((idx, w, L[0], L[1]))
        new_num_rules = get_num_rules_from_value(value_list)
        value_list.pop()
        # update min_num_rules
        if (new_num_rules < min_num_rules):
          min_num_rules = new_num_rules
          best_approx = approx
          best_value = (idx, w, L[0], L[1])

      if (arg & PICK_U_ONLY > 0):
        value_list.append((idx, w, U[0], U[1]))
        new_num_rules = get_num_rules_from_value(value_list)
        value_list.pop()
        # update min_num_rules
        if (new_num_rules < min_num_rules):
          min_num_rules = new_num_rules
          best_approx  = approx
          best_value = (idx, w, U[0], U[1])

    return best_value, best_approx


  # heuristics starts here
  min_num_rules = 0
  delta = 0.0
  value_list = []
  approx_list_ = approx_list[:]

  while (len(approx_list_) > 0):
    arg = 0    
    if (double_cmp(delta) <= 0):
      arg = arg | PICK_L_ONLY
    if (double_cmp(delta) >= 0):
      arg = arg | PICK_U_ONLY
    # choose value, update value_list, approx_list and delta
    best_value, best_approx = pick_up_one_value(approx_list_, value_list, arg)
    approx_list_.remove(best_approx)
    value_list.append(best_value)
    delta = delta + best_value[1] - best_value[2]

  return (get_num_rules_from_value(value_list), value_list)


# pick up values (L or U) from approx_list
# goals are two-fold: stay within tolerable_error and minimize #rules
# arg decides using BruteForce or Heuristics
def pick_values(approx_list, weight_map, pool_idx, tolerable_error, arg, choice):
  if (arg & BF) > 0:
    return bf_pick_values(approx_list, weight_map, pool_idx, tolerable_error)

  if (arg & HEU) > 0:
    return heu_pick_values(approx_list, tolerable_error)

  if (arg & FIXED) > 0:
    return fixed_pick_values(approx_list, choice)
  

# print rules and details
def print_out_values(rules, value_list):

#  print "------------------"

#  print('\n'.join('({},{}, {})'.format(*k) for k in value_list))
#  (imbalance, error, _) = compute_vip_imbalance(value_list, 0.0)
#  print "Max Error:", error, "Imbalance: ", imbalance, "Use: ", len(rules), "rules"
#  print('\n'.join('({},{})'.format(*k) for k in rules))
#  print rules
#  print "------------------"
  pass


class OpError(Exception):
  def __init__(self, status):
    self.msg = status
    print status


# produce the non default rules given the value list to weights
# initial suffix_forest_map is also given
def construct_rules(value_list, suffix_forest_map, pool_idx):

  # steal suffix of level exp from 'from_idx' to 'to_idx'
  def steal_suffix(from_forest, to_forest, from_idx, to_idx, exp):
    # print "steal from", from_idx, "to", to_idx, "of level", exp
    node = from_forest.find_node(exp)
    from_forest.remove_node(node)
    if (node):
      to_forest.add_tree(node)
      return (node.root, to_idx)
    else:
      return None

  # empty the bucket
  def empty_bucket(pos, neg, suffix_forest_map, pool_idx, exp, rules):
    # fill pool_idx to bucket s.t len(pos) = len(neg)
    if (len(pos) > len(neg)):
      for i in range(len(pos) - len(neg)):
        neg.append(pool_idx)
    elif (len(pos) < len(neg)):
      for i in range(len(neg) - len(pos)):
        pos.append(pool_idx)

    new_pos, new_neg = [], []
    while (len(pos) > 0 and len(neg) > 0):
      idx_p = pos.pop()
      idx_n = neg.pop()

      if (idx_p == idx_n):
        continue

      rule = steal_suffix(suffix_forest_map[idx_n],
                          suffix_forest_map[idx_p],
                          idx_n, idx_p, exp);
      if (rule == None):
        if (idx_p != pool_idx):
          new_pos.append(idx_p)
          new_pos.append(idx_p)
        if (idx_n != pool_idx):
          new_neg.append(idx_n)
          new_neg.append(idx_n)
      else:
        rules.append(rule)
    return new_pos, new_neg


  # main logic starts here
  # memrge tokens and sort in increasing value of exp field
  token_list = get_token_list(value_list)
  token_list.sort(key=itemgetter(1))


  # process tokens and generate rules (priority increases)
  rules = []
  token_pos_bucket = []
  token_neg_bucket = []
  exp_old = -1
  for (op, exp, idx) in token_list:
    while (exp != exp_old):
      token_pos_bucket, token_neg_bucket = empty_bucket(token_pos_bucket, 
                                                        token_neg_bucket, 
                                                        suffix_forest_map,
                                                        pool_idx, exp_old,
                                                        rules);
      exp_old = exp_old + 1
#      print exp_old, token_pos_bucket, "\n", token_neg_bucket

    if (op > 0):
      token_pos_bucket.append(idx)
    else:
      token_neg_bucket.append(idx)

  token_pos_bucket, token_neg_bucket = empty_bucket(token_pos_bucket, 
                                                    token_neg_bucket, 
                                                    suffix_forest_map,
                                                    pool_idx, exp_old,
                                                    rules);

#  print exp_old, token_pos_bucket, "\n", token_neg_bucket
#  print "===========\n"
  if (len(token_pos_bucket) > 0 or len(token_neg_bucket) > 0):
    print token_list
    print "pos_bucket: ",token_pos_bucket
    print "neg_bucket: ", token_neg_bucket
    print "OpError:", value_list
    raise OpError("tokens: pos = {}, neg = {}".format(len(token_pos_bucket),
                                                      len(token_neg_bucket)))

  return rules


def check_value_valid(value_list, weight_map, pool_idx):
  x, y = 0.0, 0.0
  for (idx, w, v, vlist) in value_list:
    x = weight_map[idx] + v
    if (double_cmp(x) < 0 or double_cmp(x - 1) > 0):
      return False
    y = y + v

  x = weight_map[pool_idx] - y
  if (double_cmp(x) < 0 or double_cmp(x - 1) > 0):
    return False

  return True


# produce #rules needed given the value list to weights and initial weight
def get_number_rules(value_list, weight_map_, pool_idx):
  weight_map = weight_map_.copy()
  if (not check_value_valid(value_list, weight_map, pool_idx)):
    return -1


  res =  __get_number_rules(value_list, weight_map, pool_idx)
  if (res < 0):
    raise OpError("res = {}, Wrong algorithm: values = {}, weights = {}, pool = {}".format(res, value_list, weight_map_, pool_idx))

  return res


# produce #rules needed given the value list to weights and initial weight
def __get_number_rules(value_list, weight_map, pool_idx):

  # steal suffix of level exp from 'from_idx' to 'to_idx'
  def steal_suffix(weight_map, from_idx, to_idx, unit):
    from_weight = weight_map[from_idx]
    to_weight = weight_map[to_idx]
#    print "steal from {} with {} to {} with {}, unit = {}".format(from_idx, from_weight, to_idx, to_weight, unit)
    if (double_cmp(from_weight - unit) < 0):
      return False
    weight_map[from_idx] = from_weight - unit
    weight_map[to_idx] = to_weight + unit
    return True

  # empty the bucket
  def empty_bucket(pos, neg, weight_map, pool_idx, exp):

    nrules = 0
    if (len(pos) > 0 or len(neg) > 0):
      unit = get_unit(exp)

    # fill pool_idx to bucket s.t len(pos) = len(neg)
    if (len(pos) > len(neg)):
      for i in range(len(pos) - len(neg)):
        neg.append(pool_idx)
    elif (len(pos) < len(neg)):
      for i in range(len(neg) - len(pos)):
        pos.append(pool_idx)

    new_pos, new_neg = [], []
    while (len(pos) > 0 and len(neg) > 0):
      idx_p = pos.pop()
      idx_n = neg.pop()

      if (idx_p == idx_n):
        continue
      found = steal_suffix(weight_map,
                          idx_n, idx_p, unit);
      if (found):
        nrules = nrules + 1
      else:
        if (idx_p != pool_idx):
          new_pos.append(idx_p)
          new_pos.append(idx_p)
        if (idx_n != pool_idx):
          new_neg.append(idx_n)
          new_neg.append(idx_n)

    return new_pos, new_neg, nrules


  # main logic starts here
  # memrge tokens and sort in increasing value of exp field
  token_list = get_token_list(value_list)
  token_list.sort(key=itemgetter(1))


  # process tokens and generate rules (priority increases)
  token_pos_bucket = []
  token_neg_bucket = []
  exp_old = -1
  num_rules, nrules = 0, 0
  for (op, exp, idx) in token_list:
    while (exp != exp_old):
      token_pos_bucket, token_neg_bucket, nrules = empty_bucket(token_pos_bucket, 
                                                        token_neg_bucket, 
                                                        weight_map,
                                                        pool_idx, exp_old);
      if (nrules < 0):
        return -1
      num_rules = nrules + num_rules
#      print token_pos_bucket, token_neg_bucket, exp_old + 1
      exp_old = exp_old + 1


    if (op > 0):
      token_pos_bucket.append(idx)
    else:
      token_neg_bucket.append(idx)


  token_pos_bucket, token_neg_bucket, nrules = empty_bucket(token_pos_bucket, 
                                                    token_neg_bucket, 
                                                    weight_map,
                                                    pool_idx, exp_old);


  if (nrules < 0 or len(token_pos_bucket) > 0 or len(token_neg_bucket) > 0):
    return -1

  num_rules = nrules + num_rules
  return num_rules


## reconstruct the suffix forest map and
## weight map from the given rule list
def reconstruct_sf_ws_from_rules(rules, n_clusters):

  weight_map = dict()
  sf_map = dict()

  for c in range(n_clusters):
   weight_map[c] = 0.0
   sf_map[c] = SuffixForest(c, [])

  for i in range(len(rules)):
#    print rules[i], " => ",

    (pattern, to_idx) = rules[i]
    unit = get_unit(get_level(pattern))

    parent_r = None
    for j in reversed(range(i)):
      (p,idx) = rules[j]
      if overlap(pattern, p) == CONTAINED:
        parent_r = rules[j]
        break

 #   print parent_r

    if (parent_r != None):
      p, idx = parent_r
      sf_map[idx].remove_matching_nodes(pattern)
      weight_map[idx] = weight_map[idx] - unit

#    if not (to_idx in sf_map):
#      sf_map[to_idx] = SuffixForest([])
#      weight_map[to_idx] = 0.0
 
    sf_map[to_idx].add_tree(SuffixTree(pattern))
    weight_map[to_idx] = weight_map[to_idx] + unit    

  return sf_map, weight_map
