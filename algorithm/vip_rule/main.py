import sys
from argparse import ArgumentParser
import random
import math
import vip_rule
from single_vip import *
from multiple_vip import *
from hw_layers import *
from group import *
from update import *
from operator import itemgetter, attrgetter

SINGLE_VIP = 1
MULTI_VIP = 2
MULTI_VIP_LAYER = 3
GROUP = 4

## stores the single vip weight input
class SVipInfo:

  def __init__(self, weights, errors):
    self.weights = weights
    self.errors = errors
    pass

  def __getitem__(self, idx):
    return self.weights[idx], self.errors[idx]

  def get_num_tests(self):
    return len(self.errors)


## stores the multiple vip weight / traffic / rules input
class MVipsInfo:

   def __init__(self, vips_wo_v, traffic, C):
     self.vips_wo_v = vips_wo_v
     self.traffic_tests = traffic
     self.C = C
     pass

   def __getitem__(self, idx):
     vips_ = zip(self.vips_wo_v, self.traffic_tests[idx])
     vips = map(lambda(((i,w),v)):(i,v,w), vips_)
     return vips

   def get_num_tests(self):
     return len(self.traffic_tests)

   def get_C(self):
     return self.C


## reading file
def reading_file(input, traffic_input):
  infile = open(input, 'r')
  strs = infile.readline().rsplit(' ')

  if (strs[0] == "l"):
    n_tests = int(strs[1])
    tests, tes = [], []
    for cnt in range(n_tests):
      status_str = infile.readline().rsplit(' ')
      n_weights = int(status_str[0])
      tolerable_error = float(status_str[1])

      w_str = infile.readline().rsplit(' ')
      weights = []
      for i in range(n_weights):
        weights.append((i, float(w_str[i])))
      tests.append(weights)
      tes.append(tolerable_error)

    infile.close()
    return SVipInfo(tests, tes)

  elif (strs[0] == "m"):
    n_weights = int(strs[1])
    n_vips = int(strs[2])
    C = []
    for s in strs[3:]:
      C.append(int(s))
    C.sort()

    vips_wo_v = []
    for i in range(0, n_vips):
      w_str = infile.readline().rsplit(' ')
      weights = []
      for j in range(0, n_weights):
        weights.append((j, float(w_str[j])))
      vips_wo_v.append((i, weights))

    traffic_file = open(traffic_input, 'r')
    t = int(traffic_file.readline())
    traffic_tests = []
    for i in range(0, t):
      vs = traffic_file.readline().rsplit(' ')
      volumes = []
      for j in range(0, n_vips):
        volumes.append(float(vs[j]))
      traffic_tests.append(volumes)

    infile.close()
    traffic_file.close()
    return MVipsInfo(vips_wo_v, traffic_tests, C)

## translate ecmp arg
def translate_ecmp_arg(n_weights, arg):
  NON_ECMP = 0
  if arg == 'all':
    K_Range = int(math.log(n_weights, 2.0))
    def f(k): return (NON_ECMP, k, (1<<k))
    return [None] + map(f, range(0, K_Range + 1))
  elif arg == 'max':
    K = int(math.log(n_weights, 2.0))
    M = (1<<K)
    return [(NON_ECMP, K, M)]
  elif arg == 'none':
    return [None]
  else:
    M = int(arg)
    K = int(math.log(M, 2.0))
    return [(NON_ECMP, K, M)]


## test single vip
def try_single_vip(args):
  ## Brute force or Heuristics
  algo_mode = BF
  if (args.heu):
    algo_mode = HEU

  ## Debug
  debug = None
  if (args.debug != None):
    debug = open(args.debug, 'w')

  ## Header
  outfile = open(args.output, 'w')
  outfile.write("vip_index, #rules, #ECMP rules, error, weights\n")


  svip_info = reading_file(args.input, None)
  n_tests = svip_info.get_num_tests()
  for i in range(n_tests):
    weights, tolerable_error = svip_info[i]

    ## construct ecmp metadata
    ecmp_infos = translate_ecmp_arg(len(weights), args.ecmp)

    for ecmp_info in ecmp_infos:
      res = find_single_vip_w_default(weights, 
             tolerable_error, algo_mode, ecmp_info)
      _, _, rules, values = res
      M = 0
      if ecmp_info != None:
        _, _, M = ecmp_info
      outfile.write('{}, {}, {}, '.format(i, len(rules), M))
      outfile.write('{}, '.format(tolerable_error))
      outfile.write('; '.join('{}'.format(w) for (_, w) in weights))
      outfile.write('\n')

      if (debug != None):
        debug.write("idx = {}\n".format(i))
        debug.write("weights = {}, error = {}\n".format(weights, tolerable_error))
        debug.write("approximations = {}\n".format(values))
        debug.write("#rules = {} (ECMP = {})\n".format(len(rules), M))
        debug.write("\n".join("p:{}, c:{}".format(*k) for k in rules))
        debug.write("\n------------\n")

  outfile.close()
  if (debug != None):
    debug.close()


