from dateutil import parser
from datetime import timedelta
import sys
import heapq
import random
import hashlib
import math

def ip2num(ip):
    tokens = ip.split('.')
    num = 0
    for t in tokens:
        num = (num << 8) + int(t)
    return num

def num2str(num):
    s = ""
    for i in range(4):
        s = s + chr(i & ((1 << 8) - 1))
        i = (i >> 8)
    return s

def count(f, src_count, dst_count):
    for line in f:
        tokens = line.split(',')
        if (tokens[0] == tokens[1]):
            continue
        t0 = tokens[0]
        t1 = tokens[1]
        npackets = tokens[11]
        nbytes = tokens[12]
        sip = tokens[3]
        dip = tokens[4]
        if (sip in src_count):
            src_count[sip].append((dip, t0, t1, npackets, nbytes))
        else:
            src_count[sip] = [(dip, t0, t1, npackets, nbytes)]

        if (dip in dst_count):
            dst_count[dip].append((sip, t0, t1, npackets, nbytes))
        else:
            dst_count[dip] = [(sip, t0, t1, npackets, nbytes)]


def count_all(inputs):
    src_count = dict()
    dst_count = dict()

    for input in inputs:
        f = open(input, "r")
        count(f, src_count, dst_count)
        f.close()

    top_src = [(len(v), k, v) for (k, v) in src_count.items()]
    top_dst = [(len(v), k, v) for (k, v) in dst_count.items()]


#    print len(top_src), len(top_dst)

    ## src is 255, dst is 37 (>100)
    n_top_src = sorted(top_src, reverse = True)
    n_top_dst = sorted(top_dst, reverse = True)

    return n_top_src, n_top_dst


def count_dst(input):
    dst_count = dict()

    f = open(input, "r")
    for line in f:
        tokens = line.split(',')
        dip = tokens[0]
        sip = tokens[1]
        t = tokens[2]
        endt = tokens[3]
        npackets = tokens[4]
        nbytes = 0

        if (dip in dst_count):
            dst_count[dip].append((sip, t, npackets, nbytes, endt))
        else:
            dst_count[dip] = [(sip, t, npackets, nbytes, endt)]
    f.close()

    top_dst = [(len(v), k, v) for (k, v) in dst_count.items()]
    n_top_dst = sorted(top_dst, reverse = True)
    return n_top_dst


def check_valid(v, ntokens):
    appear = set()
    for vv, tstr, npackets, nbytes in v:
        nn = ip2num(vv)
        appear.add(nn % ntokens)
    return (len(appear) == ntokens)


## mode = "input" or "ng" or "ecmp"
def balance(n_top, n, mode):
    if (mode == "input"):
        nbits = 7
        print nbits
    else:
        nbits = 1
    ntokens = (1 << nbits)
    random.seed(29)
    count = 0
    for l, k, v in n_top:
        balance_t = dict()
        count = count + 1
        if (count > n):
            break
        for vv, tstr, npackets, nbytes in v:
            t = parser.parse(tstr)
            if (mode == "input"):
                dt = timedelta(minutes = t.minute % 30,
                               seconds = t.second)
            else:
                dt = timedelta(minutes = t.minute % 2,
                               seconds = t.second)
            tminute = t - dt

            nn = ip2num(vv)
            idx = 0
            if (mode == "ecmp"):
                h0 = hashlib.new("sha")
                h0.update(bin(nn)[2:])
                nn = int(h0.hexdigest()[-1], 16)
                idx = nn % ntokens
            elif (mode == "ng"):
                if ((nn & 4095) == 84):
                    idx = 0
                elif ((nn & 511) == 97):
                    idx = 1
                elif ((nn & 3) == 0):
                    idx = 1
                else:
                    idx = 0
            elif (mode == "input"):
                idx = nn % ntokens
                

            if (tminute not in balance_t):
                balance_t[tminute] = [0.0] * ntokens
#            balance_t[tminute][idx] = balance_t[tminute][idx] + 1
            balance_t[tminute][idx] = balance_t[tminute][idx] + float(npackets)

        for tminute in sorted(balance_t):
            cc = balance_t[tminute]
            summ = sum(cc)
            if (mode != "input"):
                print tminute, ",",
                print " , ".join(str(x / summ) for x in cc)
            else:
                print "\n".join(str(x / summ) for x in cc)

def eval(n_top, n, nfin):
    def read_rules(nfin):
        filters = []
        m = int(nfin.readline())
        for i in range(m):
            tokens = nfin.readline().split(' ')
            filters.append((int(tokens[0]), int(tokens[1]), int(tokens[2])))
        return filters

    ## starts here
    count = 0
    label = None
    for l, k, v in n_top:
        if (label == None):
            label = nfin.readline()

        if (k not in label):
            continue
        else:
            label = None

        ntokens = int(nfin.readline())
        balance_t = dict()
        sum_n = [0.0] * ntokens
        sum_e = [0.0] * ntokens

        filter = read_rules(nfin)
        for vv, tstr, npackets, nbytes in v:
            nn = ip2num(vv)
            idx_e = 0
            idx_n = 0

            h0 = hashlib.new("sha")
            
#                h0.update(hex(nn)[2:])
#            h0.update(bin(nn)[2:])
            idx_e = int(h0.hexdigest()[-1], 16) % ntokens

            for (mask, v, id) in filter:
                if ((nn & mask) == v):
                    idx_n = id

            sum_n[idx_n] = sum_n[idx_n] + float(npackets)
            sum_e[idx_e] = sum_e[idx_e] + float(npackets)

        print k, ",",
        sumn = sum(sum_n)
        imb_n = 0.0
        for i in range(ntokens):
            x = sum_n[i] / sumn
#            print x, ",",
            imb_n = imb_n + math.fabs(x - 1.0 / ntokens)
        print imb_n / 2, ",",

        sume = sum(sum_e)
        imb_e = 0.0
        for i in range(ntokens):
            x = sum_e[i] / sume
 #           print x, ",",
            imb_e = imb_e + math.fabs(x - 1.0 /ntokens)
        print imb_e / 2

        count = count + 1
        if (count >= n):
            break


mode = "update"# "single"

if (mode == "input"):
    n_top_src, n_top_dst = count_all([sys.argv[1]])
    n = 20
    for i in range(n):
        l, k, v = n_top_dst[i]
        if (k != "128.112.255.98"):
            continue
        for vv in v:
            print k, ",", 
            print " , ".join(vvv for vvv in vv)
else:
    n_top_dst = count_dst(sys.argv[1])
    if (mode == "single"):
        mode = "ecmp" # "ng" # "ecmp" # "input"
        balance(n_top_dst, 1, mode)
    elif (mode == "all"):
        nfin = open(sys.argv[2], "r")
        eval(n_top_dst, n, nfin)
        nfin.close()
    elif (mode == "update"):
        for l, k, v in n_top_dst[:1]:
            print k, l
            for vv in v:
                print k, ",", 
                print " , ".join(str(vvv) for vvv in vv)
