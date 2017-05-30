import sys
import random
import math
from vip_rule import *
from single_vip import *
from vip_curve import *
from operator import itemgetter, attrgetter


## record the result of one instance
class MVipsSolution:

  def __init__(self, point_dict):
    self.point_dict = point_dict
    self.rule = None
    self.imb = None
    self.values = None

    pass

  def full_info(self, vips, curve_dict, c, ecmp_km_info):
    self.__initialize_rule_list(vips, curve_dict, c, ecmp_km_info)
    

  def __getitem__(self, i):
    return self.point_dict[i]

  def get_rules(self):
    return self.rules

  def get_imbalance(self):
    return self.imb


  def get_values(self):
    return self.values


  def get_kth_values(self, kth):
    return values[kth]


  ## solve one instance and give the rule list
  def __initialize_rule_list(self, vips, curve_dict, c, ecmp_km_info): 
    ## initialize
    M = 0
    if (ecmp_km_info == None):
      M = 0
    else:
      (NON_ECMP_Range, K, M) = ecmp_km_info

    ## initialize rule list
    final_rules, final_imb, final_values = [], 0.0, []
    final_values = dict()
    need_ecmp_rules = (ecmp_km_info != None)

    svip_solver = SVipSolver()
    ## compute rule list for every vip
    for (idx, volume, weights) in vips:
      ## retrive information
      curve = curve_dict[idx]
      p_i = self.point_dict[idx]
      (num_rules, imb, error_now, d) = curve[p_i]

      ## extract the rules directly from values
      values = d[VALUE_DICTKEY]
      pool_idx = d[POOL_DICTKEY]
      try:
        ecmp_info = d[ECMP_DICTKEY]
      except KeyError:
        ecmp_info = None

      ## Below is to re-compute the solution from the solver
#     ==== BEGIN COMMENT ====
#      sel_k, t_error = d[APPROX_K_DICTKEY], d[TERROR_DICTKEY]
#      ssol = SVipSolution(values)
#      ssol.init_rules_with_ecmp_info(pool_idx, ecmp_info)

#      ssol = svip_solver.solve_instance(weights, t_error, ecmp_info, FIXED, sel_k)
#      values = ssol.get_values()
#     ==== END COMMENT ====

      rules = ssol.get_rules()

      ## record values
      final_values[idx] = values[:]

      ## generate ECMP rules
      if (need_ecmp_rules):
        def map_ecmp((a,b)): return ('*', a, b)
        final_rules = final_rules + map(map_ecmp, rules[0:M])
        need_ecmp_rules = False
      ## generate vip-specific rules
      if (num_rules > 0):
        def map_idx((a,b)): return (str(idx), a, b)
        final_rules = final_rules + map(map_idx, rules[M:])

      ## add up imbalance
      final_imb = final_imb + imb * volume

    ## assign to self's variables
    self.rules, self.imb = final_rules, final_imb
    self.values = final_values


## solve one instance (vips, curves, c and default rule info)
class MVipsSolver:

  def __init__(self):
    pass

  ## return a solution
  def solve_instance(self, vips, curve_dict, c, ecmp_km_info):
    INVALID_IMB = (1.0, 0.0, c + 1)

    ## initialize point dict
    point_dict = []
    point_dict.extend([0] * len(vips))

    M = 0
    if (ecmp_km_info == None):
      M = 0
    else:
      (NON_ECMP_Range, K, M) = ecmp_km_info


    ## initialize curve pointer and c_now
    c_now = c - M
    for (idx, t, weights) in vips:
#      curve = curve_dict[idx].get_curve()
      curve = curve_dict[idx]
      p = curve[0]
      c_now = c_now - (p[0] - M)

    if (c_now < 0):
      return None

    ## repeat moving one curve pointer
    while (True):
      best_dec_ratio, best_vip_idx, best_curve = 0.0,  -1, None

      ## iterate over all curves and select the best curve pointer 
      ## which gives the max dec_ratio.
      for (idx, volume, weights) in vips:
        curve = curve_dict[idx]
        p_i = point_dict[idx]
        if (p_i + 1 < len(curve)):
          extra_rules = curve[p_i + 1][0] - curve[p_i][0]
          if (extra_rules <= c_now):
            decrease = (curve[p_i][1] - curve[p_i + 1][1]) * volume
            dec_ratio = decrease / extra_rules
            if (dec_ratio > best_dec_ratio):
              best_dec_ratio, best_vip_idx, best_curve = dec_ratio, idx, curve
      if (best_vip_idx < 0):
        break

      ## move the best curve pointer
      # print "BEST", best_vip_idx, best_decrease, best_extra_rules
      p_i = point_dict[best_vip_idx] + 1
      point_dict[best_vip_idx] = p_i
      c_now = c_now - (best_curve[p_i][0] - best_curve[p_i - 1][0])

    solution = MVipsSolution(point_dict)
    return solution



## solve multiple vips with a list of c (max #rules)
def solve_multiple_vips(vips, C, ecmp_km_info, eps):
#  TOLERABLE_ERROR = 1e-4

  curve_dict = VipCurveDict(vips, eps, ecmp_km_info)
  solver = MVipsSolver()

  vips_info = []
  for c in C:
    sol = solver.solve_instance(vips, curve_dict, c, ecmp_km_info)
    if (sol == None):
      vips_info.append((c, [], 2.0, ecmp_km_info))
    else:
      sol.full_info(vips, curve_dict, c, ecmp_km_info)
      vips_info.append((c, sol.get_rules(), sol.get_imbalance(), ecmp_km_info))
  return vips_info



# find the best rule for multiple vips
# minimize the total imbalance
# try different default rules (no ecmp v.s x-ecmp)
def find_best_multiple_vips(vips, C, ecmp_km_info):

  multiple_vips_info = []

  best_rules, best_imb, best_sol = None, 2, ""

  if ecmp_km_info == None:
    vips_res = solve_multiple_vips(vips, C, None)
    multiple_vips_info = multiple_vips_info + vips_res
 

  N = len(vips[0][2])
  K_Range = int(math.log(N, 2.0))

  for t in range(K_Range, K_Range + 1):
    K = t
    M = (1 << K)
    ecmp_km_info = (NON_ECMP_Range, K, M)

    vips_res = solve_multiple_vips(vips, C, ecmp_km_info)
    multiple_vips_info = multiple_vips_info + vips_res

  return multiple_vips_info
