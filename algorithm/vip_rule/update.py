import sys
import random
import math
import copy
from collections import deque
from vip_rule import *
from suffix_forest import SuffixTree, SuffixForest
from operator import itemgetter, attrgetter
from single_vip import *


def cmp_rule(r1, r2):
  return get_level(r1[0]) - get_level(r2[0])

def compute_real_churn(old_rules, new_rules):

  ## compute f and g
  def compute_f_g(rules, f, g, i):
    l = len(rules)
    (pattern, to_idx) = rules[i]
    g[pattern] = get_unit(get_level(pattern))

    gsum = 0
    fmap = [0] * n_weights
    child_r = None
    for j in range(0, i):
      (pj,idxj) = rules[j]
      if overlap(pj, pattern) != CONTAINED:
        continue

      is_child = True
      for k in range(j + 1, i):
          (pk, idxk) = rules[k]
          if overlap(pj, pk) == CONTAINED:
            is_child = False
            break

      if (is_child):
        fmapj = f[pj]
        for c in range(n_weights):
          fmap[c] = fmap[c] + fmapj[c]
        gsum = gsum + g[pj]

    fmap[to_idx] = fmap[to_idx] + g[pattern] - gsum
    f[pattern] = fmap

  ## compute the churn
  def compute_churn(rules, t_i, f, i):
    churn = 0.0
    pattern, _ = rules[i]
    fmap = f[pattern]
    for c in range(n_weights):
      if (c != t_i):
        churn = churn + fmap[c]
      fmap[c] = 0.0

    return churn

  ## find the least priority rule that 
  ## contain the pattern
  def find_contained_rule(rules, pattern):
    res = None
    for (p, t) in rules:
      if (overlap(pattern, p) == CONTAINED):
        res = (p, t)
    return res

  

  n_weights = max(max(map(lambda(x):x[1], old_rules)),
                  max(map(lambda(x):x[1], new_rules))) + 1

  old_l = len(old_rules)
  new_l = len(new_rules)

  f = dict()
  g = dict()

  rules = []
  j = new_l - 1
  churn = 0
  for i in reversed(range(old_l)):
    level_old = get_level(old_rules[i][0])

    while (j >= 0):
      level_new = get_level(new_rules[j][0])

      if (level_new >= level_old):
        (pattern, new_idx) = new_rules[j]
        (old_p, old_idx) = find_contained_rule(old_rules, pattern)
        rules.append((pattern, old_idx))
        compute_f_g(rules, f, g, len(rules) - 1)
        j = j - 1
#        print f[pattern],
        churn = churn + compute_churn(rules, new_idx, f, len(rules) - 1)
 #       print ">>>", pattern, old_p, old_idx, churn
      else:
        break

    rules.append(old_rules[i])
    compute_f_g(rules, f, g, len(rules) - 1)


  while (j >= 0):
    (pattern, new_idx) = new_rules[j]
    (old_p, old_idx) = find_contained_rule(old_rules, pattern)
    rules.append((pattern, old_idx))
    compute_f_g(rules, f, g, len(rules) - 1)
    j = j - 1
 #   print f[pattern],
    churn = churn + compute_churn(rules, new_idx, f, len(rules) - 1)
 #   print " >>>", pattern, old_p, old_idx, churn


  return churn

# sort the rules based on their pattern length (#non-* bits) and closeness to new_ws
def opt_order_rules(rules, M, ws):

  # compute imbalance
  def closeness(vs, ws):
    imb = 0.0
    for (idx, w) in ws:
#      print "({},{},{}), ".format(idx, w, vs[idx]),
      imb += abs(vs[idx] - w)
