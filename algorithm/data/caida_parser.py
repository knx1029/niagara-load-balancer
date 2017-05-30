#import dpkt, socket, glob, pcap, os
import heapq
import sys

def ip2num(ip):
    tokens = ip.split('.')
    num = 0
    for i in range(4):
        t = tokens[i]
        num = (num << 8) + int(t)
    return num

def ip2subnet16(ip):
    tokens = ip.split('.')
    num = 0
    for i in range(2):
        t = tokens[i]
        num = (num << 8) + int(t)
    return num

def strip_port(ip_port):
    tokens = ip_port.split('.')
    ip = ".".join(tokens[:4])
    return ip

def read(filename):
    fin = open(filename, "r")
    count_vip = dict()
    for line in fin:
#    for i in range(100000):
#        line = fin.readline()
        if (" IP " in line):
            tokens = line.split(' ')
            if (len(tokens) < 5):
                continue
#            vip = tokens[4].replace(":", "")
            vip = tokens[5].replace(":", "")
            vip = ip2subnet16(vip)
            if (vip not in count_vip):
                count_vip[vip] = 1
            else:
                count_vip[vip] = count_vip[vip] + 1
    fin.close()

    counts = [(v, k) for (k, v) in count_vip.items()]
    n = 200
    top_n = heapq.nlargest(n, counts)
    return top_n
#    sp_vip = set(map(lambda(x):x[1], top_n))

#    return sp_vip


def filter(filename, sp_vip):
    fin = open(filename, "r")
    count_vip = dict()
    for line in fin:
#    for i in range(100000):
#        line = fin.readline()
        if (" IP " in line):
            tokens = line.split(' ')
            if (len(tokens) < 5):
                continue
#            t = tokens[0]
#            sip = tokens[2]
#            vip = tokens[4].replace(":", "")
            t = tokens[1]
            sip = tokens[3]
            sip = strip_port(sip)
            vip = tokens[5].replace(":", "")
            vip = strip_port(vip)
            subnet = ip2subnet16(vip)
#            if (vip in sp_vip):
            if (subnet in sp_vip):
                l = 0
                for i in range(len(tokens)):
                    if (tokens[i] == "length"):
                        try:
                            l = int(tokens[i + 1])
                        except Exception:
                            pass
                        break
                print vip, ",", sip, ",", t, ",", 1, ",", l
#                print line,

    fin.close()    



#filename = "/Users/nanxikang/Documents/Research/github/policy_trans/CAIDA/equinix-sanjose.dirA.20091217-125904.UTC.anon.pcap"
#filename = "../../data/univ1_all"
filename = sys.argv[1]
#sp_vip = read(filename)
#print "\n".join("{0}, {1}.{2}".format(x[0], x[1] >> 8, x[1] & 255) for x in sp_vip)
#sp_vip = set([ip2subnet16("41.177.0.0")])
sp_vip = set([ip2subnet16("244.3.0.0")])
filter(filename, sp_vip)
