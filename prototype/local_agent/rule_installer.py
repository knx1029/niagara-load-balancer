import os
import sys
import __init__
from sql_wrapper import SQLWrapper
from base_slave import BaseSlave
from table_owner import Field, Table, TableSchema

## Manage rule tables
class RuleInstaller(BaseSlave):

######### STATIC INFO START ############

  ## these three command is used to fix a bug in ng-vlan, will be deleted later
  BUG_SW_CMD = "sudo iptables -D PREROUTING -j NG_tcp_signals -t mangle"
  BUG_BE_CMD1 = "sudo iptables -D PREROUTING -j NG_tcp_signals -t mangle"
  BUG_BE_CMD2 =  "sudo iptables -I PREROUTING -j NG_tcp_signals -t mangle"

  ## the command to call ng-vlan
  EXE_FILE = "../bin/ng-vlan"
  INSTALL_SW_RULES_CMD = "sudo {} installroutes eth0 {}"
  INSTALL_BE_RULES_CMD = "sudo {} installberoutes eth0 {}"
  UPDATE_VERSION_CMD = "sudo {} updatevipversion {} {} {}"

  ## TYPES
  HSW = "HSW"
  SSW = "SSW"
  BE = "BE"

# TABLES['active_version'] = (
#  "version int NOT NULL, "
#  "vip_id varchar(64), "
#  "ts timestamp NOT NULL, "
#  "transaction_id varchar(64) NOT NULL, "
#  "PRIMARY KEY (version, vip_id)"
# )

# TABLES['marking_version'] = (
#  "vip_id varchar(64) NOT NULL, "
#  "device_id int NOT NULL, "
#  "installed_version int NOT NULL,"
#  "marking_version int NOT NULL, "
#  "ts timestamp NOT NULL, "
#  "transaction_id varchar(64) NOT NULL,"
#  "PRIMARY KEY (vip_id, device_id)"
# )


  U32_RULE_TEMPLATE = "iptables -m u32 --u32 \"{}\" -j {} {}"
# TABLES['rule_table'] = (
#  "version int NOT NULL, "
#  "vip_label varchar(64) NOT NULL, "
#  "device_id int NOT NULL, "
#  "pktmatch varchar(512) NOT NULL, "
#  "action int NOT NULL, " #forward to switch, forward to backend, drop, reject, nat to switch, nat to backend
#  "to_device_id int NOT NULL, "
#  "priority int NOT NULL, " # smaller is higher
#  "ts timestamp NOT NULL, "
#  "transaction_id varchar(64) NOT NULL, "
#  "PRIMARY KEY (version, device_id, priority)"
#)

######### STATIC INFO FINISH ############

  def __init__(self, device_id,  wrapper):
    BaseSlave.__init__(self, device_id, wrapper)
    ip, type = self.__read_device_info(device_id)
    self.device_ip = ip
    if (RuleInstaller.HSW in type):
      self.device_type = RuleInstaller.HSW
    elif (RuleINstaller.SSW in type):
      self.device_type = RuleINstaller.SSW
    elif (RuleINstaller.BE in type):
      self.device_type = RuleINstaller.BE
    else:
      pass

#    self.ip = "10.99.88.80"
#    self.device_type = RuleInstaller.HW

  # instatiate an external process
  def __run_cmd(self, cmd):
    print "Running ", cmd
#    ret = os.system(cmd)
#    if (ret != 0):
#      exit(ret)


  ## check if new rules are pushed into the database
  def check_install_new_rule(self, vip_id, trans_id):
    active_version = self.__read_active_version(vip_id)
    marking_version, installed_version = self.__read_device_version(vip_id)
    vip_label = self.__read_vip_label(vip_id)
    # install version one by one
    current_version = installed_version
    for version in range(installed_version + 1, active_version + 1):
      
      self.start_op()
      self.__install_new_version(vip_id, vip_label, version, trans_id)
      self.end_op()
      current_version = version
      break

    return (current_version, marking_version, 
            active_version, installed_version)



  ## update to a newer version
  def apply_new_version(self, vip_id, trans_id, new_version = -1):
    active_version = self.__read_active_version(vip_id)
    marking_version, installed_version = self.__read_device_version(vip_id)
    if (new_version < 0):
      new_version = installed_version
