import sys
import subprocess
from datetime import timedelta
import numpy as np
import pandas as pd
from bokeh.plotting import *
from bokeh.session import Session

SCP = False
sleep_gap = 20

## configurations
index = 'timestamp'
field = 'npackets'

ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3", "192.168.1.4"]
style = ["red", "blue", "green", "orange"]
amortized_sec = 1000000

local_file_template = "%s.summary"
if SCP:
    remote_input = 'tbd.summary'
    remote_file_template = "mininet@192.168.56.101:/home/niagara/ecmp_router/analysis/%s" 
else:
    remote_input = 'tbd.summary'
    remote_file_template="http://www.cs.princeton.edu/~nkang/backdoor/%s"

delta = timedelta(minutes = 15)


## work starts from here    

if (len(sys.argv) > 1):
    description = sys.argv[1]

if (len(sys.argv) > 2):
    field = sys.argv[2]

if (len(sys.argv) > 3):
    remote_input = sys.argv[3]

remote_input = remote_file_template % remote_input
local_input = local_file_template % field

## read from input files
def read_remote_file():
    if SCP:
        subprocess.call(["scp", remote_input, local_input])
    else:
        subprocess.call(["wget", "-O", local_input, remote_input])
    X = pd.read_csv(local_input, parse_dates=[index])
    return X

## compute the load difference and divided by time
def calc_diff(x):
    x['diff'] = x[field] - x[field].shift()
    x['timediff'] = x[index] - x[index].shift()
    x['secdiff'] = x['timediff'] / np.timedelta64(amortized_sec)
    x['avg_recv'] = x['diff'] # / x['secdiff']
    y = x[x['diff'] >= 0]
    return y

def re_read_file():
    X = read_remote_file()
    xs = []
    end_time = X[index].max()
    beg_time = end_time - delta
    if beg_time < X[index].min():
        beg_time = X[index].min()
    for ip in ips:
        f = X[X.ip == ip]
        ## create a zero line
        if (len(f) == 0):
            x = pd.DataFrame(
                [[beg_time, 0, 0],
                 [end_time, 0, 0]],
                index = [beg_time, end_time],
                columns = [index, field, 'avg_recv'])
        else:
            x = f[f.timestamp > beg_time]
            x = calc_diff(x)

        xs.append((ip, x))
    return xs




## work starts from here

xs = re_read_file()
#output_file("load.html", title = "server load")
output_server("Server Load (%s) for %s" % (field, description))

hold()

config = zip(xs, style)

#figure(title = "Server load (%s)" % field,
#       x_axis_type = "datetime")

for (ip, x), color in config:
    line(
        x[index],
        x['avg_recv'],
        color = color,
        width = 5,
        legend='Server %s' % ip,
        x_axis_type = "datetime",
        tools = "pan,wheel_zoom,box_zoom,reset,previewsave"
        )

curplot().title = "Server load %s" % field 

# show()

import time
from bokeh.objects import Glyph

render = [r for r in curplot().renderers if isinstance(r, Glyph)]

# end_time = X[index].min()
# while end_time < X[index].max() + delta
# if True:
# if False:
while True:
    xs = re_read_file()
    ziped = zip(xs, render)

    for xs, r in ziped:
        ip, x = xs
        ds = r.data_source
        ds.data['legend'] = "server %s" % ip
        ds.data['x'] = x[index]
        ds.data['y'] = x['avg_recv']
        cursession().store_objects(ds)

    time.sleep(10)

