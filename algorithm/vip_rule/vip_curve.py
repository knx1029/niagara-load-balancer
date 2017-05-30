import sys
import random
import math
from vip_rule import *
from single_vip import *
from operator import itemgetter, attrgetter


ECMP_DICTKEY = 'ecmp'
VALUE_DICTKEY = 'value_list'
POOL_DICTKEY = 'pool'
RULE_DICTKEY = 'rule'
LEAF_DICTKEY = 'leaf'

# compute monotonic points (x, y, _)
# s.t, there is no pair of (x1, y1) and (x2, y2), s.t
# (x1 >= x2) && (y1 >= y2)
def monotonic(points):
  
  def cmp_points(p1, p2):
    ans = 0.0
    if (p1[0] != p2[0]): 
      return p1[0] - p2[0]
    else:
      if (p1[1] < p2[1]):
        return -1;
      else:
        return 1

  points.sort(cmp = cmp_points)
  new_points = []
  cur_min_imb = 0.0
  for k in range(0, len(points)):
    if (k == 0 or double_cmp(points[k][1] - cur_min_imb) < 0):
      new_points.append(points[k])
      cur_min_imb = points[k][1]

  return new_points    

# brute force find all possible (#rules, imbalance)
#def bf_imb_rule_points(approx_list, ecmp_info, tolerable_error):
def bf_imb_rule_points(approx_list, weight_map, pool_idx, ecmp_info, tolerable_error, eps, ws, algo_arg):

  def create_point(value_list):
    weight_map_ = weight_map.copy()
    num_rules = get_number_rules(value_list, weight_map_, pool_idx)
    if (num_rules < 0):
      return None

    if (ecmp_info == None):
      num_rules = num_rules + 1
    else:
      (_, non_ecmp_exp, _, M) = ecmp_info
      if (non_ecmp_exp < 0):
        num_rules = num_rules + M
      else:
        num_rules = num_rules + M + 1


    (imbalance, error, _) = compute_vip_imbalance(value_list, eps)

    d = {VALUE_DICTKEY: value_list, ECMP_DICTKEY: ecmp_info,
         POOL_DICTKEY: pool_idx};

    point = (num_rules, imbalance, error, d)

    return point


  ## main logic starts here

  points = []
  num_rules = 0

  exp = 1 << len(approx_list)

  def get_k_from_heu():
    _, value_list = heu_pick_values(approx_list, tolerable_error)
    expo, k = 0, 0
    for (idx, w, _, _) in approx_list:
      for (idx_, w_, v_, _) in value_list:
        if (idx == idx_ and v_ > w_):
          k = k + (1 << expo)
      expo = expo + 1
    return k


  ## brute force search
  # for k in range(0, exp):
  ## heuristic pick    
  # for k in [get_k_from_heu()]:

  if algo_arg == BF:
    k_choices = range(0, exp)
    for k in k_choices:
      value_list = get_value_list_from_choice(approx_list, k)
      point = create_point(value_list)
      if point != None:
        points.append(point)
  elif algo_arg == HEU:
    _, full_value_list = heu_pick_values(approx_list, tolerable_error)
    token_list = get_token_list(full_value_list)
    token_list.sort(key=itemgetter(1))

    #construct ordered token list
    bucket, exp_old, op_old = [], -1, -1
    ordered_token_list = []
    for token in token_list:
      (op, exp, idx) = token
      if (exp != exp_old):
        while len(bucket) > 0:
          ordered_token_list.append(bucket.pop())

      exp_old = exp
      if len(bucket) == 0 or op_old == op:
        bucket.append(token)
        op_old = op
      else:
        ordered_token_list.append(bucket.pop())
        ordered_token_list.append(token)
    while len(bucket) > 0:
      ordered_token_list.append(bucket.pop())

