## import old svip
if False:
    import os, sys, inspect
    paths = ["../"]
    for relative_path in paths:
        cmd_subfolder = os.path.realpath(os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], relative_path)))
        if cmd_subfolder not in sys.path:
            print "import directory: ", cmd_subfolder
            sys.path.insert(0, cmd_subfolder)
    from single_vip import *
#######

from svip_solver import *
from mvip_solver import *
import math
import random
import sys

def gen(ntests, nweights):
    ws_list = []
    random.seed(29)
    for i in range(0, ntests):
        ns = [random.random() for j in range(0, nweights)]
        s = sum(ns)
        ws = zip(range(0, nweights), [n / s for n in ns])
        ws_list.append(ws)
    return ws_list

def show_svip(rules, values):
    print values
    print len(rules)
    print "\n".join(str(r) for r in rules)

def show_rule_vector(rules):
    print len(rules)
    for r in rules:
        p = r[0]
        x = 0
        w = 0
        for c in p:
            if (c == '0'):
                x = x + 1
                w = w << 1
            elif (c == '1'):
                x = x + 1
                w = (w << 1) + 1
        print (1 << x) - 1, w, r[1]

def show_mvip(rules, values):
    for vip_idx, vip_rules in rules:
        if vip_idx == None:
            print "Default Rules"
            show_svip(vip_rules, None)
        else:
            print "Rules for VIP", vip_idx
            if (values == None):
                vip_values = None
            else:
                vip_values = values[vip_idx]
            show_svip(vip_rules, vip_values)


## return the best feasible eps (eval should be TrafficExactEval type)
def min_svip_eps(solver, ws, eval, drules):
    eps_lower = 0.0
    eps_upper = 1.0
    best_eps = -1.0
    best_rules = None
    best_values = None
    while (math.fabs(eps_upper - eps_lower) > 1e-4):
        eps = (eps_lower + eps_upper) / 2

        solver.set_input(ws, eval, drules, eps)
        try:
            result = solver.solve()
        except Exception as e:
            eps_lower = eps
            continue

        if (not result):
            eps_lower = eps
            continue

        eps_upper = eps
        best_rules, best_values = solver.get_output()
        best_eps = eps

        if (not SVipUTest.validate(best_rules,
                                   best_values,
                                   ws,
                                   eval,
                                   eps)):
            print eps
            print "weight", eval.weight(best_rules[-1][0])
            print "show_svip"
            show_svip(best_rules, best_values)
            break

    return best_eps, best_rules, best_values




def test_svip(ntests, nweights, drules, fin):
    eps = 1e-2
#    eval = TrafficVectorEval(2, [0.15, 0.35, 0.25, 0.25])
 
#    eval = TrafficEval()
    solver = SVipSolver()

#    ws_list = gen(ntests, nweights)
#    ws_list = [((0, 0.5), (1, 0.5))]
#    ws_list = [((0, 1.0/3), (1, 1.0/6), (2, 0.5))]    
    ws_list = [((0, 0.5), (1, 0.5))]
    cnt1, cnt2 = 0, 0
    res1, res2 = 0, 0
    t1, t2 = 0.0, 0.0
#    for ws in ws_list:
    mode = "Mpath2"
#    mode = "LBer"
    for i in range(ntests):
        if (mode == "LBer"):
            label = "...."
            nweights = 2
#            label = fin.readline()
#            nweights = int(fin.readline())
            ws = zip(range(nweights), [1.0/nweights] * nweights)
            vector_len = int(fin.readline())
            vector = [0] * (1<<vector_len)
            for i in range(1 << vector_len):
                vector[i] = float(fin.readline())
            eval = TrafficVectorEval(vector_len, vector)
        elif (mode == "Mpath1"):
            line = fin.readline()
            if (line == None or len(line) == 0):
                break
            nweights = 4
            ws = zip(range(nweights), [1.0 / nweights] * nweights)
            tokens = line.split(' , ')
            label = tokens[0]
            vector_len = int(math.ceil(math.log(len(tokens) - 2) / math.log(2) - 1e-9))
            vector = [0.0] * (1 << vector_len)
            for i in range(1 << vector_len):
                vector[i] = float(tokens[i + 1])
            eval = TrafficVectorEval(vector_len, vector)
        elif (mode == "Mpath2"):
            line = fin.readline()
            if (line == None or len(line) == 0):
                break
            nweights = 4
#            ws = zip(range(nweights), [1.0 / nweights] * nweights)
            ws = zip(range(nweights), [1.0 / 3, 1.0 / 3, 1.0 / 6, 1.0 / 6])
            tokens = line.split(' , ')
            label = tokens[0]
            line = fin.readline()
            tokens = line.split(';')
            def f(x):
                y = x.split(',')
                return (int(y[0]), float(y[1]))
            vs = map(f, tokens)
            eval = TrafficExactEval(vs)
#            if (label != "2015-05-23 13:05:00"):
#                continue

        if (mode == "Mpath2"):
            eps, rules, values = min_svip_eps(solver, ws, eval, drules)
#            print eps
        else:
            solver.set_input(ws, eval, drules, eps)
            start = time.time()
            result = solver.solve()
            t1 = t1 + time.time() - start
            if (not result):
                print "Exception occured for", ws
                continue
            rules, values = solver.get_output()

        res1 = len(rules)
        if (not SVipUTest.validate(rules,
                                   values,
                                   ws,
                                   eval,
                                   eps)):
            print "FALSE!  11111"
            print "weight", ws
            print "show_svip"
            show_svip(rules, values)
            break

