################### Unit Test ######################

from info import *
from rule_table import *
from dumb_ofctl import *

def TestShowRules(rules):
#    print "\n".join("{0},{1},{2}".format(k[0],k[1],k[2]) for k in rules)
    print "\n".join("{0},{1}".format(k[0],k[1]) for k in rules)
    print ""


def TestGetEcmpInit(dst_str):
    dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
               for x in dst_str.items()}

    return dst


def TestEcmpPolicy(mthread):
    policy = EcmpPolicy()
	
    ecmp_create = [{"1.1.1.1": (2, None),
                    "5.5.5.5": (5, None),
                    "3.3.3.3": (1, None)},
                   {"1.1.1.1": (1, ""),
                    "5.5.5.5": (5, None),
                    "2.2.2.2": (2, None)}]
    ecmp_final = {"4.4.4.4": (3, None),
                  "5.5.5.5": (3, None),
                  "3.3.3.3": (1, None)}
    ecmp_destroy = [1]
    gateway_final = {"4.4.4.4", "5.5.5.5", "3.3.3.3"}
    
    dst_add = [(0,
                {"4.4.4.4": (3, None)})]
    dst_delete = [(0,
                   ["1.1.1.1"])]
    dst_change = [(0,
                   {"5.5.5.5": (3, None)})]
    ecmp_array = []
    
    ## create
    def create():
        for dst in ecmp_create:
            dst_str = TestGetEcmpInit(dst)
            ecmp_id = policy.create_ecmp_group(dst_str)
            ecmp_array.append(ecmp_id)
            
    ## add
    def add():
        for (id, dst) in dst_add:
            ecmp_id = ecmp_array[id]
            dst_str = TestGetEcmpInit(dst)
            policy.add_to_ecmp_group(ecmp_id, dst_str)
            
    ## delete
    def delete():
        for (id, dst) in dst_delete:
            ecmp_id = ecmp_array[id]
            dst_str = [ip_addr_aton(x) for x in dst]
            policy.delete_from_ecmp_group(ecmp_id, dst_str)
            
    ## change
    def change():
        for (id, dst) in dst_change:
            ecmp_id = ecmp_array[id]
            dst_str = TestGetEcmpInit(dst)
            policy.change_ecmp_weights(ecmp_id, dst_str)
            
    ## destroy
    def destroy():
        for id in ecmp_destroy:
            ecmp_id = ecmp_array[id]
            policy.destroy_ecmp_group(ecmp_id)
            
    ## assert init
    def check_create():
        data = policy.get_data()
        for ecmp_id in ecmp_array:
            assert (ecmp_id in data), ("%d not in policy" % ecmp_id)

    ## assert final
    def check_final():
        data = policy.get_data()
	## destroy
        ecmp_id = ecmp_array[1]
        assert (ecmp_id not in data), ("%d in policy" % ecmp_id)
		
	## same
        ecmp_id = ecmp_array[0]
        assert (ecmp_id in data), ("%d not in policy" % ecmp_id)
        dst_str = TestGetEcmpInit(ecmp_final)
        group = EcmpGroup(ecmp_id, dst_str)
        final_data = group.get_data()
        assert (final_data == data[ecmp_id]), ("%s != %s in data" % (final_data, data[ecmp_id]))
		
	## gateway
        gws = policy.get_gateways()
        assert (len(gws) == len(gateway_final)), "#gateways %d != %d" % (len(gws), len(gateway_final))
        for gw in gateway_final:
            assert (gw in gws), ("%s not in gateways" % gw)

    ## assert 
    def check_rule_equal(r1, r2):
        assert (len(r1) == len(r2)), ("#rules %d != %d" % (len(r1), len(r2)))
        for i in range(0, len(r1)):
            p1, m1, a1 = r1[i]
            p2, m2, a2 = r2[i]
            assert p1 == p2, ("priority %d != %d" % (p1, p2))
            assert str(m1) == str(m2), ("match %s != %s" % (str(m1), str(m2)))
            assert str(a1) == str(a2), ("action %s != %s" % (str(a1), str(a2)))
            
    ## apply match and action to abstract_rules
    def apply():
        dst_str = {"1.1.1.1": (2, ""),
                   "2.2.2.2": (1, None),
                   "3.3.3.3": (1, "4.4.4.4")}
        dst = TestGetEcmpInit(dst_str)
        ecmp_id = policy.create_ecmp_group(dst)
        abstract_rules = [(0, ("***", "1.1.1.1")),
                          (1, ("*11", "2.2.2.2")),
                          (2, ("*01", "3.3.3.3"))]

        ## test wildcard
        raw_ip, sip, mask = nw_addr_aton("10.1.0.0&0xffff0000")
        match = Match(sip = sip, sip_mask = mask)
        action = Action()
							 
        sip_int = ipv4_text_to_int(match.m_sip)
        concrete_rules =[(0, Match(sip = ipv4_int_to_text(sip_int),
                                   sip_mask = mask),
                          Action(dip = "1.1.1.1",
                                 gateway = "1.1.1.1")),
                         (1, Match(sip = ipv4_int_to_text(sip_int | 3),
                                   sip_mask = mask | 3),
                          Action(gateway = "2.2.2.2")),
                         (2, Match(sip = ipv4_int_to_text(sip_int | 1),
                                   sip_mask = mask | 3),
                          Action(dip = "3.3.3.3",
                                 gateway = "4.4.4.4"))]
        
        rules = policy.apply(ecmp_id,
                             abstract_rules,
                             match = match,
                             action = action)
        check_rule_equal(rules, concrete_rules)
		

	## test prefix
        raw_ip, sip, prefix_len = nw_addr_prefix_aton("10.1.0.0/16")
        mask = UINT32_MAX & (UINT32_MAX << (32 - prefix_len))
        match = Match(sip = sip, sip_mask = mask)
        action = Action()
        rules = policy.apply(ecmp_id,
                             abstract_rules,
                             match = match,
                             action = action)
        check_rule_equal(rules, concrete_rules)


    if mthread:
        thread1 = Thread(target = create)
        thread2 = Thread(target = add)
        thread3 = Thread(target = delete)
        thread4 = Thread(target = change)
        thread5 = Thread(target = destroy)

        thread1.start()
        thread1.join() 
        check_create()
		
        thread2.start()
        thread3.start()
        thread4.start()
        thread5.start()
        
        thread1.join()
        thread3.join()
        thread4.join()
        thread5.join()
        check_final()

    else:
        create()
        add()
        check_create()
        delete()
        change()
        destroy()
        check_final()
		
    apply()