#    print ">", token_list, "\n===\n", ordered_token_list, "<"

    # initialize value list
    value_list = []
    for (idx, w, v, vlist) in full_value_list:
      value_list.append((idx, w, 0.0, []))
    points.append(create_point(value_list))

    for (op, exp, idx) in ordered_token_list:
      new_value_list = []
      unit = op * 1.0 / (1 << exp)
      for one_value in value_list:
        (idx_, w, v, vlist) = one_value
        if (idx_ == idx):
          vvlist = vlist[:]
          vvlist.append((op, exp))
          new_value_list.append((idx_, w, v + unit, vvlist))
        else:
          new_value_list.append(one_value)
      value_list = new_value_list
      point = create_point(value_list)
      if (point != None):
        points.append(point)
      
      
  else:
    pass

  points = monotonic(points)

  return points



## get the step-like curve (x = #rules, y = imbalance, z = tolerable_error)
## for a weight list
def opt_get_imb_rule_curve_ws(weights, eps, pool_idx, weights_map, ecmp_info, algo_arg):

  ## Flags
  FROM = 1
  FROM_L = 0
  FROM_U = 1
  TO = 2
  TO_L = 0
  TO_U = 2
  FLAG_INV = FROM | TO #3
  FROM_L_TO_L = FROM_L | TO_L #0
  FROM_L_TO_U = FROM_L | TO_U #1
  FROM_U_TO_L = FROM_U | TO_L #2
  FROM_U_TO_U = FROM_U | TO_U #3

  ## compute all the intermediate steps to Ls and Us to approximate w
  ## until the error < tolerable_error
  def get_Ls_Us_w(old_w, eps):

    def inverse_sign((sign, exp)): return (-sign, exp)
    def inverse_flag(flag): return FLAG_INV ^ flag

#    if (double_cmp(old_w) == 0):
#      return []

    w = abs(old_w)
    if (double_cmp(w) == 0):
      return ((w, 0, [], TO_L), (w, 0, [], TO_U))

    lower_bound, upper_bound = 0.0, 1.0
    error = max(w - lower_bound, upper_bound - w) 
    tokens = []
#    symb_L, symb_U = ['L'], ['U']
    symb_L, symb_U = [], [(1, 0)]
    use_arg = USE_L_ONLY
    tokens.append((w, w - lower_bound, symb_L[:], TO_L))

    while (double_cmp(error - eps) > 0):
      approx_arg = 0
      if (double_cmp((w - lower_bound) - eps) > 0):
        approx_arg = approx_arg | APPROX_L_ONLY
      if (double_cmp((upper_bound - w) - eps) > 0):
        approx_arg = approx_arg | APPROX_R_ONLY

      res = approximate_w_more(w, lower_bound, symb_L, upper_bound, symb_U, approx_arg | use_arg)

      if (approx_arg & APPROX_L_ONLY > 0):
        L = res[1]
        token = (w - lower_bound, w - res[0], L[:], TO_L)
        lower_bound = res[0]
        tokens.append(token)
        symb_L = L

      if (approx_arg & APPROX_R_ONLY > 0):
        U = res[3]
        token = (upper_bound - w, res[2] - w, U[:], TO_U)
        upper_bound = res[2]
        tokens.append(token)
        use_arg = use_arg | USE_R_ONLY
        symb_U = U

      error = max(upper_bound - w, w - lower_bound)

    if (old_w < 0):
      tokens = map(lambda((a,b,c,d)): (a,b, map(inverse_sign, c), inverse_flag(d)), tokens)


    return tokens

  def cmp_e_token(e1, e2):
    if (double_cmp(e1[0] - e2[0]) != 0):
      return double_cmp(e2[0] - e1[0])
    else:
      return double_cmp(e2[1] - e1[1])




  # main logic starts

  ## build a dict
  l_dict, u_dict = dict(), dict()

  ## compute all possible errors, namely, Z-value for the curve
  e_tokens = []
  none_count = 0
  for (idx, w) in weights:
    if (idx == pool_idx):
      continue
    e_tokens_  = get_Ls_Us_w(w, eps)
