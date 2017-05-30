import sys
import random
import math
from vip_rule import *
from single_vip import *
from multiple_vip import *
from suffix_forest import *
from operator import itemgetter, attrgetter


def zip_minus(xs, ys):
  zs = zip(xs, ys)
  def minus((x,y)): return x - y
  return map(minus, zs)


def distribute_leaf_rules(leaf_rules, root_rules):
  mk = dict()
  for i in range(len(leaf_rules)):
    (suffix, to_idx) = leaf_rules[i]
    found = False

    ## try find in aggregated leaf rule list
    for j in reversed(range(i)):
      (s_, idx_) = leaf_rules[j]
      res = overlap(suffix, s_)
      if res == CONTAINED:
        found = True
        mk[i] = mk[j]
        break
      elif res == NONE:
        continue
      else:
        raise NameError("Wrong rule layout with {} and {}".format(leaf_rules[i], leaft_rules[j]))
    ## try find in root rule list
    if (not found):
      for j in reversed(range(len(root_rules))):
        (s_, idx_) = root_rules[j]
        res = overlap(suffix, s_)
        if res == CONTAINED:
          found = True
          mk[i] = idx_
          break
        elif res == NONE:
          continue
        else:
          raise NameError("Wrong rules with {}, {}".format(leaf_rules[i], leaft_rules[j]))

    if (not found):
      raise NameError("No match for {}".format(leaf_rules[i]))

  return mk



# this function gives a solution to a two-level tree
# topology with N leaves (i.e, the root has M children). 
# The inputs are: the weights of leaves for all vips, 
# the rule capacity C ofthe root and the tolerable error.
# The rule layout optimizes the total imbalance at the 
# root-to-leaf switch, and achieves the tolerable
# error at the leaves.
def solve_two_layer_tree(vips, curve_dict, c, tolerable_error, ecmp_km_info, algo_mode):
  ## compute the multi-vip solution
  mvips_solver = MVipsSolver()
  mvips_sol = mvips_solver.solve_instance(vips, curve_dict, c, ecmp_km_info)

  ## initialize the leaf rules counter
  n_clusters = len(vips[0][2])
  leaf_num_rules = []
  leaf_num_rules.extend([0] * n_clusters)

  ## many analysis variables
  total_imb = 0.0
  M = 0
  if (ecmp_km_info != None):
    _, _, M = ecmp_km_info

  total_num_rules = M
  root_vips_rules = []
  leaf_vips_rules = dict()
  for i in range(n_clusters):
    leaf_vips_rules[i] = []

  ## compute rule list for every vip
  svip_solver = SVipSolver()
  for (vip_idx, volume, weights) in vips:
    def exd(r): return (r[0], r[1], vip_idx)

    ## retrive information
    curve = curve_dict[vip_idx]
    p_i = mvips_sol[vip_idx]
    point = curve[p_i]
    (num_rules, imb, error_now, d) = point

    ## update analysis var
    total_imb = total_imb + imb * volume
    total_num_rules = total_num_rules + num_rules - M

#    print "vip {} choose point {}".format(vip_idx, p_i)
#    print curve[p_i]

    root_sol, leaf_sol = get_root_leaf_sol(point)

    ## Below is an alternative
    # root_sol, leaf_sol = __get_root_leaf_sol(weights, point, tolerable_error, algo_mode)

    ## first root rules
    root_rules = root_sol.get_rules()
    values = root_sol.get_values()
    (v_imb, v_error, v_pool_e) = compute_vip_imbalance(values, tolerable_error)

    ## append root rules
    if (len(root_vips_rules) == 0):
      root_vips_rules.extend(map(exd, root_rules[:]))
    else:
      root_vips_rules.extend(map(exd, root_rules[M:]))
    
    ## now is leaf
    leaf_rules = leaf_sol.get_rules()

    ## check correctness
#    check_correctness(weights, root_rules + leaf_rules, tolerable_error)

    ## identify where (which leaf sw) each leaf rule should go
    mk = distribute_leaf_rules(leaf_rules, root_rules)
    for i in mk:
      ## count leaf rules,and append
      leaf_num_rules[mk[i]] = leaf_num_rules[mk[i]] + 1
      leaf_vips_rules[mk[i]].append(exd(leaf_rules[i]))


    ## boosting the packing of multiple C (increasing order)
    curve.truncate(p_i)

  return (c, (total_imb, root_vips_rules), leaf_vips_rules, ecmp_km_info)



def solve_two_layer_trees(vips, C, eps, ecmp_km_info, algo_mode):
  curve_dict = VipCurveDict(vips, eps, ecmp_km_info, algo_mode)
  multiple_layers_info = []

  ## enumerate over c
  for c in C:
#    print "work on", c
    layer_res = solve_two_layer_tree(vips, curve_dict, c, eps, ecmp_km_info, algo_mode)
    multiple_layers_info.append(layer_res)

  return multiple_layers_info


# find the best rule for multiple vips
# minimize the total imbalance at root
# try different default rules (no ecmp v.s x-ecmp) + c
def find_best_two_layer_tree(vips, eps, C, algo_mode):
  multiple_layers_info = []

  if False:
    layer_res = solve_two_layer_tree(vips, c, eps, None, algo_mode)
    multiple_layers_info = multiple_layers_info + layer_res
 

  N = len(vips[0][2])
  K_Range = int(math.log(N, 2.0))

  for t in range(K_Range, K_Range + 1):
    K = t
    M = (1 << K)
    ecmp_km_info = (NON_ECMP_Range, K, M)

    layer_res = solve_two_layer_trees(vips, C, eps, ecmp_km_info)
    multiple_layers_info = multiple_layers_info + layer_res

  return multiple_layers_info