def TestFlowGroup():
    table = FlowGroupTable()
    fg_array = []
	
    def create():
        _, ip, mask = nw_addr_aton("1.0.0.0&0xff000000")
        match = Match(sip = ip, sip_mask = mask)
        action = Action()
        fg = table.create_flow_group(match, action)
        fg_array.append(fg.m_fg_id)
		
        _, ip, mask = nw_addr_aton("2.0.0.0&0xff000000")
        match = Match(sip = ip, sip_mask = mask)
        action = Action()
        fg = table.create_flow_group(match, action)
        fg_array.append(fg.m_fg_id)
		
    def check_create():
        data = table.get_data()
        for fg_id in fg_array:
            assert (fg_id in data), ("%d not in flow group" % fg_id)
            
	
    def check_get():
        fg_id1 = fg_array[0]
        group = table.get_flow_group(sip = ip_addr_aton("1.0.0.1"))
        assert (group == table[fg_id1]), "group not equal"
        
        group = table.get_flow_group(sip = ip_addr_aton("3.0.0.1"),
                                     sport = 3)
        assert (group == None), "group not equal"

    def check_destroy():
        fg_id = fg_array[0]
        table.destroy_flow_group(fg_id)
        data = table.get_data()
        assert (fg_id not in data), ("%d in data" % fg_id)
		
    create()
    check_create()
    check_get()
    check_destroy()


def TestRuleEngine():
    rule_limit = 5
    default_rules = None
    engine = RuleEngine(rule_limit, default_rules)

    dst_str = {"1.1.1.1": (1, ""),
               "5.5.5.5": (5, None),
               "2.2.2.2": (2, None)}
    dst = TestGetEcmpInit(dst_str)

    fg1 = 1
    ecmp1 = EcmpGroup(fg1, dst)
    msr1 = FGMeasurement()
    if (not engine.add_or_change_flow_group(fg1, ecmp1, msr1)):
        print "WRONG!"

    if (not engine.compute_rules()):
        print "WRONG!"
    rules1 = engine.get_rules(fg1)
    TestShowRules(rules1)


    dst_str = {"1.1.1.1": (1, ""),
               "5.5.5.5": (5, None)}
    dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
           for x in dst_str.items()}

    fg2 = 2
    ecmp2 = EcmpGroup(fg2, dst)
    msr2 = FGMeasurement()
    engine.add_or_change_flow_group(fg2, ecmp2, msr2)

    engine.compute_rules()

    rules1 = engine.get_rules(fg1)
    rules2 = engine.get_rules(fg2)

    print ">>>>>>>>>>>>>>>>>>"
    TestShowRules(rules1)
    TestShowRules(rules2)

    engine.add_or_change_flow_group(fg1, ecmp2, msr1)
    engine.compute_rules()

    rules1 = engine.get_rules(fg1)
    rules2 = engine.get_rules(fg2)

    print ">>>>>>>>>>>>>>>>>>"
    TestShowRules(rules1)
    TestShowRules(rules2)