#    print "w and its  tokens: ", w, e_tokens_
    e_tokens = e_tokens + map(lambda((a,b,c,d)):(a,b,c,d,idx), e_tokens_)
    if (double_cmp(w) == 0):
      l_dict[idx] = (0, [])
      u_dict[idx] = (0, [])
    elif (double_cmp(w) > 0):
      l_dict[idx] = (w, [])
      u_dict[idx] = None
      none_count = none_count + 1
    else:
      l_dict[idx] = None
      u_dict[idx] = (-w, [])
      none_count = none_count + 1

  e_tokens.sort(cmp=cmp_e_token)



  ## compute X, Y
  all_points = []

  for i in range(len(e_tokens)):
    e_token = e_tokens[i]
    e_before, e_after, list, flag, t_idx = e_token
    tl, tu = l_dict[t_idx], u_dict[t_idx]

    if (flag & TO == TO_L):
      l_dict[t_idx] = (e_after, list)
      if (tl == None):
        none_count = none_count - 1
    elif (flag & TO == TO_U):
      u_dict[t_idx] = (e_after, list)
      if (tu == None):
        none_count = none_count - 1
    else:
      raise OpError("Wrong Flag {}".format(flag))


    if (none_count > 0):
      continue

    e = e_before - 1e-6
    approx_list = []
    for (idx, w) in weights:
      if (idx == pool_idx):
        continue
      (le, L), (ue, U) = l_dict[idx], u_dict[idx]
      approx_list.append((idx, w, (w - le, L), (w + ue, U)))

    if True:
      approx_list = []
      for (idx, w) in weights:
        if (idx == pool_idx):
          continue
        L, U = approximate(w, e)
        approx_list.append((idx, w, L, U))

#    raise OpError("right error?")


    points_e = bf_imb_rule_points(approx_list, weights_map, pool_idx, ecmp_info, e, eps, weights, algo_arg)
    all_points = all_points + points_e


  all_points = monotonic(all_points)

#  print "ECMP_INFO:", ecmp_info
#  print "Weights:", weights
#  print "Curves:", all_points

  return all_points


## get the step-like curve (x = #rules, y = imbalance, z = tolerable_error)
## for a weight list
## only use one rule list (obtained from eps) and truncate it step-by-step
def get_imb_rule_curve_from_svip_sol(ws, eps, ecmp_info, algo_arg):
  ## main logic starts here

  ## get the rules (whose tolerable error = eps)
  solver = SVipSolver()
  sol = solver.solve_instance(ws, eps, ecmp_info, algo_arg)

  values = sol.get_values()
  pool_idx = sol.get_pool_idx()
  rules = sol.get_rules()
  total_num_rules = len(rules)


  M = 1
  if ecmp_info != None:
    _, _, _, M = ecmp_info


  ## initialize
  vlist = []
  value_dict = {}
  for v in values:
    (idx, w, _, _) = v
    item = (idx, w, 0.0, [])
    value_dict[idx] = item
    vlist.append(item)
  
  ## the very first point
  all_points = []

  ## construct the rules by truncating the rule list
  for i in range(M, total_num_rules + 1):
    ## create a new solution
    vlist = []
    for (idx, w, v, list) in value_dict.values():
      vlist.append((idx, w, v, list[:]))

    d = {VALUE_DICTKEY: vlist, ECMP_DICTKEY: ecmp_info,
         POOL_DICTKEY: pool_idx, RULE_DICTKEY: rules[0:i], 
         LEAF_DICTKEY: rules[i+1:]};
    (imb, error, pool_e) = compute_vip_imbalance(vlist, eps)

    point = (i, imb, error, d)
    all_points.append(point)

    if (i >= total_num_rules):
      continue

    (s1, w1_idx) = rules[i]

    ## find where the token comes from
    for j in range(i - 1, -1, -1):
      (s2, w2_idx) = rules[j]
      if (overlap(s1, s2) == CONTAINED):
#        print s1, s2, w1_idx, w2_idx
        break

    exp = get_level(s1)
    unit = get_unit(exp)
    ## update the value list of w1 & w2
    if (w1_idx != pool_idx):
      (_, w1, v1, l1) = value_dict[w1_idx]
      l1.append((1, exp))
      v1 = v1 + unit
      value_dict[w1_idx] = (w1_idx, w1, v1, l1)

    if (w2_idx != pool_idx):
      (_, w2, v2, l2) = value_dict[w2_idx]
      l2.append((-1, exp))
      v2 = v2 - unit
      value_dict[w2_idx] = (w2_idx, w2, v2, l2)

  return all_points




