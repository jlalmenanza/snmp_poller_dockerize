from flask import jsonify
from flask import request
from flask_restful import Resource
from flask_restful import reqparse
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from backend_api.app.models.error_schema import ErrorObject
from backend_api.app.common.schema_builder import SchemaBuilder
from backend_api.app.common.api_utils import ApiUtils
from backend_api.app.common.db_utils import DatabaseUtils
from backend_api.app.models.snmp_poller import SnmpPoller
from backend_api.app.models.snmp_poller_schema import SnmpPollerSchema
from backend_api.app.models.blacklist import Blacklist
from backend_api.app.models.blacklist_schema import BlacklistSchema
from backend_api.app.models.selected_oid import SelectedOid
from backend_api.app.models.selected_oid_schema import SelectedOidSchema
from backend_api.app.common.service_manager import ServiceManager
from backend_api.app.models.ip_list_schema import IpListSchema
from backend_api.app import logger
from backend_api.app.api import db
from utils.database_util import DatabaseUtil
import json
import os
import ast




class SnmpPollerApi(Resource):

    api_utils = ApiUtils()
    db_utils = DatabaseUtils()
    db_util_raw = DatabaseUtil()

    main_model = SnmpPoller
    main_schema = SnmpPollerSchema
    service = ServiceManager(module_name='poller')

    module_name = 'SNMP Poller'

    def get(self, id=None, show=None, status=None):
        args = self.api_utils.optional_parameters()
        try:
            poller_session = self.db_utils.model_session(self.main_model)
            if id is not None: 
                poller_session = poller_session.filter(self.main_model.id==id)
            poller_session = poller_session.order_by(self.main_model.id.desc()).all()

            schema_option = self.api_utils.schema_options(self.main_schema,args['columns'])
            poller_result = self.main_schema(**schema_option).dump(poller_session)
            poller_result = self.api_utils.get_paginated_list(poller_result, args['start'], args['limit'])
            
           
            for poller_element in poller_result:
                poller_element['extractor'] = [{"source": "SNMP"}]
                if 'blacklist' in args['include']:
                    blacklist = self.db_utils.select_with_filter(Blacklist, BlacklistSchema, 
                            {'snmp_poller_id': poller_element['id']})  
                    poller_element['blacklist'] = blacklist

                if 'selected_oid' in args['include']:
                    selected_oid = self.db_utils.select_with_filter(SelectedOid, SelectedOidSchema, 
                            {'snmp_poller_id': poller_element['id']})
                    poller_element['selected_oid'] = selected_oid
                    
                if 'selected_ips' in args['include']:
                    conn = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"),os.environ.get("SNMP_DB_PORT"))
                    query_string = "Select {0}_id,ip_address,system_description,system_name,device_model from {0}".format(poller_element["table_name"])     
                    result = conn.select_query(query_string)
                    poller_element['selected_ip'] = result

            return {'data': poller_result}, 200
        except Exception as err:
            logger.log("Error encountered on Poller : %s" % str(err), log_type='ERROR')
            return eval(str(err)), 422
        finally:
            db.session.close()
            db.engine.dispose()
            
    def post(self):
        conn = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"),os.environ.get("SNMP_DB_PORT"))
        args = self.api_utils.parameters(self.main_model(), blacklist="append", selected_oid="append", ip_list="append")
        list_of_ids = {}
        try:
            blacklist = list(eval(items) for items in list(args['blacklist']))
            selected_oid = list(filter(None, args['selected_oid'])) 
            ip_list = list(eval(items) for items in list(args['ip_list']))

            del args['ip_list']
            del args['blacklist']   
            del args['selected_oid']
        
            SnmpPollerSchema().load(args)
            if (selected_oid and ip_list)  and self.api_utils.ip_validator(ip_list)  and self.api_utils.ip_validator(blacklist) and self.api_utils.oid_validator(conn,selected_oid) :
                args["table_name"] = "snmp_{0}".format(args['table_name'])
                poller_data = self.main_schema().load(args)
                poller_result = self.db_utils.insert_data(self.module_name,self.main_model, poller_data, commit=True)
                list_of_ids['snmp_poller'] = poller_result

                for ip_data in ip_list:
                    IpListSchema().load(ip_data)

                if blacklist is not None:
                    for blacklist_element in blacklist:
                        blacklist_obj = {}
                        blacklist_obj['ip_address'] = blacklist_element['ip_address']
                        blacklist_obj['snmp_poller_id'] = poller_result
                        blacklist_obj['system_description'] = blacklist_element['system_description']
                        blacklist_obj['system_name'] = blacklist_element['system_name']
                        blacklist_obj['device_model'] = blacklist_element['device_model']
                        blacklist_data = BlacklistSchema().load(blacklist_obj)
                        blacklist_result = self.db_utils.insert_data(self.module_name, Blacklist, blacklist_data, commit=True)
                        list_of_ids['blacklist'] = blacklist_result

                if selected_oid is not None:    
                    for selected_oid_element in selected_oid:
                        selected_oid_obj = {}
                        selected_oid_obj['oid_key'] = selected_oid_element
                        selected_oid_obj['snmp_poller_id'] = poller_result
                        selected_oid_data = SelectedOidSchema().load(selected_oid_obj)
                        selected_oid_result = self.db_utils.insert_data(self.module_name, SelectedOid, selected_oid_data, commit=True)
                        list_of_ids['selected_oid'] = selected_oid_result
                oid_raw  = conn.select_query('Select oid_key from oid_list group by oid_key')
                oid_main = [oid['oid_key'] for oid in oid_raw]
                oid_main.extend(['ip_address', 'status','device_model','system_description','system_name'])
                # args['table_name'] = "snmp_{0}".format(args['table_name'])
                SchemaBuilder(args['table_name'], fields=oid_main).create_table(default_date=True)
                SchemaBuilder().create_data_retention(args['table_name'])
               

                conn = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"),os.environ.get("SNMP_DB_PORT"))
                query_string = 'INSERT INTO {0} (ip_address,system_description,device_model,system_name) values ({1})' .format(args['table_name'], '%(ip_address)s,%(system_description)s,%(device_model)s ,%(system_name)s')   
                conn.insert_many_query(query_string, ip_list)

                args['snmp_poller_id'] = poller_result

               
                logger.log("Inserted data to SNMP Poller. Status CREATED 201")
                return {'message': 'Successfully added.', 'snmp_poller_payload': args}, 201
            else:
                return {'message': 'Payload verification failed.', 'snmp_poller_payload': args}, 422
            
        except ValidationError as value_error:
            logger.log("Validation encountered on SNMP poller table: %s" % (str(value_error)), log_type='ERROR')
            self.db_utils.data_rollback(list_of_ids)
            return {'lists': value_error.messages, 'type': 'ValidationError', 'message': 'Validation errors in your request'}, 422
        except Exception as err:
            logger.log("Error encountered on SNMP poller : %s" % str(err), log_type='ERROR')
            self.db_utils.data_rollback(list_of_ids)
            return eval(str(err)), 422
    # def post(self):
    #     conn = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"),os.environ.get("SNMP_DB_PORT"))
    #     args = self.api_utils.parameters(self.main_model(), blacklist="append", selected_oid="append", ip_list="append")
    #     list_of_ids = {}
    #     try:
    #         blacklist = list(eval(items) for items in list(args['blacklist']))
    #         selected_oid = list(filter(None, args['selected_oid'])) 
    #         ip_list = list(eval(items) for items in list(args['ip_list'])) 
    #         del args['ip_list']
    #         del args['blacklist']   
    #         del args['selected_oid']
        
    #         SnmpPollerSchema().load(args)
    #         if (selected_oid and ip_list)  and self.api_utils.ip_validator(ip_list)  and self.api_utils.ip_validator(blacklist) and self.api_utils.oid_validator(conn,selected_oid) :
    #             poller_data = self.main_schema().load(args)
    #             poller_result = self.db_utils.insert_data(self.module_name,self.main_model, poller_data, commit=True)
    #             list_of_ids['snmp_poller'] = poller_result

    #             if blacklist is not None:
    #                 for blacklist_element in blacklist:
    #                     blacklist_obj = {}
    #                     blacklist_obj['ip_address'] = blacklist_element['ip_address']
    #                     blacklist_obj['snmp_poller_id'] = poller_result
    #                     blacklist_obj['system_description'] = blacklist_element['system_description']
    #                     blacklist_obj['system_name'] = blacklist_element['system_name']
    #                     blacklist_data = BlacklistSchema().load(blacklist_obj)
    #                     blacklist_result = self.db_utils.insert_data(self.module_name, Blacklist, blacklist_data, commit=True)
    #                     list_of_ids['blacklist'] = blacklist_result

    #             if selected_oid is not None:    
    #                 for selected_oid_element in selected_oid:
    #                     selected_oid_obj = {}
    #                     selected_oid_obj['oid_key'] = selected_oid_element
    #                     selected_oid_obj['snmp_poller_id'] = poller_result
    #                     selected_oid_data = SelectedOidSchema().load(selected_oid_obj)
    #                     selected_oid_result = self.db_utils.insert_data(self.module_name, SelectedOid, selected_oid_data, commit=True)
    #                     list_of_ids['selected_oid'] = selected_oid_result
    #             oid_raw  = conn.select_query('select oid_key from oid_list group by oid_key')
    #             oid_main = [oid['oid_key'] for oid in oid_raw]
    #             oid_main.extend(['ip_address', 'status','device_model','system_description','system_name'])
    #             SchemaBuilder(args['table_name'], fields=oid_main).create_table(default_date=True)
    #             SchemaBuilder().create_data_retention(args['table_name'])

    #             conn = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"),os.environ.get("SNMP_DB_PORT"))
    #             query_string = 'INSERT INTO {0} (ip_address,system_description,device_model,system_name) values ({1})' .format(args['table_name'], '%(ip_address)s,%(system_description)s,%(device_model)s ,%(system_name)s')   
    #             conn.insert_many_query(query_string, ip_list)

    #             args['snmp_poller_id'] = poller_result
    #             logger.log("Inserted data to SNMP Poller. Status CREATED 201")
    #             return {'message': 'Successfully added.', 'snmp_poller_payload': args}, 201
    #         else:
    #             return {'message': 'Payload verification failed.', 'snmp_poller_payload': args}, 422
            
    #     except ValidationError as value_error:
    #         logger.log("Validation encountered on SNMP poller table: %s" % (str(value_error)), log_type='ERROR')
    #         self.db_utils.data_rollback(list_of_ids)
    #         return {'lists': value_error.messages, 'type': 'ValidationError', 'message': 'Validation errors in your request'}, 422
    #     except Exception as err:
    #         logger.log("Error encountered on SNMP poller : %s" % str(err), log_type='ERROR')
    #         self.db_utils.data_rollback(list_of_ids)
    #         return eval(str(err)), 422


    # edit
    
    def put(self , id = None):
        args = self.api_utils.parameters(self.main_model(), blacklist="append", selected_oid="append", ip_list="append")
        poller_id = id
        conn = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"),os.environ.get("SNMP_DB_PORT"))
        poll_data = conn.select_query('Select status from snmp_poller where id = {0}'.format(poller_id))
        if not poll_data:
            return {'message': "ID doesn't exist", "type": "ReferenceError"}, 422
            
        poll_status = poll_data[0]['status']
        list_of_ids = {}
        
        if poll_status != 1:
            try:
                blacklist = list(eval(items) for items in list(args['blacklist']))
                selected_oid = list(filter(None, args['selected_oid'])) 
                ip_list = list(eval(items) for items in list(args['ip_list'])) 
                del args['ip_list']
                del args['blacklist']   
                del args['selected_oid']
                SnmpPollerSchema().load(args)
                if (selected_oid and ip_list)  and self.api_utils.ip_validator(ip_list)  and self.api_utils.ip_validator(blacklist) and  self.api_utils.oid_validator(conn,selected_oid) :    
                    if blacklist is not None:
                        self.db_utils.delete_data_using_id(Blacklist, {'snmp_poller_id': poller_id})
                        for blacklist_element in blacklist:
                            blacklist_obj = {}
                            blacklist_obj['ip_address'] = blacklist_element['ip_address']
                            blacklist_obj['system_description'] = blacklist_element['system_description']
                            blacklist_obj['system_name'] = blacklist_element['system_name']
                            blacklist_obj['device_model'] = blacklist_element['device_model']
                            blacklist_obj['snmp_poller_id'] = poller_id
                            blacklist_data = BlacklistSchema().load(blacklist_obj)
                            blacklist_result = self.db_utils.insert_data(self.module_name, Blacklist, blacklist_data, commit=True)
                            list_of_ids['blacklist'] = blacklist_result

                    if selected_oid is not None: 
                        self.db_utils.delete_data_using_id(SelectedOid, {'snmp_poller_id': poller_id})
                        for selected_oid_element in selected_oid:
                            selected_oid_obj = {}
                            selected_oid_obj['oid_key'] = selected_oid_element
                            selected_oid_obj['snmp_poller_id'] = poller_id
                            selected_oid_data = SelectedOidSchema().load(selected_oid_obj)
                            selected_oid_result = self.db_utils.insert_data(self.module_name, SelectedOid, selected_oid_data, commit=True)
                            list_of_ids['selected_oid'] = selected_oid_result
                    
                    if ip_list is not None:
                        table_name = conn.select_query('Select table_name from snmp_poller where id = %s ' % (poller_id))[0]
                        new_table_name = table_name["table_name"]
                        conn.truncate_table('Truncate table %s ' % (new_table_name))
                        query_string = 'INSERT INTO {0} (ip_address,system_description,device_model,system_name) values ({1})' .format(new_table_name, '%(ip_address)s,%(system_description)s,%(device_model)s ,%(system_name)s')   
                        conn.insert_many_query(query_string, ip_list)
                    
                    del args['table_name']
                    args['status'] = 0
                    args['pid'] = 0


                    self.db_utils.update_data(self.main_model, {'id': poller_id}, args, commit=True)
                    args['snmp_poller_id'] = poller_id
                    logger.log("Update SNMP Poller. Status Succesful 200")
                    return {'message': 'Update Successful.', 'snmp_poller_payload': args}, 200
                    
                else:
                    return {'message': 'Payload verification failed.', 'snmp_poller_payload': args}, 422

            except ValidationError as value_error:
                logger.log("Validation encountered on SNMP poller table: %s" % (str(value_error)), log_type='ERROR')
                self.db_utils.data_rollback(list_of_ids)
                return {'lists': value_error.messages, 'type': 'ValidationError', 'message': 'Validation errors in your request'}, 422
            except Exception as err:
                logger.log("Error encountered on SNMP poller : %s" % str(err), log_type='ERROR')
                self.db_utils.data_rollback(list_of_ids)
                return eval(str(err)), 422
        else:
            return {'message': "Update unsuccessfull. Poller is running." } ,422

    
    def delete(self, id=None):
        try:

            get_table_name = None
            poller = self.db_utils.select_with_filter(self.main_model, self.main_schema, {'id': id})
            
            if poller: 
                # poller_tasklist = self.service.check_service(poller[0]['pid'], 'poller.exe')
                # poller_tasklist = self.service.check_service(poller[0]['pid'], 'poller.py')
                # print(poller_tasklist)
                # if 'image name' in str(poller_tasklist.decode("utf-8")).lower():
                #     raise ValueError(ErrorObject(type="ServiceError", 
                #             message="Poller is running.").to_json())
                
                delete_status = self.db_utils.delete_data_using_id(SnmpPoller, {'id': id})

                get_table_name = poller[0]['table_name']
                self.db_utils.drop_table(get_table_name)
                logger.log("Deleting the data on SNMP Poller, id : {0}",format(id))
                return {'message': "Successfully deleted."}, 200
            else:
                logger.log("Encountered error on poller: ID doesn't exist", log_type='ERROR')
                return {'message': "ID doesn't exist", "type": "ReferenceError"}, 422
        except Exception as err:
            logger.log("Error encountered on SNMP Poller : %s" % str(err), log_type='ERROR')
            return eval(str(err)), 422