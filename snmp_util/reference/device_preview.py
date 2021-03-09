from snmp_util.reference.main_device_info import main_device_info
from snmp_util.reference.main_device_details import main_device_details

import snmp_util.resources.sql_utils as sql_utils
from utils.database_util import DatabaseUtil
import os
class PollPreview:
    def __init__(self,prev_config):
        self.ip_list = prev_config['ip_list']
        self.community_string = prev_config['community_string']
        self.oid_list = prev_config['oid_list']
        self.conn = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"),os.environ.get("SNMP_DB_PORT"))

    def get_oid_prev(self,device_model):
        oid_list = {"oid_list" :[]}
        oid_inner = dict()
        for oid_key in self.oid_list:
            sql_query = sql_utils.sql_templates["oid_prev"].value
            oid_raw = self.conn.jinja_select_query(sql_query, {'oid_key': oid_key,'device_model': device_model})[0]
            oid_inner[oid_raw['oid_key']] = oid_raw['oid']
        oid_list['oid_list'] = [oid_inner]
        return oid_list

    def run(self):
        main_data =list()
        try:
            for prev_info in self.ip_list:
                ip_address = prev_info['ip_address']
                device_model = prev_info['device_model']
                for_mdd = self.get_oid_prev(device_model)
                mdd_runner = main_device_details(ip_address , for_mdd , self.community_string)
                mdd_output = mdd_runner.run()
                mdd_output["ip_address"] = ip_address
                main_data.append(mdd_output)
            return main_data
        except Exception as err:
            print("err-----------------------------------")
            print(err)
            raise ValueError("Invalid device model or oid list")
          

# prev_config = {
#     'ip_list' : [{'ip_address' : '192.168.1.1' , 'device_model' : 'cisco'}],
#     'community_string' : 'trends-ro',
#     'oid_list' : ['cpu' , 'memory']
# }
# sample = PollPreview(prev_config)
# abcd = sample.run()
# print(abcd)