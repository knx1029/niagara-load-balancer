from dateutil import parser
from datetime import timedelta
import sys
import heapq
import random
import hashlib
import math
from operator import itemgetter

MINUTE_FRAME = 1
SECOND_FRAME = 30
#LINE_NUM = 428309
LINE_NUM = 6428309
#LINE_NUM = 5949897
USE_NPACKETS = False

def ip2num(ip):
    tokens = ip.split('.')
    num = 0
    for t in tokens:
        num = (num << 8) + int(t)
    return num

def num2ip(num):
    return "{0}.{1}.{2}.{3}".format(num >> 24,
                                    (num >> 16) & ((1 << 8) - 1),
                                    (num >> 8) & ((1 << 8) - 1),
                                    num & ((1 << 8) - 1))

def num2str(num):
    s = bin(num)[2:]
    return s

def ecmp(f, ntokens, nhops):
    def show(last_tminute, counts):
        if (last_tminute == None):
            return
        sumc = sum(counts)
        print last_tminute, ",", ntokens, ",",
        print ",".join(str(x * 1.0 / sumc) for x in counts)


    random.seed(29)
        
#    for line in f:
    last_tminute = None
    counts = None
    for i in range(LINE_NUM):
        line = f.readline()
        if (line == None or len(line) == 0):
            break
        tokens = line.split(',')
        dip = tokens[0]
        sip = tokens[1]
        t = parser.parse(tokens[2])
        npackets = tokens[3]
        if (len(tokens) > 4):
            nbytes = int(tokens[4]) + 34
        else:
            nbytes = 1
        dt = timedelta(minutes = t.minute % MINUTE_FRAME,
                       seconds = t.second % SECOND_FRAME,
                       microseconds = t.microsecond)
        tminute = t - dt

        if (tminute != last_tminute):
            show(last_tminute, counts)
            last_tminute = tminute
            counts = [0.0] * ntokens

        h0 = hashlib.new("sha")
        res = num2str(ip2num(sip)) + num2str(ip2num(dip))
        h0.update(res)
        hsh = h0.hexdigest()
        nn = int(hsh[-1], 16)
        idx = nn % nhops
        idx = idx % ntokens

        if (USE_NPACKETS):
            counts[idx] = counts[idx] + float(npackets)
        else:
            counts[idx] = counts[idx] + float(nbytes)
    show(last_tminute, counts)


def ng(f, rfin):

    def show(last_tminute, counts, ntokens):
        if (last_tminute == None):
            return
        sumc = sum(counts)
        print last_tminute, ",", ntokens, ",",
        print ",".join(str(x * 1.0 / sumc) for x in counts)

    def read_rules(rfin):
        filter_map = dict()
        while (True):
            tstr = rfin.readline()
            if (tstr == None) or (len(tstr) == 0):
                break
            t = parser.parse(tstr)
            filters = []
            ntokens = int(rfin.readline())
            m = int(rfin.readline())
            for i in range(m):
                tokens = rfin.readline().split(' ')
                filters.append((int(tokens[0]), int(tokens[1]), int(tokens[2])))
            filter_map[t] = (ntokens, filters)
        return filter_map


    filter_map = read_rules(rfin)
    last_tminute = None
    counts = None
    nrules = 0
    ntokens = 0
#    for line in f:
    for i in range(LINE_NUM):
        line = f.readline()

        if (line == None or len(line) == 0):
            break

        tokens = line.split(',')
        dip = tokens[0]
        sip = tokens[1]
        t = parser.parse(tokens[2])
        npackets = tokens[3]
        if (len(tokens) > 4):
            nbytes = int(tokens[4]) + 34
        else:
            nbytes = 1

        dt = timedelta(days = 1,
                       minutes = t.minute % MINUTE_FRAME,
                       seconds = t.second % SECOND_FRAME,
                       microseconds = t.microsecond)
        tminute = t - dt
        if (tminute != last_tminute):
            show(last_tminute, counts, nrules)

            filter_idx = tminute
            if (filter_idx not in filter_map):
                continue
            ntokens, filter = filter_map[filter_idx]
            last_tminute = tminute
            counts = [0.0] * ntokens
            nrules = len(filter)

        x = (ip2num(sip) << 16) + (ip2num(dip) & ((1 << 16) -1))
        idx = x % ntokens
        for (mask, v, id) in filter:
            if ((x & mask) == v):
                idx = id

        if (USE_NPACKETS):
            counts[idx] = counts[idx] + float(npackets)
        else:
            counts[idx] = counts[idx] + float(nbytes)