## test vip curve
def try_vip_stair(args):
  ## Brute force or Heuristics
  algo_mode = BF
  if (args.heu):
    algo_mode = HEU

  ## Debug
  debug = None
  if (args.debug != None):
    debug = open(args.debug, 'w')

  ## Header
  outfile = open(args.output, 'w')
  outfile.write("vip_index, #ECMP rules, error, #hw_rules, imbalance, #sw_rules\n")


  svip_info = reading_file(args.input, None)
  n_tests = svip_info.get_num_tests()
  for i in range(n_tests):
    weights, tolerable_error = svip_info[i]

    ## construct ecmp metadata
    ecmp_infos = translate_ecmp_arg(len(weights), args.ecmp)

    for ecmp_info in ecmp_infos:
      curve_detail = plot_curve(weights, tolerable_error, ecmp_info, algo_mode)
      M = 0
      if ecmp_info != None:
        _, _, M = ecmp_info
      for (v_error, v_imb, root_rules, leaf_rules, values) in curve_detail:
        outfile.write('{}, {}, '.format(i, M))
        outfile.write('{}, {}, '.format(v_error, len(root_rules)))
        outfile.write('{}, {}\n'.format(v_imb, len(leaf_rules)))

        if (debug != None):
          debug.write("idx = {}\n".format(i))
          debug.write("weights = {}\n".format(weights))
          debug.write("root_approximations = {}\n".format(values))
          debug.write("error = {}, imbalance = {}\n".format(v_error, v_imb))
          debug.write("#root_rules = {} (ECMP = {})\n".format(len(root_rules), M))
          debug.write("\n".join("p:{}, c:{}".format(*k) for k in root_rules))
          debug.write("\n#leaf_rules = {}\n".format(len(leaf_rules)))
          debug.write("\n".join("p:{}, c:{}".format(*k) for k in leaf_rules))
          debug.write("\n------------\n")

  outfile.close()
  if (debug != None):
    debug.close()

## test update
def try_update(args):
  ## Brute force or Heuristics
  algo_mode = BF
  if (args.heu):
    algo_mode = HEU

  c_per_step = args.churn

  ## Debug
  debug = None
  file_step = None
  debug_step = None
  if (args.debug != None):
    debug = open(args.debug, 'w')
    file_step = args.debug + ".step"
    debug_step = open(file_step, "w")
    debug.write("StepFile = {}\n".format(file_step))

  ## Header
  outfile = open(args.output, 'w')
  outfile.write("index, #ECMP rules, #old_rules, #joint_rules, #new_rules, churn, min_churn, #steps, trunc_imb, trunc_churn\n")

#  multi_stage(0, None, None, 0, (0, 2,4))

  svip_info = reading_file(args.input, None)
  n_tests = svip_info.get_num_tests()
  for i in range(n_tests / 2):
    if (i % 100 == 99):
      print i
