from backend_api.app.api import api



from backend_api.app.api.snmppoller_api import SnmpPollerApi
from backend_api.app.api.pollerservice_api import PollerService
from backend_api.app.api.blacklist_api import BlacklistApi
from backend_api.app.api.oid_api import OidApi
from backend_api.app.api.datapolling_api import DataPollingApi
from backend_api.app.api.poller_data import PollerData
from backend_api.app.api.poller_status import PollerStatus

from backend_api.app.api.networkdiscovery_api import NetworkDiscovery


api.add_resource(SnmpPollerApi, '/snmp/snmp/poller', '/snmp/snmp/poller/<int:id>')
api.add_resource(PollerService, '/snmp/poller/service', '/snmp/poller/service/<int:id>', 
    '/snmp/poller/service/<int:id>/logs', '/snmp/poller/service/<int:id>/logs/<string:level>')
api.add_resource(BlacklistApi, '/snmp/blacklist')
api.add_resource(OidApi, '/snmp/oid')
api.add_resource(NetworkDiscovery, '/snmp/network/discovery')
api.add_resource(DataPollingApi, '/snmp/data/view/polling')
api.add_resource(PollerData, '/snmp/poller/data', '/snmp/poller/data/<string:table_name>')
api.add_resource(PollerStatus, '/snmp/poller/status', '/snmp/poller/status/<string:table_name>')