def TestRuleStore(mthread):
    p = 1
    store = FGRuleStore(1, p)
    _, ip, mask = nw_addr_aton("10.1.0.0&0x00f00000")
    m = Match(sip = ip, sip_mask = mask)
    gw = ip_addr_aton("1.1.1.1")
    a = Action(gateway=gw)
    r1 = (1,(1,m,a))
    r2 = (2,(2,m,a))
    r3 = (3,(3,m,a))

    def rs1():
        store.append([r1])
        print "rs1",
        store.show()

    def rs2():
        store.append([r2])
        print "rs2",
        store.show()

    def rs3():
        store.append([r3])
        print "rs3",
        store.show()

    def mk():
        l = store.check_and_update()
        print "mk",
        store.show()
        l = store.finish_update_and_clear()
        print "mk",
        store.show()
        l = store.finish_clear_and_stablize()
        print "mk",
        store.show()

    if mthread:
        thread1 = Thread(target = rs1)
        thread2 = Thread(target = rs2)
        thread3 = Thread(target = rs3)
        thread4 = Thread(target = mk)
        thread5 = Thread(target = mk)

        thread1.start()
        thread2.start()
        thread3.start()
        thread4.start()
        thread5.start()

        thread1.join()
        thread2.join()
        thread3.join()
        thread4.join()
        thread5.join()

    else:
        rs1()
        mk()
        rs2()
        rs3()
        mk()
        
def TestRoutingTable(mthread):
    
    logger = ScreenLogger()
    tbl = RoutingTable(logger, 0, 20)
    fg_ids = []
    ecmp_ids = []
    def rt1():
        _, sip, smask = nw_addr_aton("1.0.0.0&0xf000000")
        _, dip, dmask = nw_addr_aton("9.9.9.9&0xffffffff")
        match = Match(sip = sip, sip_mask = smask,
                      dip = dip, dip_mask = dmask)
        action = Action()
        fg_id = tbl.create_flow_group(match, action)
        fg_ids.append(fg_id)

        _, sip, smask = nw_addr_aton("2.0.0.0&0xf000000")
        _, dip, dmask = nw_addr_aton("9.9.9.9&0xffffffff")
        match = Match(sip = sip, sip_mask = smask,
                      dip = dip, dip_mask = dmask)
        action = Action()
        fg_id = tbl.create_flow_group(match, action)
        fg_ids.append(fg_id)

    def rt2():
        dst_str = {"1.1.1.1": (1, ""),
                   "2.2.2.2": (2, "")}
        dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
               for x in dst_str.items()}
        ecmp_id = tbl.create_ecmp_group(dst)
        ecmp_ids.append(ecmp_id)

        dst_str = {"3.3.3.3": (1, None),
                   "4.4.4.4": (4, None)}
        dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
               for x in dst_str.items()}
        ecmp_id = tbl.create_ecmp_group(dst)
        ecmp_ids.append(ecmp_id)

    def rt3():
        ecmp_id = ecmp_ids[0]
        fg_id = fg_ids[0]
        tbl.apply_ecmp_to_flow_group(fg_id, ecmp_id)

    def rt4():
        ecmp_id = ecmp_ids[1]
        fg_id = fg_ids[1]
        tbl.apply_ecmp_to_flow_group(fg_id, ecmp_id)

    def rt5():
        ecmp_id = ecmp_ids[1]
        fg_id = fg_ids[0]
        tbl.apply_ecmp_to_flow_group(fg_id, ecmp_id)

    def rt6():
        ecmp_id = ecmp_ids[1]
        dst_str = {"7.7.7.7": (2, None)}
        dst = {ip_addr_aton(x[0]): (x[1][0], ip_addr_aton(x[1][1]))
               for x in dst_str.items()}
        tbl.add_to_ecmp_group(ecmp_id, dst)

    def rt7():
        ecmp_id = ecmp_ids[0]
        fg_id = fg_ids[1]
        tbl.apply_ecmp_to_flow_group(fg_id, ecmp_id)

    def rt8():
        ecmp_id = ecmp_ids[1]
        dst_str = ["3.3.3.3"]
        dst = [ip_addr_aton(x) for x in dst_str]
