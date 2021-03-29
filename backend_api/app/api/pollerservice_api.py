from flask_restful import Resource
from flask_restful import reqparse
from backend_api.app.api import db
from backend_api.app.common.api_utils import ApiUtils
from backend_api.app.common.db_utils import DatabaseUtils
from backend_api.app.models.snmp_poller import SnmpPoller
from backend_api.app.models.snmp_poller_schema import SnmpPollerSchema
from backend_api.app.models.snmppoller_logs import SnmpPollerLogs
from backend_api.app.models.snmppoller_logs_schema import SnmpPollerLogsSchema
from backend_api.app.common.service_manager import ServiceManager
from flask_jwt_extended import jwt_required
from backend_api.app import logger
import subprocess


class PollerService(Resource):

    db_utils = DatabaseUtils()
    api_utils = ApiUtils()
    service = ServiceManager(module_name='poller')

    main_model = SnmpPoller
    main_schema = SnmpPollerSchema
    
    def get(self, id=None, log='logs', level=None):
        args = self.api_utils.optional_parameters()
        try:
            if id is None:
                logger.log("Encountered error on poller service: ID is invalid", log_type='ERROR')
                return {'message': "ID doesn't exist", "type": "ReferenceError"}, 422
            logs = db.session.query(SnmpPollerLogs).filter(SnmpPollerLogs.snmp_poller_id==id)
            if level is not None:
                logs = logs.filter(SnmpPollerLogs.log_level==level)
                logger.log("Retrieving data from poller logs with filter : level %s" % (level))

            if args['start'] != 1 or args['limit'] != 0:
                logs = logs.order_by(SnmpPollerLogs.id.asc()).paginate(args['start'],args['limit'], False).items
                logger.log("Retrieving data from poller logs with paginate : start %s and limit %s" % (args['start'], args['limit']))
            else:
                logs = logs.order_by(SnmpPollerLogs.id.desc()).all()
                logger.log("Retrieving data from poller logs. Status OK 200")

            logs_data = SnmpPollerLogsSchema(many=True).dump(logs)
            return {'data': logs_data}, 200
        except Exception as err:
            pass
        finally:
            db.session.close()
            db.engine.dispose()
    
        
    def put(self, id=None):
        try:
            get_poller_service = self.db_utils.select_with_filter(self.main_model, self.main_schema, {'id': id})

            if (id is None) or (len(get_poller_service) == 0):
                logger.log("Encountered error on poller service: ID is invalid", log_type='ERROR')
                return {'message': "ID doesn't exist", "type": "ReferenceError"}, 422

            check_service = self.service.check_service(pid=get_poller_service[0]['pid'], file_name='poller.py')
            if check_service:
                logger.log("Encountered error on poller service: Poller service is already running", log_type='ERROR')
                return {'message': "Poller service is already running", "type": "ServiceError"}, 422
            else:
                # self.service.start_service(id, 'aggregate.exe')
                self.service.start_service(id, 'poller.py')

            logger.log("Starting the Service : ({0}) Service is running".format(id))
            return {'message': 'Poller service started.'}, 200
            
        except Exception as err:
            logger.log("Encountered error on poller service : %s" % (str(err)))
            return eval(str(err)), 422
    
    def delete(self, id=None):
        try:
            if id is None:
                logger.log("Encountered error on poller service: ID doesn't exist", log_type='ERROR')
                return {'message': "ID doesn't exist", "type": "ReferenceError"}, 422
            get_pid = self.db_utils.select_with_filter(self.main_model,self.main_schema, {'id': id})
            process = self.service.stop_service(pid=get_pid[0]['pid'])
            self.db_utils.update_data(SnmpPoller, {'id': id}, {'status': 0, 'pid': 0}, commit=True)
            logger.log("Stopped the poller service : (%s) %s" % (id,process))
            return {'message': process}
        except Exception as err:
            logger.log("Encountered error on poller service :(%s) %s" % (id,err), log_type='ERROR')
            return eval(str(err)), 422