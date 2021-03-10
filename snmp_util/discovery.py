from snmp_util.reference.get_ip_interfaces import get_ip_interfaces 
from snmp_util.reference.device_info import device_info 
from snmp_util.reference.model_parser import model_parser as model_parser
import time
from netaddr import *

class network_discovery:
    def __init__(self, ip_address, subnet,community_string):
        self.ip_range = """{0}/{1}""".format(ip_address,subnet)
        self.community_string = community_string

    # def get_network_interfaces(self):
    #     runner = get_ip_interfaces(self.ip_range)
    #     ip_list = runner.run()
    #     return ip_list
    def get_network_interfaces(self):
       
        ip_list = []
        for ip in IPNetwork(self.ip_range):
            ip_list.append('%s' % ip)
        return ip_list
    def validate_snmp(self,ip_list):
        main_info = []
        for i in range(len(ip_list)):
            print( ip_list[i])
            ip_address = ip_list[i]
            mdi_runner = device_info(ip_address,self.community_string)
        
            raw_info = mdi_runner.run()
            
            if raw_info["is_valid"]:
                raw_info["device_info"]["ip_address"] = ip_address
                bp_runner = model_parser(raw_info["device_info"])
                bp_info = bp_runner.run()
                main_info.append(bp_info)
        return main_info


    def run(self):
        ip_list = self.get_network_interfaces()
        if len(ip_list) > 0:
            return(self.validate_snmp(ip_list))
        else:
            return []

