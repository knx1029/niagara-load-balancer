import __init__
from sql_wrapper import SQLWrapper
from base_mgr import BaseManager
from table_owner import Field, Table, TableSchema
from rule_gen import RuleGenerator
from rule_translator import *

## Manage rule tables
class RuleManager(BaseManager):

######### STATIC INFO START ############
  RULE_CONFIG = {}

  RULE_CONFIG[TableSchema.ACTIVE_VERSION_TBNAME] = []

  RULE_CONFIG[TableSchema.MARKING_VERSION_TBNAME] = [
#    ("vip1", 1, 0, 0, BaseManager.DEFAULT, BaseManager.TRANS_ID),
#    ("vip1", 2, 0, 0, BaseManager.DEFAULT, BaseManager.TRANS_ID),
#    ("vip1", 3, 0, 0, BaseManager.DEFAULT, BaseManager.TRANS_ID),
  ]

  RULE_CONFIG[TableSchema.RULE_TABLE_TBNAME] = []

  RULE_CONFIG[TableSchema.ABSTRACT_RULE_TABLE_TBNAME] = []

  RULE_TEMPLATE = "({}, {}, {}, {}, {}, {}, {}, default, {})"

  U32_RULE_TEMPLATE = "iptables -m u32 --u32 \"{}\" -j {} {}"

