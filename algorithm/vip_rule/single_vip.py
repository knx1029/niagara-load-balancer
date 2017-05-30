import sys
import random
import math
import copy
from vip_rule import *
from suffix_forest import SuffixTree, SuffixForest
from operator import itemgetter, attrgetter


## construct a list of possible ecmp_info from the partial info ecmp_km_info
def get_ecmp_info_list(ecmp_km_info):

  (NON_ECMP_Range, K, M) = ecmp_km_info
  if (NON_ECMP_Range > 1):
    def f(exp): return (1.0 / (1 << exp), exp, K, M)
    ecmp_info_list = map(f, range(1, NON_ECMP_Range))
  else:
    ecmp_info_list = []
  ecmp_info_list.append((0, -1, K, M))

  return ecmp_info_list


## construct (weights, weight_map, pool_idx) from given ecmp information
## returns
## weights: the values to approximate
## weight_map: the initial weights_map of each cluster
## pool_idx: the chosen pool for the following apporximation process
def init_weights_from_ecmp(ws, ecmp_info):
  weight_map = dict()
  pool_idx = 0
  weights = []

  if (ecmp_info == None):
    weights = ws[:]
    weights.sort(key = itemgetter(1), reverse = True)
    pool_idx = weights[0][0]

    for (idx, _) in ws:
      weight_map[idx] = 0
    weight_map[pool_idx] = 1.0
    ## change the weight of pool (this weight is not approximated)
    weights[0] = (pool_idx, weights[0][1] - 1.0)
#    weights[0][1] = weights[0][1] - 1.0
  else:
    (non_ecmp, non_ecmp_exp, K, M) = ecmp_info
    w_avg = (1.0 - non_ecmp) / M
    for (idx, w) in ws:
      if (idx < M):
        weight_map[idx] = w_avg
        weights.append((idx, w - w_avg))
      else:
        weight_map[idx] = 0
        weights.append((idx, w))

    weights.sort(key = itemgetter(1), reverse = True)
    pool_idx = weights[0][0]
    weight_map[pool_idx] = weight_map[pool_idx] + non_ecmp
    ## change the weight of pool (this weight is not approximated)
    weights[0] = (pool_idx, weights[0][1] - non_ecmp)
#    weights[0][1] = weights[0][1] - non_ecmp

  return weights, weight_map, pool_idx


## construct the suffix forest map and default rules from given ecmp information
def init_rules_from_ecmp(n_clusters, pool_idx, ecmp_info):

  def translate_suffix(n, n_len, total_len):
    if (n_len == 0):
      return '*' * total_len
    binary_n = bin(n)
    return '*' * (total_len - n_len) + '0' * (n_len - len(binary_n) + 2) + binary_n[2:]


  ## initialize pool and add default rules
  suffix_forest_map = dict()
  rules = []

  ## if no ecmp rules
  if (ecmp_info == None):
    ## pool takes full traffic
    pool = SuffixTree("*" * BITS)
    rules.append(("*" * BITS, pool_idx))
    ## non pool has no traffic
    for idx in range(n_clusters):
      suffix_forest_map[idx] = SuffixForest(idx, [])
    suffix_forest_map[pool_idx].add_tree(pool)
  ## if ecmp rules exist
  else:
    (non_ecmp, non_ecmp_exp, K, M) = ecmp_info
    ## decide whether initial pool pattern exists
    pool = None
    if (non_ecmp_exp >= 0):
      non_ecmp_pattern = translate_suffix(0, non_ecmp_exp, BITS)[::-1]
      pool = SuffixTree(non_ecmp_pattern)

    ## initialize suffix forest map
    for idx in range(n_clusters):
      if (idx < M):
        suffix_string = translate_suffix(idx, K, BITS)
        tree = SuffixTree(suffix_string)
        if (pool != None):
          tree.remove_matching_nodes(non_ecmp_pattern)
        suffix_forest_map[idx] = SuffixForest(idx, [tree])
        rules.append((suffix_string, idx))
      else: 
        suffix_forest_map[idx] = SuffixForest(idx, [])

    if (pool != None):
      suffix_forest_map[pool_idx].add_tree(pool)
      rules.append((non_ecmp_pattern, pool_idx))

  return rules, suffix_forest_map



## represent a single vip solution
class SVipSolution:

  def __init__(self, value_list):
    self.value_list = value_list
    self.pool_idx = -1
    self.init_sf_map = None
    self.final_sf_map = None
    self.rules = None
    pass

  ## This function is only used to store information
  def set(self, value_list, pool_idx, rules):
    self.value_list = value_list
    self.pool_idx = pool_idx
    self.rules = rules
    self.init_sf_map = None
    self.final_sf_map = None
    

  def get_values(self):
    return self.value_list


  def get_rules(self):
    return self.rules

  def get_pool_idx(self):
    return self.pool_idx

  ## given initial suffix forest map
  ## and call construct_rules to generate rules
  def init_rules_with_sfmap(self, pool_idx, sf_map):
    if (self.rules != None):
      return
    self.init_sf_map = copy.deepcopy(sf_map)
    sf_map_copy = copy.deepcopy(sf_map)
    rules = construct_rules(self.value_list, sf_map_copy, pool_idx)
    self.final_sf_map = sf_map_copy
    self.pool_idx = pool_idx
    self.rules = rules

  ## create the suffix forest and default rules (ecmp or non-ecmp)
  ## and call construct_rules to generate non default rules
  def init_rules_with_ecmp_info(self, pool_idx, ecmp_info):
    if (self.rules != None):
      return

    n_clusters = len(self.value_list) + 1
    default_rules, sf_map = init_rules_from_ecmp(n_clusters, pool_idx, ecmp_info)

    self.init_rules_with_sfmap(pool_idx, sf_map)
    if (self.rules != None):
      self.rules = default_rules + self.rules


