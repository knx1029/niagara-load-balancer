import ast
import os
import sys
import subprocess
import datetime
from argparse import ArgumentParser

sys.path.append("..")

from utils import *
from info import Rule
from ecmp_router import *

BATCH = "../topo/config.sh"


class GroupMode:
    UNDEFINED = 0
    BY_GW = 1
    BY_DIP = 2

## parse the state of the controller
def parse_info(s):
    value = ast.literal_eval(s)
    data = value[0][REST_NW][0]

    active_rules = data[REST_RULES]
    real_rules = map(Rule.parse_rule, active_rules)

    flow2ecmp = ast.literal_eval(data[REST_FG2EG])

    x = {int(x[0]): x[1][0] for x in data[REST_ECMP_GROUP].items()}
    ecmp_group = {x[0]: ast.literal_eval(x[1]) for x in x.items()}

    rule_stats = map(Stats.parse_stats, data[REST_OF_TABLE])

    return real_rules, flow2ecmp, ecmp_group, rule_stats

def parse_states(s):
    value = ast.literal_eval(s)
    data = value[0][REST_NW][0]
    ecmp_group = data[REST_ECMP_GROUP]
    flow_group = data[REST_FLOW_GROUP]
    flow2ecmp = ast.literal_eval(data[REST_FG2EG])
    return ecmp_group, flow_group, flow2ecmp


## parse the table of the switch
## deprecated
def parse_tbl(f):
    rule_stats = []
    for line in f:
        if ("cookie" in line):
            tokens = line.rsplit(', ')
            for token in tokens:
                xs = token.rsplit('=')
                if ('cookie' in xs[0]):
                    cookie = int(xs[1], 0)
                elif (xs[0] == 'duration'):
                    duration = xs[1]
                elif (xs[0] == 'n_packets'):
                    npackets = int(xs[1], 0)
                elif (xs[0] == 'n_bytes'):
                    nbytes = int(xs[1], 0)

            rule_stats.append(Stats(cookie, duration, npackets, nbytes))
    return rule_stats


## match the controller state with the table stats            
def match_rule_stats(rules, rule_stats, vlan_id = 0):
    matched = []
    
    for rule in rules:
        for stats in rule_stats:            
            rest_id, success = EcmpRouter.cookie_to_id(REST_RULEID,
                                                       stats.m_cookie)
            if (success and rest_id == rule.m_rule_id):
                matched.append((rule, stats))
                break

    return matched

## select the rules and aggregate by gateway or dip
def select_and_group(matched,
                     flow2ecmp,
                     ecmp_group, 
                     fg_id,
                     option = GroupMode.BY_GW):
    summary = {}

    if (fg_id not in flow2ecmp):
        raise Error("fg_id=%d does not have an ecmp group" % fg_id)
    ecmp_id = flow2ecmp[fg_id]
    if (ecmp_id not in ecmp_group):
        raise Error("unknwon ecmp_id=%d" % ecmp_id)
    ecmp = ecmp_group[ecmp_id]

    res = [m for m in matched if m[0].m_fg_id == fg_id]

    for r in res:
        rule, rule_stats = r
        if (option == GroupMode.BY_GW):
            key = rule.m_action.m_gateway
        elif (option == GroupMode.BY_DIP):
            key = rule.m_action.m_dip
        else:
            continue

        if (key == 0):
#            print ("warning, unsupported rule for grouping.\n%s %s"
#                   % (str(rule), str(rule_stats)))
            continue
        if (key not in ecmp):
#            print ("warning, unrecognized rule to ecmp group %d.\n(%s,%s)"
#                   % (ecmp_id, str(rule), str(rule_stats)))
            continue

        if (key in summary):
            s = summary[key]
            s.m_npackets += rule_stats.m_npackets
            s.m_nbytes += rule_stats.m_nbytes
        else:
            s = Stats(0, 0, rule_stats.m_npackets, rule_stats.m_nbytes)
            summary[key] = s

    return summary

