from backend_api.app.api import db
from backend_api.app.common.db_utils import DatabaseUtils
from backend_api.app.models.error_schema import ErrorObject
from utils.database_util import DatabaseUtil
from backend_api.app import logger
import os



class SchemaBuilder(DatabaseUtils):
    
    def __init__(self, table_name=None,orig_table_name=None,fields=[], default=[]):
        self.orig_table_name = orig_table_name
        self.table = table_name
        self.fields = fields
        self.default = default
        self.db_util = DatabaseUtil(os.environ.get("DB_CONN"), os.environ.get("DB_USER"), 
            os.environ.get("DB_PASSWORD"), os.environ.get("SNMPDB"),os.environ.get("SNMP_DB_PORT"))


    def create_table(self,default_date=False,show_datetime=True, agg_type=None, status_id=False, normalize_status_id=False, source_ref=False, date_dim=False, date_dim_name='date_dimension_id'):
        datetime = ""
        status_field = ""
        normalize_status_field = ""
        source_fields = ""
        date_dim_field = ""
        fk = ""
        columns = []

        if show_datetime:
            if default_date:
                datetime = "datetime timestamp  without time zone NOT NULL DEFAULT (current_timestamp AT TIME ZONE 'UTC'),"
                columns.append("datetime timestamp  without time zone NOT NULL DEFAULT (current_timestamp AT TIME ZONE 'UTC'),")
            else:
                datetime = 'datetime timestamp,'
                columns.append('datetime timestamp')
            

        if status_id:
            status_field = "%s_status_id VARCHAR(50) DEFAULT '0'," % (str(self.table).lower())
            columns.append( "%s_status_id VARCHAR(50) DEFAULT '0'" % (str(self.table).lower()))
        
        if normalize_status_id:
            normalize_status_field = "%s_normalize_status_id VARCHAR(50) DEFAULT '0'," % (str(self.table).lower())
            columns.append("%s_normalize_status_id VARCHAR(50) DEFAULT '0'" % (str(self.table).lower()))



        if agg_type is not None:
            if agg_type != 'current':
                fk = '{0}_id INT FOREIGN KEY REFERENCES {0}_current({0}_current_id),'.format(self.orig_table_name)
                columns.append('{0}_id INT FOREIGN KEY REFERENCES {0}_current({0}_current_id)'.format(self.orig_table_name))


        if source_ref:
            source_fields = "source_id INT NULL, \
                source_table varchar(255), \
                {0} INT FOREIGN KEY REFERENCES date_dimension(date_id),".format(date_dim_name)
            columns.append( "source_id INT NULL, \
                source_table varchar(255), \
                {0} INT FOREIGN KEY REFERENCES date_dimension(date_id)".format(date_dim_name))
            
                
        if date_dim:
            date_dim_field = "{0} INT FOREIGN KEY REFERENCES date_dimension(date_id),".format(date_dim_name)
            columns.append( "{0} INT FOREIGN KEY REFERENCES date_dimension(date_id)".format(date_dim_name))


        try:
            sql = """
                CREATE TABLE %s 
                    ( %s_id SERIAL PRIMARY KEY,
                        %s %s %s )
                """ % (self.table,
                str(self.table).lower(),
                ''.join('{} VARCHAR(255) NULL,'.format(field) for field in self.fields),
                ''.join('{0}_{1} VARCHAR(255) NULL,'.format(str(self.table).lower(),default) for default in self.default),
                ','.join(columns))
            self.execute_raw_query(sql)
            return True
        except Exception as err:
            raise ValueError(ErrorObject(type="TableError", message="Encountered error while creating table.").to_json())

    # def create_trigger(self, data):
    #     sql = """
    #         CREATE TRIGGER trigger_{0} ON  
    #         {1} AFTER INSERT AS BEGIN
    #         INSERT INTO {2} ({3}, {2}_source, source_id, source_table)
    #         SELECT {4}, '{5}', {1}_id, '{1}'
    #         FROM {1} as t1 WITH (NOLOCK)
    #         WHERE not exists (select * from {2} as t2 
    #             where t1.{1}_id = t2.source_id and t2.source_table = '{1}')
    #         WAITFOR DELAY '00:00:01'
    #         UPDATE {2} SET [date_dimension_id] = (SELECT date_id FROM date_dimension 
    #         WHERE datetime = cast({2}.datetime as date)) WHERE date_dimension_id IS NULL;

    #         WAITFOR DELAY '00:00:01'
    #         END;
    #     """.format(
    #             data['trigger_name'],
    #             data['table'],
    #             data['destination_table'],
    #             ','.join('{}'.format(dest) for dest in data['destination']),
    #             ','.join('{}'.format(targ) for targ in data['target']),
    #             data['source']
    #         )
    #     try:
    #         self.execute_raw_query(sql)
    #     except Exception as error:
    #         logger.log(sql)
    #         logger.log("Encountered error : %s" % (str(error)), log_type='ERROR')
    #         self.drop_trigger(data['trigger_name'])
    #         raise ValueError(ErrorObject(type="StoredProcedureError", message="Please check the target tables and fields").to_json())

    
    def create_data_retention(self, table_name, retention=30):


        sql = """CREATE FUNCTION delete_old_{0}() RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                DELETE FROM {0} WHERE datetime < NOW() - INTERVAL '{1} days'; RETURN NULL; END; $$;

                CREATE TRIGGER trigger_delete_{0}
                    AFTER INSERT ON {0}
                    EXECUTE PROCEDURE delete_old_{0}(); """.format(table_name, retention)

        try:
            self.execute_raw_query(sql)
        except Exception as error:
            logger.log("Encountered error : %s" % (error), log_type='ERROR')
            self.drop_trigger('data_retention_{0}'.format(table_name))
            raise ValueError(ErrorObject(type="StoredProcedureError", message="Please check the target tables and fields").to_json())

        

    def insert_into_select(self, data):
        sql = """
                INSERT INTO %s (%s, [source])
                SELECT %s, '%s' FROM %s
            """  % (data['destination_table']
             ,','.join('[{}]'.format(dest) for dest in data['destination'])
             ,','.join('[{}]'.format(targ) for targ in data['target'])
             ,data['table'])
        try:
            self.execute_raw_query(sql)
        except Exception as error:
            raise ValueError("Error on inserting raw data to normalize table")