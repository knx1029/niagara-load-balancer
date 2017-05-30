import sys
import random
import math
from vip_rule import *
from single_vip import *
from multiple_vip import *
from suffix_forest import *
from operator import itemgetter, attrgetter

K_MEANS = 1
K_MEDIAN = 2
class GroupSolver:

  def __init__(self, init_vips):
    self.init_vips = init_vips

  def group_vips(self, k, arg = K_MEANS):

    ## compute dist between two vectors
    def compute_dist(w1, g2, arg):
      res = 0
      z = zip(w1, g2)
      if (arg == K_MEANS):
        x = map(lambda(x):(x[0][1] - x[1])*(x[0][1] - x[1]), z)
      elif (arg == K_MEDIAN):
        x = map(lambda(x):abs(x[0][1] - x[1]), z)
      else:
          raise OpError("Wrong arg {} in compute dist".format(arg))
      res = sum(x)
      return res

    ## compute the updated weights
    def new_weight(vips, group, now_vips):
      old_vips = now_vips[:]
      for i in range(len(now_vips)):
        for j in range(len(now_vips[i])):
          now_vips[i][j] = 0.0
      
      sums = [0.0] * len(now_vips)
      for (idx, t, weights) in vips:
        kth = group[idx]
        sums[kth] = sums[kth] + t
        for j in range(len(weights)):
          now_vips[kth][j]= now_vips[kth][j] + t * weights[j][1]

      for i in range(len(now_vips)):
        if (double_cmp(sums[i]) == 0):
          for j in range(len(now_vips[i])):
            now_vips[i][j] = old_vips[i][j]
        else:
          for j in range(len(now_vips[i])):
            now_vips[i][j] = now_vips[i][j] / sums[i]

      return sums          

    ## main logic starts

    self.init_vips.sort(key = itemgetter(1), reverse = True)

    now_vips = []
    group = []

    i = 0
    while len(now_vips) < k and i < len(self.init_vips):
      ws = map(lambda(x): x[1], self.init_vips[i][2])
      exists = False
      for now_vip in now_vips:
        d = compute_dist(self.init_vips[i][2], now_vip, arg)
        if (double_cmp(d) == 0):
          exists = True
          break
      if (not exists):
        now_vips.append(ws)
      i = i + 1

    if len(now_vips) < k:
      k = len(now_vips)
      print "only {} distinct vips".format(k)

    for (idx, _, _) in self.init_vips:
      group.append(-1)

    converge = False
    converge_timer = 0
    agg_dist = 0.0
    while (not converge) and (converge_timer <= 1):
      converge = True
      ## allocate
      agg_dist = 0.0
      for (idx, t, weights) in self.init_vips:
        best_i, best_dist = -1, 0
        for i in range(k):
          dist = compute_dist(weights, now_vips[i], arg)
          if (best_i < 0 or best_dist > dist):
            best_i, best_dist = i, dist
        agg_dist = agg_dist + best_dist * t
        if (group[idx] != best_i):
          converge = False
          group[idx] = best_i

      ## update now_vips
      new_weight(self.init_vips, group, now_vips)

 #     print now_vips
      converge_timer = converge_timer + 1
      print converge_timer, agg_dist

    print converge_timer


    sums = new_weight(self.init_vips, group, now_vips)
    res = []
    n_group = 0
    for i in range(k):
      g_ws = now_vips[i]
      weights = zip(range(0, len(g_ws)), g_ws)
      res.append((i, sums[i], weights))
      if (double_cmp(sums[i]) != 0):
        n_group = n_group + 1
    print "distinct groups", n_group

    return res, group


def show(vips, c):
  print "m {} {} {}".format(len(vips[0][2]), len(vips), c)
  for (idx, t, weights) in vips:
    for (_, w) in weights:
      print w,
    print ""

  print "1"
  for (idx, t, weights) in vips:
    print t,
  print ""


def group_and_ungroup(old_vips, vips, group, curve_dict, c, eps, ecmp_km_info, algo_mode):

  ## compute the multi-vip solution
  mvips_solver = MVipsSolver()
  mvips_sol = mvips_solver.solve_instance(vips, curve_dict, c, ecmp_km_info)

  total_imb = 0.0
  M = 0
  if (ecmp_km_info != None):
    _, _, M = ecmp_km_info
  total_num_rules = M

  ## ungroup vips
  svip_solver = SVipSolver()
  for (idx, volume, weights) in vips:

    ## retrive information
    curve = curve_dict[idx]
    p_i = mvips_sol[idx]
    point = curve[p_i]
    (num_rules, imb, error_now, d) = point


    t_value_list = d[VALUE_DICTKEY]
    t_pool_idx = d[POOL_DICTKEY]
    try:
      ecmp_info = d[ECMP_DICTKEY]
    except KeyError:
      ecmp_info = None

    ## get root rule list
    #root_sol = SVipSolution(t_value_list)
    #root_sol.init_rules_with_ecmp_info(t_pool_idx, ecmp_info)

    root_sol, _ = get_root_leaf_sol(point)
    ## Below is an alternative
    # root_sol, _ = __get_root_leaf_sol(weights, point, eps, algo_mode)

    ## first root rules
    root_rules = root_sol.get_rules()
    values = root_sol.get_values()

    ## update analysis var
    total_num_rules = total_num_rules + num_rules - M

    ## compute value dict
    ## map gap (v - w) to dict
    value_dict = dict()
    pool_v = 0.0
    for (wi, w, v, _) in values:
      value_dict[wi] = v - w
      pool_v = pool_v - (v - w)

    value_dict[root_sol.pool_idx] = pool_v
    ## add up the original weights
    for (wi, w) in weights:
      value_dict[wi] = value_dict[wi] + w

#    print value_dict

    ## calculate imbalance for group idx
    imb_group = 0.0
    for (vi, tr, weights) in old_vips:
      if group[vi] == idx:
        vip_values = []
        for (wi, w) in weights:
          vip_values.append((wi, w, value_dict[wi]))
        vip_imb, _, _ = compute_vip_imbalance(vip_values, eps)
        imb_group = imb_group + vip_imb * tr

#          if OPT_W_PRIME_GROUP:
#            imb_group = imb_group + max(value_dict[wi] - w - eps, 0.0) * tr
#          else:
#            imb_group = imb_group + abs(w - value_dict[wi]) * tr * 0.5

#    print imb_group
    total_imb = total_imb + imb_group

  return total_num_rules, total_imb


def grouping(vips, num_groups, eps, C, ecmp_km_info, algo_mode):

  ## group vips
  group_solver = GroupSolver(vips)
  vips_, group = group_solver.group_vips(num_groups, K_MEANS)

  print "finish grouping"

  curve_dict = VipCurveDict(vips_, eps, ecmp_km_info, algo_mode)

  print "finish curve"

  imbs = []
  for c in C:
    num_rules, imb = group_and_ungroup(vips, vips_, group, curve_dict, c, eps, ecmp_km_info, algo_mode)
    imbs.append((c, num_rules, imb, vips_, group, ecmp_km_info))

  return imbs



def find_best_grouping(vips, num_groups, eps, C, ecmp_km_info, algo_mode):
  info = []

  if ecmp_km_info == None:
    l = grouping(vips, num_groups, eps, C, None, algo_mode)
    info = info + l
  else:
    N = len(vips[0][2])
    K_Range = int(math.log(N, 2.0))

    for t in range(K_Range, K_Range + 1):
      K = t
      M = (1 << K)
      ecmp_km_info = (NON_ECMP_Range, K, M)
      l = grouping(vips, num_groups, eps, C, ecmp_km_info, algo_mode)
      info = info + l

  return info