######### STATIC INFO FINISH ############

  def __init__(self, wrapper):
    BaseManager.__init__(self, wrapper)
    self.rule_generator = RuleGenerator()
    pass

  def init_rule_info(self, trans_id):
    self.init_info(RuleManager.RULE_CONFIG, trans_id)

  ## compute vip_rules
  def compute_vip_rules(self, vip_mgr, vip_ids, trans_id):
    self.start_op()

    ## clear previous
    # for vip_id in vip_ids:
    #  criteria = [(Field.VIP_LABEL, repr(vip_id))]
    #  self.delete_info(TableSchema.RULE_TABLE_TBNAME, criteria)

    argv = ["-ecmp", "none", "-mode", "multi_vip"]
    vips = self.__read_vip_weights(vip_mgr, vip_ids)
    ## get the related devices involved in the vip setup
    print vips
    def f(z, x):
      return z + map(lambda y: y[0], x[2])
    related_device = reduce(f, vips, [])
    # hack here: does not do grouping, assume each vip is a group
    # vip_id and vip_label is one-to-one mapping
    hw_rules, sw_rules = self.rule_generator.generate_mvip_rules(argv, vips)

    vip_info = self.__read_vip_info(vip_mgr, vip_ids)
    topo = self.__read_topo(related_device)

    u32_trans = U32RuleTranslator(hw_rules, sw_rules)
    of_trans = OfRuleTranslator(hw_rules, sw_rules)
    abstract_trans = AbstractRuleTranslator(hw_rules, sw_rules)

    abstract_config = dict()
    actual_config = dict()
    dev_spec, up, down = topo

    for dev_id in dev_spec:
      dev_type, dev_class = dev_spec[dev_id]
      abstract_rule = abstract_trans.translate_rules(dev_id,
                                                     down[dev_id],
                                                     up[dev_id],
                                                     dev_class,
                                                     vip_info)
      if (dev_type == "Pica8"):
        actual_rule = of_trans.translate_rules(dev_id,
                                               down[dev_id],
                                               up[dev_id],
                                               dev_class,
                                               vip_info)

      elif (dev_type == "Linux"):
        print "yes", dev_id
        actual_rule = u32_trans.translate_rules(dev_id,
                                                down[dev_id],
                                                up[dev_id],
                                                dev_class,
                                                vip_info)
      else:
        actual_rule = []

      print "DEVICE :", dev_id
      print "\n".join("{}".format(k) for k in actual_rule)
      abstract_config[dev_id] = abstract_rule
      actual_config[dev_id] = actual_rule

    
    vip_labels = self.__read_vip_label(vip_ids)
    current_versions = self.__read_or_create_version(vip_ids, trans_id)
    new_versions = dict()
    for (vip_id, current_version) in current_versions.items():
      new_versions[vip_id] = current_version + 1

    self.__write_abstract_rule_table(abstract_config,
                                     vip_labels,
                                     new_versions,
                                     topo,
                                     trans_id)
    self.__write_rule_table(actual_config,
                            vip_labels,
                            new_versions,
                            topo,
                            trans_id)
    self.__write_version(new_versions, trans_id)

    self.end_op()

  ## read active version
  def __read_or_create_version(self, vip_ids, trans_id):
    versions = dict()
    for vip_id in vip_ids:
      fields = [Field.VERSION]
      criteria = [(Field.VIP_ID, repr(vip_id))]
      entry = self.query_one_info(fields, TableSchema.ACTIVE_VERSION_TBNAME, 
                                  criteria, None, None)
      if (entry == None):
        start_version = 1
        tuples = [(repr(start_version),
                 repr(vip_id),
                 BaseManager.DEFAULT_VALUE,
                 repr(trans_id))]
        self.insert_info(TableSchema.ACTIVE_VERSION_TBNAME, tuples, trans_id)
        versions[vip_id] = start_version
      else:
        version = int(entry[0])
        versions[vip_id] = version
    return versions

  ## write active version
  def __write_version(self, versions, trans_id):
    for (vip_id, version) in versions.items():
      criteria = [(Field.VIP_ID, repr(vip_id))]
      values = [(Field.VERSION, version),
                (Field.TRANSACTION_ID, repr(trans_id))]
      self.update_info(TableSchema.ACTIVE_VERSION_TBNAME, values, criteria)

  # read vip label
  def __read_vip_label(self, vip_ids):
    vip_labels = dict()
    for vip_id in vip_ids:
      fields = [Field.VIP_LABEL]
      criteria = [(Field.VIP_ID, repr(vip_id))]
      entry = self.query_one_info(fields, TableSchema.VIP_LABEL_TBNAME, 
                                  criteria, None, None)
      vip_label = entry[0]
      vip_labels[vip_id] = str(vip_label)

    return vip_labels


  ## pull vip weights
  def __read_vip_weights(self, vip_mgr, vip_ids):
    vips = []
    for vip_id in vip_ids:
      traffic = vip_mgr.read_vip_traffic(vip_id)
      weights = vip_mgr.read_vip_grouped_weights(vip_id)
      vips.append((vip_id, traffic, weights))
    return vips

  ## pull vip ips
  def __read_vip_info(self, vip_mgr, vip_ids):
    vip_info = dict()
    for vip_id in vip_ids:
      vip_info[vip_id] = vip_mgr.read_vip_desc(vip_id)
    return vip_info


  ## pull dev class
  def __read_topo(self, related_dev = None):

    # get the related devices and their links
    up = dict()
    down = dict()

    fields = [Field.DEVICE_ID, Field.NORTH_BOUND_DEVICE_ID]
    list = self.query_info(fields, TableSchema.DEVICE_ID_TBNAME, None, None, None)

    for entry in list:
      down_dev_id, up_dev_id = entry
      if (related_dev is not None):
        if (not (down_dev_id in related_dev)):
          if (not (up_dev_id in related_dev)):
            continue
      if (down_dev_id in up):
        up[down_dev_id].append(up_dev_id)
      else:
        up[down_dev_id] = [up_dev_id]
      if (up_dev_id in down):
        down[up_dev_id].append(down_dev_id)
      else:
        down[up_dev_id] = [down_dev_id]

    # get the spec of related-devices
    X = TableSchema.DEVICE_ID_TBNAME
    Y = TableSchema.DEVICE_SPEC_TBNAME
    I = Field.DEVICE_SPEC_ID
    fields = [Field.DEVICE_ID, Field.DEVICE_TYPE, Field.DEVICE_CLASS]
    tb_name = "{},{}".format(X, Y)
    criteria = [("{}.{}".format(X, I), "{}.{}".format(Y, I))]
    list = self.query_info(fields, tb_name, criteria, None, None)

    dev_spec = dict()
    for entry in list:
      dev_id = entry[0]
      if (dev_id in down) or (dev_id in up):
        dev_spec[dev_id] = (entry[1], entry[2])
        if not (dev_id in down):
          down[dev_id] = []
        if not (dev_id in up):
          up[dev_id] = []

    topo = (dev_spec, up, down)
    return topo

  ## insert abstract rules to DB
  def __write_abstract_rule_table(self, config, labels, versions, topo, trans_id):

    dev_spec, _, _ = topo
    rules = []

    for device_id in config:
      dev_config = config[device_id]
      for i in range(0, len(dev_config)):
        line = dev_config[i]
        pktmatch, to_device_id, vip_id = line

        vip_label = labels[vip_id]
        version = versions[vip_id]
        one_rule = (repr(version),
                    repr(vip_label),
                    repr(device_id),
                    repr(pktmatch), 
                    repr(to_device_id),
                    repr(i), 
                    BaseManager.DEFAULT_VALUE,
                    repr(trans_id))
        rules.append(one_rule)

    self.insert_info(TableSchema.ABSTRACT_RULE_TABLE_TBNAME, rules, trans_id)


  ## insert iptable u32 rules to DB
  def __write_rule_table(self, config, labels, versions, topo, trans_id):
    
    dev_spec, _, _ = topo
    rules = []

    for device_id in config:
      dev_config = config[device_id]
      for i in range(0, len(dev_config)):
        line = dev_config[i]
        pktmatch, to_device_id, vip_id = line
        action = ""
        HW = RuleTranslator.HW
        SW = RuleTranslator.SW
        BE = RuleTranslator.BE
        dev_type, dev_class = dev_spec[device_id]
        to_dev_type, to_dev_class = dev_spec[to_device_id]
        if (dev_class == HW and to_dev_class == SW):
          action = "REDIRECT_TO"
        elif (dev_class == SW and to_dev_class == SW):
          action = "REDIRECT_TO"
        elif (dev_class == SW and to_dev_class == BE):
          action = "SEND_TO" 
        elif (dev_class == BE and to_dev_class == SW):
          action = "SEND_TO" 
        elif (dev_class == HW and to_dev_class == HW):
          action = "SEND_TO"
        else:
          print dev_class, to_dev_class
          pass

        vip_label = labels[vip_id]
        version = versions[vip_id]
        one_rule = (repr(version),
                    repr(vip_label),
                    repr(device_id),
                    repr(pktmatch), 
                    repr(action),
                    repr(to_device_id),
                    repr(i), 
                    BaseManager.DEFAULT_VALUE,
                    repr(trans_id))
        rules.append(one_rule)

    self.insert_info(TableSchema.RULE_TABLE_TBNAME, rules, trans_id)


  def close(self):
    pass
