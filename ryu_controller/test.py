from ecmp_router import *
from dumDbp_ofctl import *

class HwPort:
    def __init__(self, port_no, hw_addr):
        self.port_no = port_no
        self.hw_addr = hw_addr

def TestEcmpRouter():
    dp = DumbDatapath(1)
    logger = ScreenLogger()
    debugger = Debugger()
    ofctl = DumbOfCtl(dp, logger, debugger)

    port_data = PortData({1:HwPort(1, "00-00-00-00-00-01"),
                          2:HwPort(2, "00-00-00-00-00-02"),
                          3:HwPort(3, "00-00-00-00-00-03")})

    def turn_off():
        debugger.turn_off()
        logger.turn_off()

    def turn_on():
        debugger.turn_on()
        logger.turn_on()

    def match(priority = 0, sip = 0, dip = 0, sport = 0, dport = 0,
              new_sip = 0, new_dip = 0, new_sport = 0, new_dport = 0):
        match = dict()
        if priority:
            match[REST_FG_PRIORITY] = priority
        if sip:
            match[REST_SIP] = sip
        if dip:
            match[REST_DIP] = dip
        if sport:
            match[REST_SPORT] = sport
        if dport:
            match[REST_DPORT] = dport
        if new_sip:
            match[REST_NEW_SIP] = new_sip
        if new_dip:
            match[REST_NEW_DIP] = new_dip
        if new_sport:
            match[REST_NEW_SPORT] = new_sport
        if new_dport:
            match[REST_NEW_DPORT] = new_dport
        return match

    def set_address(s):
        print "-----------set address----------"
        data = {}
        data[REST_ADDRESS] = s
        print router.set_data(data)

    def set_ecmp(op, gw = 0, id = 0):
        print "----------%s ecmp group----------" % op
        data = {}
        data[REST_ECMP_GROUP] = op
        if gw:
            data[REST_ECMP_GATEWAY] = gw
        if id:
            data[REST_ECMP_ID] = id
        print router.set_data(data)


    def set_flow(op, match, id = 0, e_id = 0):
        print "----------%s ecmp group----------" % op
        data = {}
        data[REST_FLOW_GROUP] = op
        data.update(match)
        if id:
            data[REST_FLOW_GROUP_ID] = repr(id)
        if e_id:
            data[REST_ECMP_ID] = repr(e_id)
        print router.set_data(data)

    def delete_data(id = 0, e_id = 0, a_id = 0):
        print "----------delete data----------"
        data = {}
        if id:
            data[REST_FLOW_GROUP_ID] = id
        if e_id:
            data[REST_ECMP_ID] = e_id
        if a_id:
            data[REST_ADDRESSID] = a_id
        print router.delete_data(data, None)

    def add_arp():
        router.arp_table.add(dst_ip = ip_addr_aton("10.1.0.1"),
                             dst_mac = "10-01-00-01-00-00",
                             src_mac = "00-00-00-00-00-01",
                             out_port = 1)

        router.arp_table.add(dst_ip = ip_addr_aton("10.2.0.1"),
                             dst_mac = "10-02-00-01-00-00",
                             src_mac = "00-00-00-00-00-01",
                             out_port = 2)


    ## test starts here

    print "---------init----------"
    turn_off()
    router = EcmpRouter(0, dp, ofctl, port_data, logger)

    set_address("10.0.0.2/16")
    set_address("10.1.0.2/16")
    set_address("10.2.0.2/16")
#    delete_data(a_id = 1)

    set_ecmp("create", gw = "{'10.1.0.1':(2,None), '10.3.0.1':(2,None)}")
    set_ecmp("create", gw = "{'10.1.0.1':(1,''), '10.2.0.1':(2,'')}")
    set_ecmp("add", gw = "{'10.2.0.1':(1,None)}", id = 2)
    set_ecmp("change", gw = "{'10.1.0.1':(1,None)}", id = 2)
    set_ecmp("delete", gw = "['10.3.0.1']", id = 2)
#    set_ecmp("destroy", id = 3)
#    delete_data(e_id = 3)

    m = match(sip = "10.0.0.1&0xffff0000")
    set_flow("create", m)
    set_flow("apply", {}, id = 1, e_id = 2)
    m = match(dip = "10.3.5.5&0xffffffff")
    set_flow("create", m)
    set_flow("apply", {}, id = 2, e_id = 3)
#    set_flow("destroy", {}, id = 2)
#    delete_data(id = 2)

    add_arp()

    print ""
#   turn_on()
    router.start({})
#    set_flow("apply", {}, id = 1, e_id = 3)
#    set_flow("destroy", {}, id = 2)

    time.sleep(1)
    print "-------------get----------"
    data = router.get_data()
    print "\n".join("{0}:{1}".format(x[0], x[1]) for x in data.items())

    router.stop()

    print ""
    print ""
    router.routing_table.show()

    print ""
    print ""

    msg = ofctl.get_all_flow(None)
    for flow in msg[0].body:
        print str(flow)


TestEcmpRouter()
# l = '{"2":(None, 1)}'
# k = ast.literal_eval(l)
# print check_dict_type(k, str, tuple, str, int)