class SVipSolver:

  def __init__(self):
    pass


  def __compute_value_list(self, weights, weight_map, pool_idx, tolerable_error, arg, choice):
    ## compute approx list
    approx_list = []
    for (idx, w) in weights:
      if (idx == pool_idx):
        continue
      (L, U) = approximate(w, tolerable_error)
      approx_list.append((idx, w, L, U))
#      print tolerable_error
#      print "L and U for w:", w, (idx, w - L[0], L[1],U[0] - w, U[1])

    ## pick values
    (num_rules, value_list) = pick_values(approx_list, weight_map, pool_idx, tolerable_error, arg, choice)
    return value_list

  ## solve the approximation for a single vip
  ## given weights and tolerable_error
  ## generate rules and values to approximate weights
  ## while staying within the tolerable_error
  def solve_instance(self, ws, tolerable_error, ecmp_info, arg, choice = -1):
    ## update weights
    weights, weight_map, pool_idx = init_weights_from_ecmp(ws, ecmp_info)

    ## generate value_list
    value_list = self.__compute_value_list(weights, weight_map, pool_idx, tolerable_error, arg, choice)

    ## generate rules
    solution = SVipSolution(value_list)
    solution.init_rules_with_ecmp_info(pool_idx, ecmp_info)
#    rules = solution.get_rules()

    return solution



  ## solve based on existing sf_map
  ## weights are already changed to the difference
  ## weight_map and sf_map are sync-ed
  def solve_special(self, weights, weight_map, pool_idx, tolerable_error, sf_map, arg, choice = -1):
    ## generate value_list
    value_list = self.__compute_value_list(weights, weight_map, pool_idx, tolerable_error, arg, choice)

    ## generate rules
    solution = SVipSolution(value_list)
    solution.init_rules_with_sfmap(pool_idx, sf_map)
#    rules = solution.get_rules()

    return solution



#  values = map(lambda (idx, w, v, vlist):(idx, w, v), value_list)
#  print "solve_Single_vip", values, "\n details = ", compute_vip_imbalance(values), "\n where ecmp_info =", ecmp_info
#  return (rules, values)
def find_single_vip_w_default(ws, tolerable_error, arg, ecmp_km_info):

  best_len, best_sol, rules, values = 0, [], [], []
  solver = SVipSolver()

  if (ecmp_km_info == None):
    sol = solver.solve_instance(ws, tolerable_error, None, arg)
    rules, values = sol.get_rules(), sol.get_values()

    best_len = len(rules)
    best_sol = best_sol + [None]
  else:
    ecmp_info_list = get_ecmp_info_list(ecmp_km_info)

    best_len = INFINITY
    for ecmp_info in ecmp_info_list:
      (non_ecmp, non_ecmp_exp, K, M) = ecmp_info
      sol = solver.solve_instance(ws, tolerable_error, ecmp_info, arg)
      rules, values = sol.get_rules(), sol.get_values()
      if (len(rules) < best_len):
        best_len = len(rules)
        best_sol = [ecmp_info[:]]
      elif (len(rules) == best_len):
        best_sol.append(ecmp_info[:])

  best_values = map(lambda (idx, w, v, vlist): (idx, w, v), values)
  return best_len, best_sol, rules, values
    

# try all possible strategies for a single vip
# including: no ecmp default rules, x-bit ecmp default rules (with y-mask)
def find_best_single_vip(weights, tolerable_error, arg):

  single_vip_info = []

#  (rules, values) = solve_single_vip(weights, tolerable_error, arg, None)
  (l, s, r, v) = find_best_single_vip_w_default(weights, tolerable_error, arg, None)
  best_len, best_sol, rules, values = l, s, r, v
  single_vip_info.append((l, s, r, v, None))

  N = len(weights)
  K_Range = int(math.log(N, 2.0))

  for K in range(0, K_Range + 1):
    M = 1 << K
    ecmp_km_info = (NON_ECMP_Range, K, M)
    (l, s, r, v) = find_single_vip_w_default(weights, tolerable_error, arg, ecmp_km_info)
    single_vip_info.append((l, s, r, v, ecmp_km_info))

    if (l - M < best_len):
      best_len, best_sol, rules, values = l - M, s, r, v

  return (best_len, best_sol, rules, values), single_vip_info
  

