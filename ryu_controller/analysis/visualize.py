import os
import sys
import subprocess

plot_exec = "plot.py"
infos = ["Vip 192.168.6.6:12345", "Vip 192.168.7.7:54321"]
args = ["npackets", "nbytes"]

ps = []
for arg in args:
    p = subprocess.Popen(["python", plot_exec, infos[0], arg])
    ps.append(p)

line = sys.stdin.readline()
for p in ps:
    p.kill()
    
