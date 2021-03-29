import sys
import os
from utils.database_util import DatabaseUtil
import psutil

class ProcessIdUtil():
    def __init__(self, pid_directory, id, module_name, table_name, logger):
        self.pid_directory = pid_directory
        self.id = id
        self.module_name = module_name.replace(' ', '_').lower()
        self.table_name = table_name
        self.logger = logger
        self.conn = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"),os.environ.get("SNMP_DB_PORT"), self.logger)

    def create_directory(self):
        if not os.path.exists(os.path.join(os.getcwd(), self.pid_directory)):
            os.mkdir(os.path.join(os.getcwd(), self.pid_directory))
            print(self.pid_directory, 'created.')
    
    def create_pid(self):
        try:
            with open(os.path.join(os.getcwd(), self.pid_directory, str(self.module_name) + '.pid'), 'w') as file:
                file.write(str(os.getpid()))
        except Exception as err:
            raise ValueError(
                "Error encountered in creating PID: %s" % (err))

    def read_pid(self):
        try: 
            f = open(os.path.join(os.getcwd(), self.pid_directory, str(self.module_name) + '.pid'), 'r')
            contents = f.read()
            f.close()
            return contents
        except FileNotFoundError:
            return False

    def delete_pid(self):
        try:
            os.remove(os.path.join(os.getcwd(), self.pid_directory, str(self.module_name) +'.pid'))
        except Exception as err:
            raise ValueError(
                "Error encountered in deleting PID: %s" % (err))

    def save_pid(self, pid=None):
        try:
            if pid:
                query_string = 'UPDATE {0} SET pid = {1} WHERE id = {2}'.format(self.table_name, pid, self.id)
            else:
                query_string = 'UPDATE {0} SET pid = {1} WHERE id = {2}'.format(self.table_name, os.getpid(), self.id)
            self.conn.insert_query(query_string)
        except Exception as err:
            raise ValueError(
                "Error encountered in creating PID: %s" % (err))

    def get_pid(self):
        try:
            query_string = 'SELECT pid FROM {0} WHERE id = {1}'.format(self.table_name, self.id)
            pid = self.conn.select_query(query_string)
            return pid[0]['pid']
        except Exception as err:
            raise ValueError(
                "Error encountered in getting PID: %s" % (err))

    def is_pid_running(self, pid):
        # services = ['worker.exe', 'aggregate.exe','visionapi.exe']
        # services = ['worker.py', 'aggregate.py', 'VisionAPI.py', 'poller.py']
        # check if pid exists
        
        # if psutil.pid_exists(pid):
        #     process = psutil.Process(pid)
        #     if process.name() == 'python' and (process.cmdline()[1] and process.cmdline()[1] in services):
        #         return True
        
        # if pid does not exist, check if command exists
        # for process in psutil.process_iter():
        #     try:
        #         if len(process.cmdline()) == 3:
        #             if process.name() == 'python' and (process.cmdline()[1] and process.cmdline()[1] in services) and process.cmdline()[2] == self.id:
        #                 if process.pid != os.getpid():
        #                     self.save_pid(process.pid)
        #                     return True
        #     except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        #         pass

        return False

    def is_process_running(self):
        db_pid = self.get_pid()
        db_pid_running = self.is_pid_running(db_pid)
        
        if self.read_pid():
            file_pid = int(self.read_pid())
            file_pid_running = self.is_pid_running(file_pid)
        
            if file_pid_running and db_pid_running:
                return True
        else:
            if db_pid_running:
                return True

        return False

    def is_process_running_without_db(self):
        
        if self.read_pid():
            file_pid = int(self.read_pid())
            file_pid_running = self.is_pid_running(file_pid)
            if file_pid_running:
                return True
        return False

