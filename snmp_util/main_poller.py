from snmp_util.reference.main_device_info import main_device_info
from snmp_util.reference.main_device_details import main_device_details
from utils.database_util import DatabaseUtil
import snmp_util.resources.sql_utils as sql_utils
import requests
import datetime
import multiprocessing
import os
import sys
import time
import atexit
import psutil
import signal
from utils.pid_util import ProcessIdUtil
from utils.log_util import Logger

logs_directory = 'poller_logs'
pid_directory = 'poller_pid'

class start_polling:
    def __init__(self,poller_id = 0):
        self.poller_id = poller_id
        # self.conn = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"))
        try:
            self.conn = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"),os.environ.get("SNMP_DB_PORT"))
            conn = self.conn.get_connection(interval = 60)
            conn.close()
        except Exception as err:
            print(err)
            sys.exit()
        self.logger = None
        self.pid_util = None
        atexit.register(self.exit_handler)

    def poller_event(self, status):
        status = int(status)
        try:
            self.conn.jinja_update_query(sql_utils.sql_templates["update_event"].value, {"status":status , "id":self.poller_id})
            if status is not 1:
                os.kill(os.getpid(), signal.SIGINT)
        except Exception as err:
            self.logger.log('An error has occured while updating poller status: {0}'.format(err), 'critical')
            sys.exit(1)
    
    def get_poller_config(self):
        sql_query = sql_utils.sql_templates["poller_config"].value
        return self.conn.jinja_select_query(sql_query , {'poll_id' : self.poller_id})
    
    def get_selected_oid(self,id,device_model):
        oid_list = {"oid_list" :[]}
        oid_inner = dict()
        sql_query = sql_utils.sql_templates["oid_config"].value
        oid_raw = self.conn.jinja_select_query(sql_query, {'poll_id': id,'device_model': device_model} )
        for key,value in enumerate(oid_raw):
            oid_inner[value['oid_key']] = value['oid']
        oid_list['oid_list'] = [oid_inner]
        return oid_list

    def get_ip_address(self,table):
        ip_list = list()
        blacklist_list = self.conn.select_query("""SELECT ip_address from blacklist where snmp_poller_id = {0}""".format(self.poller_id)) 
        blist ="("
        for index,ip in enumerate(blacklist_list):
            if ((index +1) == len(blacklist_list)):
                blist+="'{0}'".format(ip["ip_address"])
            else:
                blist+="'{0}',".format(ip["ip_address"])
        blist+=")"
        if len(blacklist_list) >0:
            sqlquery = """SELECT ip_address from {0} where ip_address not in {1}""".format(table,blist)
        else:
            sqlquery = """SELECT ip_address from {0}""".format(table)
            
        raw_list = self.conn.select_query(sqlquery)
        if len(raw_list) > 0:
            for key,items in enumerate(raw_list):
                ip_list.append(items["ip_address"])
            return ip_list
        else:
            return (False)
    
    def push_to_normalize(self, source):
        try:
            payload = {
                'user': os.environ.get("DB_USER"),
                'password': os.environ.get("DB_PASSWORD"), 
                'dbname': os.environ.get("SNMPDB"), 
                'host': os.environ.get("DB_CONN"), 
                'port': os.environ.get("SNMP_DB_PORT"), 
                'table_name': source};
            resp = requests.put(os.environ.get("NORMALIZE_API"), json=payload, verify=False, timeout=5)
        except Exception as error:
            print(error)

    def insert_update(self,device_detail,table_name):
        ip_address = device_detail['ip_address']
        del device_detail['ip_address']

        placeholder = ', '.join('?' * len(device_detail))
        update_util = sql_utils.sql_templates["poll_update_up"].value

        update_query = update_util.format(
            table_name,
            ', '.join("{0}='{1}'".format(value,device_detail[value]) for key,value in enumerate(device_detail)),
            ip_address , 
            self.poller_id)
        

        self.conn.update_query(update_query)
        self.logger.log('Device Polled: {0}'.format(ip_address), 'INFO')

        try:
            self.push_to_normalize(table_name)
            # call_proc = '''DECLARE @ErrorMsg NVARCHAR(MAX)
            #             EXEC normalize_snmp_data @worker_table = '%s' ,@error_message = @ErrorMsg output
            #             Select @ErrorMsg
            #             GO''' % table_name
            # result = self.conn.call_proc(call_proc)
            # if result[0][0] and result[0][0] is not None:
            #     self.logger.log('An error has occured while executing stored procedure: {0}'.format(result[0][0]), 'CRITICAL')
            #     # self.update_worker_status(-1)
            #     # sys.exit()
        except Exception as err:
            self.logger.log('An error has occured while executing stored procedure: {0}'.format(err), 'CRITICAL')
            # self.update_worker_status(-1)
            # sys.exit()

    def exit_handler(self):
        if self.pid_util:
            if str(self.pid_util.read_pid()) == str(os.getpid()):
                try:
                    self.pid_util.delete_pid()
                except Exception as err:
                    self.logger.log(err, 'critical')       
                    
    def signal_handler(self, signum, frame):
        self.exit_handler()
        if self.logger:
            self.logger.log('Service stopped.')
        sys.exit(1)

    def create_directory(self, directory):
        if not os.path.exists(os.path.join(os.getcwd(), directory)):
            os.mkdir(os.path.join(os.getcwd(), directory))
            print(directory, 'Directory created.')

    def run(self):
        multiprocessing.freeze_support()
        self.create_directory(logs_directory)
        self.create_directory(pid_directory)
        poller_config = self.get_poller_config()
        
        if poller_config :
            poller_config = poller_config[0]
            subnet = poller_config["subnet"]
            community_string = poller_config["community_string"]
            interval = poller_config["interval"]
            table_name = poller_config["table_name"]
            poll_name = poller_config["poll_name"]
            self.logger = Logger(logs_directory, self.poller_id, table_name, 'snmp_poller_logs')
            self.pid_util = ProcessIdUtil(pid_directory, self.poller_id ,table_name,'snmp_poller',None)
            self.logger.config_logging()
            # print(self.pid_util.is_process_running())
            if self.pid_util.is_process_running():
                self.logger.log('Already running.')
                sys.exit(1)
            else:
                self.logger.log("[{0}] : Poller running...".format(poll_name))  
                self.poller_event(1)
                ip_list = self.get_ip_address(table_name)
                try:
                    self.pid_util.create_pid()
                    self.pid_util.save_pid()
                except Exception as err:
                    
                    self.logger.log(err, 'critical')
                    sys.exit(1)
                runner = True
                if ip_list == False:
                    print("No device selected")
                    return "No device selected"
                while runner:
                    # start
                    for ip_address in ip_list:
                        mdi_runner = main_device_info(ip_address , community_string)
                        mdi_output = mdi_runner.run()
                        if mdi_output["is_valid"]:
                            try:
                                mdi_data = mdi_output["main_info"] 
                                
                                for_mdd = self.get_selected_oid(self.poller_id,  mdi_data['device_model'])
                                mdd_runner = main_device_details(mdi_data["ip_address"] , for_mdd , community_string)
                                mdd_output = mdd_runner.run()
                          
                                mdd_output["ip_address"] = mdi_data["ip_address"]
                               
                                self.insert_update(mdd_output,table_name)
                            except Exception as err:
                                self.logger.log("[{0}] : Stopped due to an error : {1}".format(poll_name,err))
                                self.poller_event('-1')
                        else:
                            update_util = sql_utils.sql_templates["poll_update_down"].value
                            update_query = update_util.format(table_name,ip_address)
                            self.conn.update_query(update_query)
                            self.logger.log("[{0}] : No SNMP response for {1}".format(poll_name , ip_address))
                            self.push_to_normalize(table_name)
                            # try:
                            #     call_proc = '''DECLARE @ErrorMsg NVARCHAR(MAX)
                            #                 EXEC normalize_snmp_data @worker_table = '%s' ,@error_message = @ErrorMsg output
                            #                 Select @ErrorMsg
                            #                 GO''' % table_name
                            #     result = self.conn.call_proc(call_proc)
                            #     if result[0][0] and result[0][0] is not None:
                            #         self.logger.log('An error has occured while executing stored procedure: {0}'.format(result[0][0]), 'CRITICAL')
                            #         # self.update_worker_status(-1)
                            #         # sys.exit()\
                            # except Exception as err:
                            #     self.logger.log('An error has occured while executing stored procedure: {0}'.format(err), 'CRITICAL')   
                    self.logger.log('Sleeping for {0}(sec/s)'.format(interval), 'INFO')  
                    time.sleep(interval)
        else:
            print('Poller does not exist.')

if (len(sys.argv) < 2):
    print('Missing arguments. Run using command \'python <script filename> <poller_id>\'.')
elif (len(sys.argv) == 2):
    poller_id = sys.argv[1]
    poll_runner = start_polling(poller_id)
    poll_runner.run()