class VipCurve:

  def __init__(self, ws, eps, ecmp_km_info, algo_arg):
    self.ws = ws[:]
    self.eps = eps
    self.ecmp_km_info = ecmp_km_info
    self.algo_arg = algo_arg
    self.__curve = None
    self.__start_idx = 0
    pass

  def truncate(self, kth):
    self.__start_idx = self.__start_idx + kth

  def __get_curve(self):
    if self.__curve == None:
      self.__compute_curve()
    return self.__curve

  def __getitem__(self, i):
    c = self.__get_curve()
    return c[self.__start_idx + i]

  def __len__(self):
    c = self.__get_curve()
    return len(c) - self.__start_idx

  ## vips = [{idx, volume, weights}]
  ## try all possible strategies for multiple vips
  ## given the fixed default rule info
  def __compute_curve(self):
    curve = []

    if (self.ecmp_km_info == None):
      curve = self.__compute_curve_full_ecmp(None)
    else:
      ecmp_info_list = get_ecmp_info_list(self.ecmp_km_info)
      for ecmp_info in ecmp_info_list:
        ## structure of ecmp_info: (non_ecmp, non_ecmp_exp, K, M) = ecmp_info
        sub_curve = self.__compute_curve_full_ecmp(ecmp_info)
        curve = curve + sub_curve

    self.__curve = monotonic(curve)

  # vips = [{idx, volume, weights}]
  # try all possible strategies for multiple vips
  # given the fixed default rule info
  def __compute_curve_full_ecmp(self, ecmp_info):
#    print "start"

#    weights, weights_map, pool_idx = init_weights_from_ecmp(self.ws, ecmp_info)
#    points = opt_get_imb_rule_curve_ws(weights, self.eps, pool_idx, weights_map, ecmp_info, self.algo_arg)
    points =  get_imb_rule_curve_from_svip_sol(self.ws, self.eps, ecmp_info, self.algo_arg)
#    print "end"
    return points



class VipCurveDict:

  def __init__(self, vips, eps, ecmp_km_info, algo_arg):
    self.vips = vips[:]
    self.eps = eps
    self.ecmp_km_info = ecmp_km_info
    self.algo_arg = algo_arg
    self.__initialize_curve_list()
    pass


  def __getitem__(self, i):
    return self.__curve_list[i]

  def __initialize_curve_list(self):
    self.__curve_list = []
    self.__curve_list.extend([None] * len(self.vips))

    for (idx, volume, weights) in self.vips:
      self.__curve_list[idx] = VipCurve(weights, self.eps, self.ecmp_km_info, self.algo_arg)
#      curve = self.__curve_list[idx].get_curve()
      point = self.__curve_list[idx][0]
     
## check the correctness of the combined root rules and leaf rules
def check_correctness(weights, rules, tolerable_error):
  def weight_str(s):
    exp= len(s) - s.count('*')
    unit = 1.0 / (1 << exp)
    return unit

  def joint(s, s_):
    t = ''
    for i in range(len(s)):
      if (s[i] == '*'):
        t = t + s_[i]
      else:
        t = t + s[i]
    return t


  w_map = dict()
  for (idx, _) in weights:
    w_map[idx] = 0.0

  # print '\n'.join('{},{}'.format(*k) for k in rules)

  for i in reversed(range(len(rules))):
    (s, idx) = rules[i]
    unit = weight_str(s)
    w_map[idx] = w_map[idx] + unit

    for j in reversed(range(i)):
      (s_, idx_) = rules[j]
      res = overlap(s, s_)

      if (res == OVERLAP or res == CONTAINED):
        unit_ = weight_str(joint(s, s_))
        w_map[idx_] = w_map[idx_] - unit_
        unit = unit - unit_
        if (double_cmp(unit) == 0):
          break
        elif (double_cmp(unit) < 0):
          raise OpError("unit becomes negative {} after {}".format(unit, unit_))

      elif (res != NONE):
        raise OpError("{} in matching rule {} and {}".format(res, s, s_))

  for (idx, w) in weights:
    delta = w - w_map[idx]
    if (double_cmp(abs(delta) - tolerable_error) > 0):
      raise OpError( "Wrong with {}, where w = {}, w' = {}".format(idx, w, w_map[idx]))