def microTE(f, ntokens, microte, nhops):
       
    def ToR(ip):
        x = ip2num(ip)
        return x >> 8 ## assume a /24 subnet

    def bin_pack(ToR_count):
        if (ToR_count == None):
            return
        L = [0.0] * ntokens
        cov = [1.0] * ntokens
        for i in range(ntokens, nhops):
            cov[i % ntokens] = cov[i % ntokens] + 1
        for x in sorted(ToR_count.values(), reverse = True):
            best_i = 0
            for i in range(1, ntokens):
                if (L[i] / cov[i] < L[best_i] / cov[best_i]):
                    best_i = i
            L[best_i] = L[best_i] + x
        print ",".join(str(l / sum(L)) for l in L)

    def show(last_tminute, ToR_set):
        if (last_tminute == None):
            return
        srcToR_set = set()
        for (x, _) in ToR_set:
            srcToR_set.add(x)
        print last_tminute, ",", len(ToR_set), ",",


    def input(tminute, sip_count):
        if (last_tminute != None):
            print ""
            sumc = sum(sip_count.values())
            print ";".join("{0},{1}".format(str(x), str(v/sumc)) for (x, v) in sip_count.items())
 
    last_tminute = None
    ToR_set = None
    ToR_count = None
    sip_count = None
    last_ToR_set = None
#    for line in f:
    for i in range(LINE_NUM):
        line = f.readline()
        if (line == None or len(line) == 0):
            break
        tokens = line.split(',')
        dip = tokens[0]
        sip = tokens[1]
        t = parser.parse(tokens[2])
        npackets = tokens[3]
        if (len(tokens) > 4):
            nbytes = int(tokens[4]) + 34
        else:
            nbytes = 1
        dt = timedelta(minutes = t.minute % MINUTE_FRAME,
                       seconds = t.second % SECOND_FRAME,
                       microseconds = t.microsecond)
        tminute = t - dt

        if (tminute != last_tminute):
            show(last_tminute, ToR_set)
            if microte != "input":
                bin_pack(ToR_count)
            else:
                input(last_tminute, sip_count)
            last_ToR_set = ToR_set
            last_tminute = tminute
            ToR_set = set()
            ToR_count = dict()
            sip_count = dict()

        if (microte != "opt"):
            pair = (ToR(sip), ToR(dip))
        else:
            pair = (sip, dip)
        ToR_set.add(pair)
        if (pair not in ToR_count):
            ToR_count[pair] = 0.0
        if (USE_NPACKETS):
            ToR_count[pair] = ToR_count[pair] + npackets
        else:
            ToR_count[pair] = ToR_count[pair] + nbytes
        nsip = (ip2num(sip) << 16) + (ip2num(dip) & ((1 << 16) - 1))
        if (nsip not in sip_count):
            sip_count[nsip] = 0.0
        if (USE_NPACKETS):
            sip_count[nsip] = sip_count[nsip] + npackets
        else:
            sip_count[nsip] = sip_count[nsip] + nbytes
        
    show(last_tminute, ToR_set)
    if microte != "input":
        bin_pack(ToR_count)
    else:
        input(last_tminute, sip_count)


def local_flow(f, ntokens):

    def lf(last_tminute, dst_set):
        if (last_tminute == None):
            return
        nrules = 0
        links = [0.0] * ntokens
        for dst, src_set in dst_set.items():
            flows = sorted(binpack(src_set, ntokens))
            links = sorted(links, reverse = True)
            for i in range(ntokens):
                links[i] = links[i] + flows[i][0]
                nrules = nrules + flows[i][1]
            summ = sum(links)
        print last_tminute, ",", nrules, ",",
        print ",".join(str(l / summ) for l in links)
            

    def binpack(src_set, ntokens):
        heaped_flows = []
        bincap = 0.0
        for (src, size) in src_set.items():