#  if True:
    try:
      old_ws, old_error = svip_info[2 * i]
      new_ws, new_error = svip_info[2 * i + 1]
      if (len(old_ws) != len(new_ws)):
        raise OpError("old weights and new weights miss match")

      ## construct ecmp metadata
      ecmp_infos = translate_ecmp_arg(len(old_ws), args.ecmp)
      for ecmp_info in ecmp_infos:
        old_rules, min_churn, res = update_to_new_weights(old_ws, new_ws,
                                                          old_error, new_error, 
                                                          ecmp_info, algo_mode)


        M = 0
        if ecmp_info != None:
          _, _, M = ecmp_info

        if (debug != None):
          debug.write("idx = {}\n".format(i))
          debug.write("old_weights = {}\n".format(old_ws))
          debug.write("old_error = {}\n".format(old_error))
          debug.write("new_weights = {}\n".format(new_ws))
          debug.write("new_error = {}\n".format(new_error))
          debug.write("#old_rules = {} (ECMP = {}))\n".format(len(old_rules), M))
          debug.write("\n".join("p:{}, c:{}".format(*k) for k in old_rules))
          debug.write("\n------------\n")

        (joint_rules, new_rules, churn) = res[-1]
        T = len(new_rules)
        for (joint_rules, new_rules, churn) in res:
          outfile.write('{}, {}, '.format(i, M))
          outfile.write('{}, {}, '.format(len(old_rules), len(joint_rules)))
          nstep = 1
          if (debug != None):
            nstep, res_ = multi_step_update(old_rules, new_rules, c_per_step, ecmp_info)
          outfile.write('{}, {}, {}, {},'.format(len(new_rules), churn, min_churn, nstep))
          ## try to truncate to fit
          imb_, churn_ = fit_T_imb_churn(new_ws, old_rules, new_rules, new_error, T)
          outfile.write('{}, {}'.format(imb_, churn_))

          outfile.write('\n')

          if (debug != None):
            debug.write("idx = {}\n".format(i))
            debug.write("#new_rules = {} (#joint_rules = {})\n".format(
                    len(new_rules), len(joint_rules)))
            debug.write("churn = {}\n".format(churn))
            debug.write("\n".join("p:{}, c:{}".format(*k) for k in new_rules))
            debug.write("\n------------\n")

            debug_step.write("idx = {}\n".format(i))
            debug_step.write("#new_rules = {} (#joint_rules = {})\n".format(
                         len(new_rules), len(joint_rules)))
            debug_step.write("#steps = {}\n".format(nstep))
            for cnt, step_rules in res_:
              debug_step.write("Step {}\n".format(cnt))
              debug_step.write("\n".join("p:{}, c:{}".format(*k) for k in step_rules))
              debug_step.write("\n===============\n")
    except OpError, e:
      print i, "error occurs, but will continue"


  outfile.close()
  if (debug != None):
    debug.close()
    debug_step.close()



## test multiple vips
def try_multi_vip(args):
  ## Brute force or Heuristics
  algo_mode = BF
  if (args.heu):
    algo_mode = HEU

  ## Debug
  debug = None
  if (args.debug != None):
    debug = open(args.debug, 'w')

  ## Header
  outfile = open(args.output, 'w')
  outfile.write("traffic_index, #ECMP rules, error, #hw_rules, imbalance, #sw_rules\n")

  mvip_info = reading_file(args.input, args.traffic)

  ## construct ecmp metadata
  ecmp_infos = translate_ecmp_arg(len(mvip_info[0][0][2]), args.ecmp)

  eps = args.error
  n_tests = mvip_info.get_num_tests()
  C = mvip_info.get_C()
  for i in range(n_tests):
    vips = mvip_info[i]

    ## customize C in multi_vip
    C = []
    nweights = len(mvip_info[0][0][2])
    c = nweights
    C.append(c)
    c = 50
    while (c <= 4000):
      if (c > nweights):
        C.append(c)
      c = c + 50


    for ecmp_info in ecmp_infos:
      M = 0
      if ecmp_info != None:
        _, _, M = ecmp_info
    
      res = solve_two_layer_trees(vips, C, eps, ecmp_info, algo_mode)
    
      for (c, (imb, root_rules), leaf_rules, _) in res:
        outfile.write('{}, {}, {}, '.format(i, M, eps))
        outfile.write('{}, {}, '.format(len(root_rules), imb))
        outfile.write(', '.join('{}'.format(len(leaf_rules[j])) for j in leaf_rules))
        outfile.write('\n')

        if (debug != None):
          debug.write("traffic_idx = {}, error = {}\n".format(i, eps))
          debug.write("imbalance = {}\n".format(imb))
          debug.write("#root_rules = {} ({} ECMP rules)\n".format(len(root_rules), M))
          debug.write("\n".join("p:{}, c:{}, vip:{}".format(*k) for k in root_rules))
          debug.write("\n")
          for j in leaf_rules:
            l = leaf_rules[j]
            debug.write("#leaf_rules = {}, for switch {}\n".format(len(l), j))
            debug.write("\n".join("p:{}, c:{}, vip:{}".format(*k) for k in l))
            debug.write("\n")

  outfile.close()
  if (debug != None):
    debug.close()


