import __init__
import sys
from argparse import ArgumentParser
import random
import math
from operator import itemgetter, attrgetter
import vip_rule
from vip_rule.hw_layers import *
from vip_rule.group import *
from vip_rule.update import *

## parsing
def parse_args(str):
  parser = ArgumentParser(description = 'run simulation')

  parser.add_argument('-mode', action = 'store',
                    choices = ['single_vip', 'vip_stair', 'update',
                                'multi_vip', 'grouping'],
                    help='modes: single_vip, vip_stair, update,'
                         + 'multi_vip, grouping');
  parser.add_argument('-error', action = 'store', type = float, default = 0.001)
  parser.add_argument('-churn', action = 'store', type = float, default = 0.1)
  parser.add_argument('-group', action = 'store', type = int, default = 100)
  # for ecmp, all is not supported
  parser.add_argument('-ecmp', action = 'store', default = 'max',
                    help='ecmp:max, none, all, #ecmp_rules');
  parser.add_argument('-heu', action = 'store_true')
  parser.add_argument('-bf', action = 'store_true')
#  parser.add_argument('-bits', action = 'store', type = int, default = 32)

  args = parser.parse_args(str)

  return args


## Call algorithm to generate abstract bit matching rules
## Call conversion to iptable u32 rules
class RuleGenerator:

  def __init__(self):
    self.algo_wrapper = AlgorithmWrapper()
    pass


  ## generate mvip rules
  def generate_mvip_rules(self, argv, vips):

    ## parse arguments
    args = parse_args(argv)

    ## transform algorithm's input and output
    trans = AlgoInOutTransformer()
    for vip in vips:
      trans.add_vip(vip)
    algo_vips = trans.to_algo_vips()

    print algo_vips

    res = self.algo_wrapper.solve_multi_vip(args, algo_vips, 10)
    algo_hw_rules, algo_sw_rules, algo_imb = res
    hw_rules = trans.from_algo_rules(algo_hw_rules)
    sw_rules = []

    print "HW"    
    print "\n".join("{}".format(r) for r in  hw_rules)

    ## here we concatenate all rules for sw together
    ## as an optimization, we can let each sw to keep their own
    for j in algo_sw_rules:
     sw_rule = trans.from_algo_rules(algo_sw_rules[j])
     sw_rules = sw_rules + sw_rule

    print "SW"
    print "\n".join("{}".format(r) for r in sw_rules)

    return hw_rules, sw_rules


  ## TODO
  def update_mvip_rules(self, old_args, old_res, new_args):
    pass


  def test(self):
    argv = ["-mode", "multi_vip", "-ecmp", "none", "-heu", "-error", "0.001"]
    # Main logic starts here

    args = parse_args(argv)
 
    # a VIP is a three tuple (vip_id, traffic, [(dev_id, w)])
    # VIPs must numbered from [0, nvips)
    # Clusters must numbered from [0, nweights)

    if args.mode == 'multi_vip':
      vip1 = ("vip1", 0.6, [(2, 0.3), (1, 0.7)])
      vip2 = ("vip2", 0.4, [(3, 0.5), (1, 0.5)])
      vips = [vip1, vip2]

      rules = self.generate_mvip_rules(argv, vip)
      return rules

    elif args.mode == 'update':
      pass

    elif args.mode == 'grouping':
      pass

    else:
      pass


class AlgorithmWrapper:

## TODO : only solve_multi_vip works
  @staticmethod
  def translate_ecmp_arg(n_weights, arg):
    if arg == 'max':
      K = int(math.log(n_weights, 2.0))
      M = (1<<K)
      return (0, K, M)
    elif arg == 'none':
      return None
    else:
      M = int(arg)
      K = int(math.log(M, 2.0))
      return [(0, K, M)]


  ## solve multiple vips
  def solve_multi_vip(self, args, vips, c):

    ## Brute force or Heuristics
    algo_mode = BF
    if (args.heu):
      algo_mode = HEU

    ## construct ecmp metadata
    ecmp_info = self.translate_ecmp_arg(len(vips[0][2]), args.ecmp)
    
    ## run
    eps = args.error
    res = solve_two_layer_trees(vips, [c], eps, ecmp_info, algo_mode)
    c, (imb, root_rules), leaf_rules, _  = res[0]

    return root_rules, leaf_rules, imb



# a VIP is a three tuple (vip_id, [(dev_id, w)], traffic)
# Keep a mapping between real vip_id & dev_id and what the algorithm sees
# Reasons: algorithm needs VIPs numbered in [0, nvips), Devs numbered in [0, nweights)
class AlgoInOutTransformer:

  def __init__(self):
    self.nvips = 0
    self.vips = []

    self.ndevs = 0
    self.dev_dict = dict()
    self.devs = []

    self.total_traffic = 0.0
    pass

  def add_vip(self, vip):
     vip_id, traffic, devices = vip
     self.vips.append((vip_id, traffic, devices))
     for (dev_id, w) in devices:
       if not (dev_id in self.dev_dict):
         self.dev_dict[dev_id] = self.ndevs
         self.ndevs = self.ndevs + 1
         self.devs.append(dev_id)
         self.total_traffic = self.total_traffic + traffic


  ## transform the real VIPs to VIPs for algorithm
  def to_algo_vips(self):
    algo_vips = []
    kth_vip = 0

    for vip_id, traffic, devices in self.vips:
  
      weights = [0] * self.ndevs

      for (dev_id, w) in devices:
        dev_index = self.dev_dict[dev_id]
        weights[dev_index] = w
      sum_w = sum(weights)
      weights = map(lambda(x): x * 1.0/sum_w, weights)
      weights = zip(range(0, self.ndevs), weights)

      algo_vips.append((kth_vip, traffic / self.total_traffic, weights))
      kth_vip = kth_vip + 1

    return algo_vips

  def from_algo_dev_id(self, dev_id):
    return self.dev_dict[dev_id]

  ## transform the rules from the algorithm to real VIPs    
  def from_algo_rules(self, rules):

    def __transform_rule(rule): 
      (pattern, did, vid) = rule
      vip_id = self.vips[vid][0]
      dev_id = self.devs[did]
      return (pattern, dev_id, vip_id)

    return map(__transform_rule, rules)