#    print ""
    return imb

  # update vs
  def get_vs(vs, rule, res_rules):
    (pattern, to_idx) = rule
    unit = get_unit(get_level(pattern))
    imb = 0.0
    vs[to_idx] = vs[to_idx] + unit
    for j in reversed(range(len(res_rules))):
      (p,idx) = res_rules[j]
      if overlap(pattern, p) == CONTAINED:
        vs[idx] = vs[idx] - unit
        break

  ## main logic starts here
  res_rules = rules[:M]
  cand_rules = rules[M:]

  ## construct the initial value of
  vs = dict()
  for (idx, w) in ws:
    vs[idx] = 0.0
  for rule in res_rules:
    get_vs(vs, rule, res_rules)


  while (len(cand_rules) > 0):
    next_i = -1
    next_rule = None
    next_vs = None
    next_imb = -1
    for i in range(len(cand_rules)):
      rule = cand_rules[i]
      vs_ = vs.copy()
      get_vs(vs_, cand_rules[i], res_rules)
      imb = closeness(vs_, ws)
      if (next_i < 0 or get_level(rule[0]) < get_level(next_rule[0]) or 
          get_level(rule[0]) == get_level(next_rule[0]) and imb < next_imb):
        next_i = i
        next_rule = rule
        next_imb = imb
        next_vs = vs_
    vs = next_vs
    res_rules.append(next_rule)
    cand_rules.pop(next_i)
#    print next_imb

#  print "RULES BEFORE ORDERING"
#  print "\n".join("{}".format(k) for k in rules)
#  print "RULES AFTER ORDERING"
#  print "\n".join("{}".format(k) for k in res_rules)

  return res_rules

      
## compute min churn
def compute_min_churn(old_ws, new_ws):
  ws = dict()
  for (idx, w) in old_ws:
    ws[idx] = w
  min_churn = 0
  for (idx, w) in new_ws:
    if (w > ws[idx]):
      min_churn = min_churn + w - ws[idx]
  return min_churn


## calculate different ways to update from old weights to new weights
def update_to_new_weights(old_ws, new_ws, old_error, new_error, ecmp_km_info, algo_mode):

  # retrieve ecmp info (the rules shared both weights by default)
  M = 0
  ecmp_info = None
  if (ecmp_km_info != None):
    ecmp_info_list = get_ecmp_info_list(ecmp_km_info)
    ecmp_info = ecmp_info_list[0]
    M = max(M, ecmp_info[3])

  # calculate the old rules
  svip_solver = SVipSolver()

  old_sol = svip_solver.solve_instance(old_ws, old_error,
                        ecmp_info, algo_mode)

  old_rules = old_sol.get_rules()
  old_pool_idx = old_sol.get_pool_idx()

  # reorder the rules (an optional optimization)
  old_rules = opt_order_rules(old_rules, M, new_ws)

#  print "======= old rules ======"
#  print "\n".join("{}, {}".format(*k) for k in old_rules)

  # enumerate possible ways to calaculate new weights
  new_rule_res = []
  n_clusters = len(old_ws)

  for i in reversed(range(M + 1, len(old_rules) + 1)):
   try:
    joint_rules = old_rules[:i]
    sf_map, weight_map = reconstruct_sf_ws_from_rules(joint_rules, n_clusters)

#    print "over"

    weights = []
    for (idx, w) in new_ws:
      weights.append((idx, w - weight_map[idx]))
    weights.sort(key = itemgetter(1), reverse = True)
    new_pool_idx = weights[0][0]

    new_sol = svip_solver.solve_special(weights, weight_map, new_pool_idx,
                        new_error, sf_map, algo_mode);

    new_rules = joint_rules + new_sol.get_rules()
    new_rules.sort(cmp=cmp_rule)
#    print "======= new rules ======"
#    print "\n".join("{}, {}".format(*k) for k in new_rules)

#    print "\n",
    churn = compute_real_churn(old_rules, new_rules)

#    print "\nold: {}, new : {}, churn : {}".format(
#                                len(joint_rules), 
#                                len(new_rules),
#                                churn);
    new_rule_res.append((joint_rules, new_rules, churn))  
   except OpError, e:
    print i


  ## add the way of  computing from scrath
  joint_rules = old_rules[:M]
  new_sol = svip_solver.solve_instance(new_ws, new_error,
                        ecmp_info, algo_mode)
  new_rules = new_sol.get_rules()
  min_churn = compute_min_churn(old_ws, new_ws)
  churn = compute_real_churn(old_rules, new_rules)
  new_rule_res.append((joint_rules, new_rules, churn))

  return  old_rules, min_churn, new_rule_res