#       gw_str = {"3.3.3.3":5}
#       gws = {ip_addr_aton(x[0]):x[t] for x in gw_str.items()}
        tbl.delete_from_ecmp_group(ecmp_id, dst)
#        tbl.change_ecmp_weights(ecmp_id, gws)

    def rt9():
        fg_id = fg_ids[0]
        tbl.destroy_flow_group(fg_id)
    

    install_stop = False
    def do_install():
        while (not install_stop):
            rule = tbl.pop_next_install_rule()
            if (rule == None):
               continue
            print "do install", str(rule)

    clear_stop = False
    def do_clear():
        while (not clear_stop):
            rule = tbl.pop_next_clear_rule()
            if (rule == None):
                continue
            print "do clear", str(rule)

    thread1 = Thread(target = do_install)
    thread2 = Thread(target = do_clear)
    tbl.start()
    thread1.start()
    thread2.start()
    rt1()
    rt2()
    if not mthread:
        rt3()
        rt4()
        rt5()
        rt6()
        rt7()
        rt8()
        rt9()
        time.sleep(1)
    else:
        thread3 = Thread(target = rt3)
        thread4 = Thread(target = rt4)
        thread5 = Thread(target = rt5)
        thread6 = Thread(target = rt6)
        thread7 = Thread(target = rt7)
        thread8 = Thread(target = rt8)
        thread9 = Thread(target = rt9)
        thread3.start()
        thread4.start()
        thread5.start()
        thread6.start()
        thread7.start()
        thread8.start()
        thread9.start()
        time.sleep(1)
        
        thread3.join()
        thread4.join()
        thread5.join()
        thread6.join()
        thread7.join()
        thread8.join()
        thread9.join()

    install_stop = True
    clear_stop = True
    thread1.join()
    thread2.join()
    tbl.stop()
    tbl.show()

#    tbl.install()
#    do_install()
#    tbl.clear()
#    do_clear()
#    tbl.done()



def TestRule():
    m = Match(sip = "10.0.0.0",
              sip_mask = 0xff000000,
              dip = "192.168.6.6",
              dip_mask = 0xffffffff,
              ip_proto = 6,
              sport = 4,
              dport = 5)

    m1 = Match(sip = "10.0.0.0",
              sip_mask = 0xff000000,
              dip = "192.168.6.6",
              dip_mask = 0xffffffff,
              ip_proto = 6,
              sport = 4,
              dport = 5)

    assert (m == m1), "match unequal!"
    m1.m_sport = 6
    assert (m != m1), "match equal!"
    print "match", m

    a = Action(gateway = "192.168.1.1",
               sip = 0,
               dip = 0,
               sport = 0,
               dport = 0)

    a1 = Action(gateway = "192.168.1.1",
                sip = 0,
                dip = 0,
                sport = 0,
                dport = 0)
    assert (a == a1), "action unequal!"
    a1.m_sport = 6
    assert (a != a1), "action equal!"
    print "action", a

    rule = Rule(rule_id = 1,
                fg_id = 2,
                priority = 3,
                match = m,
                action = a)

    s = str(rule)
    rule_ = Rule.parse_rule(s)
    assert (rule == rule_), "rule unequal!"


def TestArpTable():
    tbl = ArpTable()
    tbl.add(ip_addr_aton("1.1.1.1"),
            "00-00-00-00-00-01",
            "00-00-00-00-00-00",
            1)
    tbl.show()
    time.sleep(1)
    tbl.add(ip_addr_aton("1.1.1.2"),
            "00-00-00-00-00-02",
            "00-00-00-00-00-00",
            2)
    tbl.show()
    time.sleep(1)
    tbl.clear(1.5)
    tbl.show()

def TestAddressData():
    tbl = AddressData()
    a = "10.0.0.2/24"
    b = "192.168.0.3/16"
    a_id = tbl.add_address(a).address_id
    b_id = tbl.add_address(b).address_id
    tbl.show()
    print a_id
    print tbl.get_address(ip = ip_addr_aton('10.0.0.5'))
    print tbl.get_address(ip = ip_addr_aton('10.0.1.0'))
    tbl.delete_address(address_id = a_id)
    tbl.show()
    

# TestRuleEngine()
# TestEcmpPolicy(False)
# TestFlowGroup()
# TestRule()
TestRuleStore(False)
# TestRoutingTable(False)
# TestArpTable()
# TestAddressData()

if False:
    s = "{'a':3,'b':4 }"
    d = ast.literal_eval(s)
    print check_dict_type(d, str, int)
    s = "[3,4,5]"
    k = ast.literal_eval(s)
    print check_list_type(k, int)