## retrieve data and filter the rules
def work(input_file, output_file, fg_id, mode, create_new = True):
    f = open(input_file, 'r')
    for line in f:
        if (REST_NW in line):
            rules, flow2ecmp, ecmp_group, rule_stats = parse_info(line)
            break
    f.close()

    matched = match_rule_stats(rules, rule_stats)

    if (create_new):
        f = open(output_file, 'w')
        f.write("timestamp,ip,npackets,nbytes\n")
    else:
        f = open(output_file, 'a')
    summary = select_and_group(matched,
                               flow2ecmp,
                               ecmp_group,
                               fg_id,
                               mode)

    now = datetime.datetime.now()
    for ip, stats in summary.items():
        f.write("%s,%s,%d,%d\n" % (now,
                                   ip,
                                   stats.m_npackets,
                                   stats.m_nbytes))
    f.close()
    

def display_states(input_file, ecmp_file, flow_file):
    f = open(input_file, 'r')
    for line in f:
        if (REST_NW in line):
            ecmp_group, flow_group, flow2ecmp = parse_states(line)
            break
    f.close()

    f = open(ecmp_file, 'w')
    f.write("------ EcmpGroup -----\n")
    for x in sorted(ecmp_group.keys()):
        y = ecmp_group[x]
        f.write(">>>>  ecmp_id : %s  <<<<\n" % x)

        f.write("members (NAT_IP, weight, GATEWAY)\n")
        members = ast.literal_eval(y[0])
        if (not members):
            f.write("\n")
        else:
            f.write("\n".join("{0}, {1}, {2}".format(a[0], a[1][0], a[1][1])
                              for a in members.items()))
            f.write("\n")

        f.write("rules (priority, pattern, NAT_IP)\n")
        rules = y[1]
        if (not rules):
            f.write("\n")
        else:
            f.write("\n".join(k for k in reversed(rules)))
            f.write("\n")
        f.write(">>>>>><<<<<<\n\n")

    f.close()


    f = open(flow_file, 'w')
    f.write("------ FlowGroup -----\n")
    for x in sorted(flow_group.keys()):
        y = flow_group[x]

        tokens = y.rsplit(', ')
        a = int(tokens[0].rsplit(':')[1])
        b = flow2ecmp[a]
        f.write(">>>>  flow group %d  : ecmp group %d  <<<<\n" % (a, b))
        fields = tokens[2].rsplit('+')
        f.write("\n".join(fields))
        f.write("\n")
        f.write(">>>>>><<<<<<\n\n")

    f.close()


def parse_args(s):
  parser = ArgumentParser(description = 'retrieve stats for rules')

  parser.add_argument('-mode', action = 'store',
                    choices = ['gw', 'dip'],
                    help = 'modes: gw, dip');
  parser.add_argument('-fg_id', action = 'store', type = int)
  parser.add_argument('-sw', action = 'store', default = 's1')
  parser.add_argument('-batch', action = 'store', default = None)
  parser.add_argument('-info', action = 'store', default = "./tbd.info")
  parser.add_argument('-summary', action = 'store', default = "./tbd.summary")
  parser.add_argument('-ecmp', action = 'store', default = "./tbd.ecmp")
  parser.add_argument('-flow', action = 'store', default = "./tbd.flow")
  parser.add_argument('-create_new', action = 'store_true')

  args = parser.parse_args(s)
  return args


## main starts here

args = parse_args(sys.argv[1:])
if (args.batch != None):
    BATCH = args.batch

f = open(args.info, 'w')
subprocess.call(["bash", BATCH, args.sw, "get"], stdout = f)
f.close()

mode = GroupMode.UNDEFINED
if args.mode == 'gw':
    mode = GroupMode.BY_GW
elif args.mode == 'dip':
    mode = GroupMode.BY_DIP

display_states(args.info, args.ecmp, args.flow)

if mode != GroupMode.UNDEFINED:
    work(args.info, args.summary, args.fg_id, mode, args.create_new)