#            size.sort(reverse = True)
            size.sort()
            summ = sum(size)
            bincap = bincap + summ
            heaped_flows.append((summ, src))
        heapq.heapify(heaped_flows)
        
        bincap = math.ceil(bincap / ntokens)
        bincap = bincap * 1.0
        binBd = [bincap] * ntokens
        nrules = [0] * ntokens
        while (len(heaped_flows) > 0):
            best_i = 0
            for i in range(ntokens):
                if (binBd[i] > binBd[best_i]):
                    best_i = i
            size, src = heapq.heappop(heaped_flows)
            if (size <= binBd[best_i] + 1e-6):
                binBd[best_i] = binBd[best_i] - size
                nrules[best_i] = nrules[best_i] + 1
            else:
                nsizes = src_set[src]

                if (nsizes[0] > binBd[best_i] + 1e-6):
                    delta = nsizes[0] - binBd[best_i]
                    for i in range(ntokens):
                        binBd[i] = binBd[i] + delta
                    bincap = bincap + delta
                    heapq.heappush(heaped_flows, (size, src))
                    continue

                filled = 0.0
                new_nsizes = []
                for j in range(len(nsizes)):
                    nsize = nsizes[j]
                    if (nsize <= binBd[best_i] + 1e-6):
                        binBd[best_i] = binBd[best_i] - nsize
                        filled = filled + nsize
                    else:
                        new_nsizes.append(nsize)
                src_set[src] = new_nsizes
                heapq.heappush(heaped_flows, (size - filled, src))
                nrules[best_i] = nrules[best_i] + 1

        flows = []
        for i in range(ntokens):
            flows.append((bincap - binBd[i], nrules[i]))
        return flows

    last_tminute = None
    dst_set = None
#    for line in f:
    for i in range(LINE_NUM):
        line = f.readline()
        if (line == None or len(line) == 0):
            break
        tokens = line.split(',')
        dip = tokens[0]
        sip = tokens[1]
        t = parser.parse(tokens[2])
        npackets = tokens[3]
        if (len(tokens) > 4):
            nbytes = int(tokens[4]) + 34
        else:
            nbytes = 1
        dt = timedelta(minutes = t.minute % MINUTE_FRAME,
                       seconds = t.second % SECOND_FRAME,
                       microseconds = t.microsecond)
        tminute = t - dt

        if (tminute != last_tminute):
            lf(last_tminute, dst_set)
            last_tminute = tminute
            dst_set = dict()

        if (dip not in dst_set):
            dst_set[dip] = dict()
        src_set = dst_set[dip]
        if (sip not in src_set):
            src_set[sip] = []
        if (USE_NPACKETS):
            src_set[sip].append(npackets)
        else:
            src_set[sip].append(nbytes)
        
    lf(last_tminute, dst_set)


def countDstToR(f):
    def ToR(ip):
        x = ip2num(ip)
        return x >> 8 ## assume a /24 subnet

    dstToR = dict()
    for i in range(LINE_NUM):
        line = f.readline()
        if (line == None or len(line) == 0):
            break
        tokens = line.split(',')
        dip = tokens[0]
        tor = ToR(dip)
        if (len(tokens) > 4):
            nbytes = int(tokens[4]) + 34
        else:
            nbytes = 1
        if (tor not in dstToR):
            dstToR[tor] = 0.0
        dstToR[tor] = dstToR[tor] + nbytes

    print len(dstToR)
    data = ((n, d) for (d, n) in dstToR.items())
    print "\n".join("{0}, {1}".format(num2ip(d << 8), str(n)) for (n, d) in sorted(data, reverse = True))
    

mode = sys.argv[1]
if (mode == "ng"):
    nfin = open(sys.argv[2], "r")
    rfin = open(sys.argv[3], "r")
    ng(nfin, rfin)
    nfin.close()
    rfin.close()
elif (mode == "ecmp"):
    nfin = open(sys.argv[2], "r")
    ecmp(nfin, 4, 6)
    nfin.close()
elif (mode == "microte" or mode == "opt"):
    nfin = open(sys.argv[2], "r")
    microTE(nfin, 4, mode, 6)
    nfin.close()
elif (mode == "input"):
    nfin = open(sys.argv[2], "r")
    microTE(nfin, 4, mode, 4)
    nfin.close()
elif (mode == "lf"):
    nfin = open(sys.argv[2], "r")
    local_flow(nfin, 4)
    nfin.close()
elif (mode == "count"):
    nfin = open(sys.argv[2], "r")
    countDstToR(nfin)
    nfin.close()