#        show_svip(rules, values)

        print label
        print nweights
        show_rule_vector(rules)

        if False:
            algo_mode = HEU
            ecmp_info = None
            start = time.time()
            _, _, rules, vlist = find_single_vip_w_default(ws,
                                                           eps,
                                                           algo_mode,
                                                           ecmp_info)
            values = [ (x[0], x[1]) for x in values]
            t2 = t2 + time.time() - start

            res2 = len(rules)
            if (not SVipUTest.validate(rules,
                                       values,
                                       ws,
                                       eval,
                                       eps)):
                print "FALSE!  22222"
                print ws
                print vlist
                show_svip(rules, values)
                break
            else:
                res2 = 100000

        if (res1 <= res2):
            cnt1 = cnt1 + 1
        if (res2 <= res1):
            cnt2 = cnt2 + 1
 
#    print "cnt1 {0}, cnt2 {1}".format(cnt1,
#                                      cnt2)
#    print "time1 {0}, time2 {1}".format(t1, t2)


def test_mpath(fin):

    def gen_default_rules(nweights):
        nbits = int(math.floor(math.log(nweights)/math.log(2) + 1e-9))
        prefix = "*" * (BITS - nbits)
        drules = []
        for i in range(1 << nbits):
            k = i
            pattern = ""
            for j in range(nbits):
                pattern = str(k & 1) + pattern
                k = (k >> 1)
            pattern = prefix + pattern
            drules.append((pattern, i))
        return drules
            
    eps = 1e-3
    eval = TrafficEval()
    solver = SVipSolver()

    while (True):
       label = fin.readline()
       if (label == None) or (len(label) == 0):
           break

       label = label.replace("\n", "")
       nweights = int(fin.readline())
       ntests = int(fin.readline())
       no_shared_rules = 0
       shared_rules = 0
       default_nrules = 0
       for i in range(ntests):
           line = fin.readline()
           tokens = line.split(' ')
           ws = zip(range(nweights), 
                    map(lambda(x): float(x), tokens))

           drules = None

           solver.set_input(ws, eval, drules, eps)
           result = solver.solve()
           if (not result):
               print "Exception occured for", ws
               continue
           rules, values = solver.get_output()
           no_shared_rules = no_shared_rules + len(rules)

           drules = gen_default_rules(nweights)
           solver.set_input(ws, eval, drules, eps)
           result = solver.solve()
           if (not result):
               print "Exception occured for", ws
               continue
           rules, values = solver.get_output()
           shared_rules = shared_rules + len(rules) - len(drules)
           default_nrules = len(drules)

       print label, ",", no_shared_rules, ",", shared_rules + default_nrules
           


def test_mvip(nvips, nweights, C, fin = None):
    eps = 1e-2

    eval = TrafficEval()
    solver = MVipSolver(eps)
    traffic = gen(1, nvips)
    ws_list = gen(nvips, nweights)
    vips = map(lambda(x): (x[0][0], x[1], eval, x[0][1]), zip(traffic[0], ws_list))
    drules = [("*" * 30 + "00", 0),
              ("*" * 30 + "01", 1),
              ("*" * 30 + "10", 2),
              ("*" * 30 + "11", 3)]
    drules = None            

    solver.set_input(vips, C, drules)
    start = time.time()
    result = solver.solve()
    end = time.time()
    if (not result):
        print "Exception occured for"
        print '\n'.join('{0},{1},{2}'.format(v[0],v[3],v[1]) for v in vips)

    rules, values = solver.get_output()
    res1 = len(rules)

#    print "\n".join(str(r) for r in rules)
    for r in rules:
        print r
    print "--------"

    if (not MVipUTest.validate(rules,
                               values,
                               vips,
                               C,
                               eps)):
        print "FALSE!  11111"
        print '\n'.join('{0},{1},{2}'.format(v[0],v[3],v[1]) for v in vips)
        show_mvip(rules, values)
    print "stairtstep", end - start

    ## try the new way
    rule_map = {}
    svip_solver = SVipSolver()
    total = 0.0
    for (vip_idx, weights, traffic_eval, popularity) in vips:
        svip_solver.set_input(weights, traffic_eval, drules, eps)
        start = time.time()
        svip_solver.solve()
        end = time.time()
        total += end - start

        vip_rules, _ = svip_solver.get_output()
        rule_map[vip_idx] = vip_rules
 
    smvip_solver = SMVipSolver()
    vip_popularity = {x[0]: x[3] for x in vips}
    smvip_solver.set_input(vip_popularity, C, rule_map, drules)
    print "prepare", total

    start = time.time()
    smvip_solver.solve()
    end = time.time()
    rules_ = smvip_solver.get_output()
    if (not MVipUTest.validate(rules,
                               None,
                               vips,
                               C,
                               eps)):
        print "FALSE!  11111"
        print '\n'.join('{0},{1},{2}'.format(v[0],v[3],v[1]) for v in vips)
        show_mvip(rules, values)
 
    print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>"
    print "time", end - start

ntests = 4
nweights = 16
C = 10

drules = [("*" * 30 + "00", 0),
          ("*" * 30 + "01", 1),
          ("*" * 30 + "10", 2),
          ("*" * 30 + "11", 3)]
drules = None
#mode = "imb" 
mode =""
if (mode == "imb"):
    fin = open(sys.argv[1], "r")
    ntests = 65 * 3 + 10
    test_svip(ntests, nweights, drules, fin)
    fin.close()
elif (mode == "asym_topo"):
    fin = open(sys.argv[1], "r")
    test_mpath(fin)
    fin.close()

test_mvip(ntests, nweights, [C], drules)
