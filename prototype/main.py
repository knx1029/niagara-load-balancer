from sql.sql_wrapper import SQLWrapper
from sql.table_owner import TableOwner
from sql.device_mgr import DeviceManager
from sql.vip_mgr import VIPManager
from rule_gen.rule_mgr import RuleManager
from local_agent.rule_installer import RuleInstaller

db_name = 'niagara_test'

config = {
   'user': 'root',
   'host': 'localhost',
#  'password': ' ',
#  'database': '',
   'raise_on_warnings': True,
}


wrapper = SQLWrapper(config)
#wrapper.create_db(db_name)
wrapper.change_db(db_name)

table_owner = TableOwner(wrapper)
table_owner.create_table()

device_mgr = DeviceManager(wrapper)
device_mgr.init_device_info("tid#device_init")

vip_mgr = VIPManager(wrapper)
vip_mgr.init_vip_info("tid#vip_init")

rule_mgr = RuleManager(wrapper)
rule_mgr.init_rule_info("tid#rule_init")
rule_mgr.compute_vip_rules(vip_mgr, ["vip1"], "tid#rule_gen")
#rule_mgr.compute_vip_rules(vip_mgr, ["vip2"], "tid#rule_gen")
#rule_mgr.compute_vip_rules(["vip1"], "tid#rule_gen2")
#rule_mgr.insert_ruleset_from_file("../rules4.txt", "vip_group1", "tid#insert_rules4")
#rule_mgr.dump_ruleset_to_file("../rules4@dev1.txt", "vip_group1", "4", "1")

# device_id = 1
# rule_installer = RuleInstaller(device_id, wrapper)
# cv, mv, av, ov = rule_installer.check_install_new_rule("vip1", "tid#rule_install")
# rule_installer.apply_new_version("vip1", "tid#version_update")
wrapper.commit()
wrapper.close()