## compute root solution and leaf solution
def get_root_leaf_sol(point):

  #extract point information
  (num_rules, imb, error_now, d) = point
  values = d[VALUE_DICTKEY]
  pool_idx = d[POOL_DICTKEY]
  
  try:
    ecmp_info = d[ECMP_DICTKEY]
  except KeyError:
    ecmp_info = None

  root_rules = d[RULE_DICTKEY]
  leaf_rules = d[LEAF_DICTKEY]

  root_sol = SVipSolution(values)
  root_sol.set(values, pool_idx, root_rules)
  leaf_sol = SVipSolution(None)
  leaf_sol.set(None, -1, leaf_rules)
  return root_sol, leaf_sol



## Below is an alternative to compute root and leaf rules
## instead of retrieving from the point
## compute root solution and leaf solution
def __get_root_leaf_sol(weights, point, eps, algo_arg):

    svip_solver = SVipSolver()

    #extract point information
    (num_rules, imb, error_now, d) = point
    t_value_list = d[VALUE_DICTKEY]
    t_pool_idx = d[POOL_DICTKEY]
    try:
      ecmp_info = d[ECMP_DICTKEY]
    except KeyError:
      ecmp_info = None

    ## get root rule list
    root_sol = SVipSolution(t_value_list)
    root_sol.init_rules_with_ecmp_info(t_pool_idx, ecmp_info)
    root_rules = root_sol.get_rules()
    values = root_sol.get_values()
    (v_imb, v_error, v_pool_e) = compute_vip_imbalance(values, eps)

    if (len(root_rules) != num_rules):
      print "Error", point
      print values
      print "\n".join("{} {}".format(*k) for k in root_rules)
      raise OpError("Wrong in Vip Curve, num_rules = {}, but #root_rules = {}".format(num_rules, len(root_rules)))

    new_w = map(lambda((idx, w, v, vlist)): (idx, w - v), values)
    new_w.append((root_sol.pool_idx, v_pool_e))
    new_w.sort(key = itemgetter(1), reverse = True)
    new_pool_idx = new_w[0][0]


    ## old_weight_map[i] = weight[i] - w[i]
    ## new_weight_map[i] = old_weight_map[i] + v[i]
    init_w_map = dict()
    for (idx, w) in weights:
      init_w_map[idx] = w
    for (idx, w, v, _) in values:
      init_w_map[idx] = init_w_map[idx] - w + v
    init_w_map[t_pool_idx] = init_w_map[t_pool_idx] - v_pool_e

    if False:
      print "point = {}".format(point)
      print "weights = {}".format(weights)
      print "values = {}".format(map(lambda(x):(x[0], x[1], x[2]), values))
      print "new_weights = {}".format(new_w)
      print "init_w_map = {}".format(init_w_map)


    leaf_sol = svip_solver.solve_special(new_w, init_w_map, new_pool_idx, eps, root_sol.final_sf_map, algo_arg)
    leaf_rules = leaf_sol.get_rules()

    ## check correctness
    check_correctness(weights, root_rules + leaf_rules, eps)

    return root_sol, leaf_sol


## curve info
def plot_curve(weights, eps, ecmp_km_info, algo_arg):
  vips = [(0, 1.0, weights)]
  curve_dict = VipCurveDict(vips, eps, ecmp_km_info, algo_arg)

#  curve = curve_dict[0].get_curve()
  curve = curve_dict[0]

  curve_detail = []
  for p_i in range(len(curve)):
#    print p_i
    (num_rules, imb, error_now, d) = curve[p_i]
    root_sol, leaf_sol = get_root_leaf_sol(curve[p_i])

    root_rules = root_sol.get_rules()
    root_values = root_sol.get_values()
    (v_imb, v_error, v_pool_e) = compute_vip_imbalance(root_values, eps)
    leaf_rules = leaf_sol.get_rules()

    detail = (v_error, imb, root_rules, leaf_rules, root_values)
    curve_detail.append(detail)

  return curve_detail
  
    