## find the prefix for one step
def one_step(old_rules, new_rules, churn_per_step, K):
  ## project the rules to a pattern
  def project(rules, pattern):
    res = []
    for (p, i) in rules:
      q = join(p, pattern)
      if (q != None):
        res.append((q, i))
    return res

  ## expand a pattern
  def more_bits(str, K):
    idx = str.index('*')
    res = [str[:idx] + '0' + str[idx + 1:]]
    res.append(str[:idx] + '1' + str[idx + 1:])
    for idx in range(len(str) - K, len(str)):
      if (str[idx] == '*'):
        res.append(str[:idx] + '0' + str[idx + 1:])
        res.append(str[:idx] + '1' + str[idx + 1:])

    return res

  p_set = set()
  p_queue = deque()

  init = '*' * BITS
  p_queue.append(init)
  p_set.add(init)
  now = old_rules
  best_churn, best_p = -1.0, None
  while len(p_queue) > 0:
    p = p_queue.popleft()
    next = project(new_rules, p)
    churn = compute_real_churn(now, next)
    if (double_cmp(churn - churn_per_step) <= 0):
      if (churn > best_churn):
        best_churn, best_p = churn, p
    else:
      p_cand = more_bits(p, K)
      for pp in p_cand:
        if pp in p_set:
          continue
        else:
          p_queue.append(pp)

  return best_churn, best_p, project(new_rules, best_p)


## find the prefix for one step
def multi_step_update(old_rules, new_rules, churn_per_step, ecmp_km_info):

  def compress(rules):
    now = []
    l = len(rules)
    for (p, i) in reversed(rules):
      shadow = False
      for (pp, ii) in now:
        if overlap(p, pp) == CONTAINED:
          shadow = True
          break
      if (not shadow):
        now.append((p, i))
    res = []
    for item in reversed(now):
      res.append(item)
    return res

  K = 0
  if (ecmp_km_info == None):
    K = 0
  else:
    _, K, _ = ecmp_km_info

  num_steps = 0

  res = []
#  print "~!@~!@~!@~!@~1"
  total_churn = compute_real_churn(old_rules, new_rules)
  now = old_rules[:]
#  print total_churn
  while (True):
    churn, p, next = one_step(now, new_rules, churn_per_step, K)
    now.extend(next)
    now = compress(now)
    now.sort(cmp=cmp_rule)


    total_churn = total_churn - churn
    res.append((num_steps, now[:]))
    num_steps = num_steps + 1

    if (double_cmp(total_churn) == 0):
      break
    if (p == '*' * BITS):
      break

  if (double_cmp(total_churn) != 0):
    print "~!2`12`12`12"

  return num_steps, res


## truncate
def fit_T_imb_churn(new_ws, old_rules, new_rules, eps, T):
  ## initialize
  value_dict = {}
  for v in new_ws:
    (idx, w) = v
    item = (idx, w, 0.0)
    value_dict[idx] = item
  
  ## the very first point
  all_points = []

  ## construct the rules by truncating the rule list
  if (T > len(new_rules)):
    T = len(new_rules)
  for i in range(0, T):
    (s1, w1_idx) = new_rules[i]
    ## find where the token comes from
    w2_idx = -1
    for j in range(i - 1, -1, -1):
      (s2, w2_idx) = new_rules[j]
      if (overlap(s1, s2) == CONTAINED):
        break

    ## update w1_idx
    exp = get_level(s1)
    unit = get_unit(exp)
    (_, w1, v1) = value_dict[w1_idx]
    v1 = v1 + unit
    value_dict[w1_idx] = (w1_idx, w1, v1)
    ## update w2_idx
    if (w2_idx >= 0):
      (_, w2, v2) = value_dict[w2_idx]
      v2 = v2 - unit
      value_dict[w2_idx] = (w2_idx, w2, v2)


  vlist = []
  for (idx, w, v) in value_dict.values():
    vlist.append((idx, w, v))

  (imb, error, pool_e) = compute_vip_imbalance(vlist, eps)
  churn = compute_real_churn(old_rules, new_rules[:T])

  return (imb, churn)