## test grouping
def try_grouping(args):
  ## Brute force or Heuristics
  algo_mode = BF
  if (args.heu):
    algo_mode = HEU

  ## Debug
  debug,debug_vips, debug_traffic = None, None, None
  file_vips, file_traffic = None, None
  if (args.debug != None):
    debug = open(args.debug, 'w')
    file_vips = args.debug + ".vips"
    file_traffic = args.debug + ".traffic"
    debug_vips = open(file_vips, "w")
    debug_traffic = open(file_traffic, "w")
    debug.write("group_vips_filename = {}\n".format(file_vips))
    debug.write("group_traffic_filename = {}\n".format(file_traffic))
    
  ## Header
  outfile = open(args.output, 'w')
  outfile.write("traffic_index, #ECMP rules, error, #groups, #hw_rules, imbalances\n")

  mvip_info = reading_file(args.input, args.traffic)

  ## construct ecmp metadata
  ecmp_infos = translate_ecmp_arg(len(mvip_info[0][0][2]), args.ecmp)
  n_tests = mvip_info.get_num_tests()
  C = mvip_info.get_C()

  ## customize C
  C = []
  nweights = len(mvip_info[0][0][2])
  c = nweights
  C.append(c)
  c = 50
  while (c <= 4000):
    if (c > nweights):
      C.append(c)
    c = c + 50

  eps = args.error
  num_group = args.group
  for i in range(n_tests):
    vips = mvip_info[i]
    vips_, group_ = None, None

    for ecmp_info in ecmp_infos:
      M = 0
      if ecmp_info != None:
        _, _, M = ecmp_info

#      res = find_best_grouping(vips, num_group, eps, C, ecmp_info, algo_mode)
      res = grouping(vips, num_group, eps, C, ecmp_info, algo_mode)
      for (c, nrules, imb, nvips, ngroup, _) in res:
        outfile.write("{}, {}, {}, ".format(i, M, eps))
        outfile.write("{}, {}, {} \n".format(num_group, c, imb))
        vips_, group_ = nvips, ngroup

    if (debug != None):
      debug_vips.write("m {} {} ".format(len(vips_[0][2]), len(vips_)))
      debug_vips.write(" ".join("{}".format(k) for k in C))
      debug_vips.write("\n")
      for (idx, t, weights) in vips_:
        debug_vips.write(" ".join("{}".format(k[1]) for k in weights))
        debug_vips.write("\n")
      debug_vips.write("=========ending testcase {}=========\n".format(i))

      debug_traffic.write("1\n")
      debug_traffic.write(" ".join("{}".format(k[1]) for k in vips_))
      debug_traffic.write("\n")
      debug_traffic.write("=========ending testcase {}=========\n".format(i))

      for idx in group_:
        debug.write("VIP {} belongs to Group {}\n".format(idx, group_[idx]))
      debug.write("=========ending testcase {}=========\n".format(i))

    

  outfile.close()
  if (debug != None):
    debug.close()
    debug_vips.close()
    debug_traffic.close()




## parsing
def parse_args(str):
  parser = ArgumentParser(description = 'run simulation')

  parser.add_argument('-mode', action = 'store',
                    choices = ['single_vip', 'vip_stair', 'update',
                                'multi_vip', 'grouping'],
                    help='modes: single_vip, vip_stair, update,'
                         + 'multi_vip, grouping');
  parser.add_argument('-input', action = 'store', default = None)
  parser.add_argument('-output', action = 'store', default = None)
  parser.add_argument('-traffic', action = 'store', default = None)
  parser.add_argument('-error', action = 'store', type = float, default = 0.0001) #default = 0.001)
  parser.add_argument('-churn', action = 'store', type = float, default = 0.1)
  parser.add_argument('-group', action = 'store', type = int, default = 100)
  parser.add_argument('-debug', action = 'store', default = None)
  parser.add_argument('-ecmp', action = 'store', default = 'max',
                    help='ecmp:max, none, all, #ecmp_rules');
  parser.add_argument('-heu', action = 'store_true')
  parser.add_argument('-bf', action = 'store_true')
#  parser.add_argument('-bits', action = 'store', type = int, default = 32)

  args = parser.parse_args(str)

  return args


# Main logic starts here

args = parse_args(sys.argv[1:])

if args.mode == 'single_vip':
   try_single_vip(args)

elif args.mode == 'vip_stair':
   try_vip_stair(args)

elif args.mode == 'update':
   try_update(args)

elif args.mode == 'multi_vip':
   try_multi_vip(args)

elif args.mode == 'grouping':
   try_grouping(args)

else:
  pass