#      new_version = marking_version + 1

    if (new_version > installed_version or new_version > active_version):
      return False
    else:
      self.start_op()
      vip_ip = self.__read_vip_ip(vip_id)
      self.__update_version(vip_id, vip_ip, marking_version, new_version, trans_id)
      self.end_op()
      return True


  ## install version one by one
  def __install_new_version(self, vip_id, vip_label, version, trans_id):

    def __call():
      exe_file = RuleInstaller.EXE_FILE
      if (self.device_type == RuleInstaller.HSW or self.device_type == RuleInstaller.SSW):
        cmd = RuleInstaller.BUG_SW_CMD
        self.__run_cmd(cmd)
        cmd = RuleInstaller.INSTALL_SW_RULES_CMD.format(exe_file, rule_file_name)
        self.__run_cmd(cmd)
      elif (self.device_type == RuleInstaller.BE):
        cmd = RuleInstaller.BUG_BE_CMD1
        self.__run_cmd(cmd)
        cmd = RuleInstaller.BUG_BE_CMD2
        self.__run_cmd(cmd)
        cmd = RuleInstaller.INSTALLE_SW_RULES_CMD.format(exe_file, rule_file_name)
        self.__run_cmd(cmd)
      else:
        pass

    # this is a hack, should be modified to random-genearte 
    rule_file_name = "tmp_rule.txt"
    # write files
    self.__dump_ruleset_to_file(rule_file_name, vip_id, vip_label, version)
    # call external installer
    __call()
    # update version
    self.__write_installed_version(vip_id, version, trans_id)


  ## call
  def __update_version(self, vip_id, vip_ip, marking_version, new_version, trans_id):
    if (self.device_type == RuleInstaller.HSW):
      exe_file = RuleInstaller.EXE_FILE
      cmd = RuleInstaller.UPDATE_VERSION_CMD.format(exe_file, vip_ip, marking_version, new_version)
    else:
      pass
    self.__write_marking_version(vip_id, new_version, trans_id)


  ## write rules from SQL to file
  def __dump_ruleset_to_file(self, file_name, vip_id, vip_label, version):
    output = open(file_name, 'w')
    device_id = self.device_id

    # query
    count_str = ["count(*)"]
    fields = [Field.PKT_MATCH, Field.ACTION, Field.TO_DEVICE_ID, Field.PRIORITY]
    criteria = [(Field.VIP_LABEL, repr(vip_label)),
                (Field.VERSION, repr(version)),
                (Field.DEVICE_ID, repr(device_id))]
    group = None
    order = ["{} ASC".format(Field.PRIORITY)]

    num_rules = 0
    item = self.query_one_info(count_str, TableSchema.RULE_TABLE_TBNAME, criteria, 
                          group, order)
    num_rules = int(item[0])

    a = self.query_info(fields, TableSchema.RULE_TABLE_TBNAME, criteria, 
                        group, order)
    rules = []
    for item in a:
      pktmatch, action_id, to_device_id, _ = item
      to_device_ip, _ = self.__read_device_info(to_device_id)
      one_rule = RuleInstaller.U32_RULE_TEMPLATE.format(pktmatch, 
         BaseSlave.ACTION_DICT[action_id], to_device_ip)
      print one_rule
      rules.append(one_rule)

    # the line to output:
    # switch = 1
    # the line to output:
    # version = 1
    output.write("version = {}\n".format(version))
    output.write("switch = {}\n".format(self.device_ip))

    # the line to parse:
    # rules = 1
    output.write("rules = {}\n".format(len(rules)))
    for one_rule in rules:
      output.write("{}\n".format(one_rule))

    output.close()


  ## read device information
  def __read_device_info(self, device_id):
    # this is hack to get the device type
    fields = [Field.DEVICE_ADDRESS, Field.DEVICE_COMMENT]
    criteria = [(Field.DEVICE_ID, repr(device_id))]
    entry = self.query_one_info(fields, TableSchema.DEVICE_ID_TBNAME,
                                  criteria, None, None)
    ip = str(entry[0])
    type = str(entry[1])
    return ip, type

  # read vip ip
  def __read_vip_ip(self, vip_id):
    fields = [Field.VIP]
    criteria = [(Field.VIP_ID, repr(vip_id))]
    entry = self.query_one_info(fields, TableSchema.SERVICE_DESC_TBNAME, 
                                  criteria, None, None)
    vip = str(entry[0])
    return vip

  # read vip label
  def __read_vip_label(self, vip_id):
    fields = [Field.VIP_LABEL]
    criteria = [(Field.VIP_ID, repr(vip_id))]
    entry = self.query_one_info(fields, TableSchema.VIP_LABEL_TBNAME, 
                                  criteria, None, None)
    vip_label = str(entry[0])
    return vip_label

  ## read active version
  def __read_active_version(self, vip_id):
    fields = [Field.VERSION]
    criteria = [(Field.VIP_ID, repr(vip_id))]
    entry = self.query_one_info(fields, TableSchema.ACTIVE_VERSION_TBNAME, 
                                  criteria, None, None)
    version = int(entry[0])
    return version


  ## read marking & installed version
  def __read_device_version(self, vip_id):
    fields = [Field.MARKING_VERSION, Field.INSTALLED_VERSION]
    criteria = [(Field.VIP_ID, repr(vip_id)), 
                (Field.DEVICE_ID, repr(self.device_id))]
    entry = self.query_one_info(fields, TableSchema.MARKING_VERSION_TBNAME, 
                                  criteria, None, None)
    marking_version = int(entry[0])
    installed_version = int(entry[1])
    return marking_version, installed_version

  ## write installed version
  def __write_installed_version(self, vip_id, version, trans_id):
    criteria = [(Field.VIP_ID, repr(vip_id)), 
                (Field.DEVICE_ID, repr(self.device_id))]
    values = [(Field.INSTALLED_VERSION, version),
              (Field.TRANSACTION_ID, repr(trans_id))]
    self.update_info(TableSchema.MARKING_VERSION_TBNAME, values, criteria)

  ## write installed version
  def __write_marking_version(self, vip_id, version, trans_id):
    criteria = [(Field.VIP_ID, repr(vip_id)), 
                (Field.DEVICE_ID, repr(self.device_id))]
    values = [(Field.MARKING_VERSION, version),
              (Field.TRANSACTION_ID, repr(trans_id))]
    self.update_info(TableSchema.MARKING_VERSION_TBNAME, values, criteria)


  def close(self):
    pass
