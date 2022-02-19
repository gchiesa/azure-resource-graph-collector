import logging

import azure.mgmt.resourcegraph as graph
from msrestazure.tools import parse_resource_id, is_valid_resource_id


class GraphQuery(object):
    query_template = '''resources
                    | where type == "microsoft.resourcegraph/queries"
                    | where subscriptionId == "{subscription_id}"
                    | where resourceGroup == "{resource_group}"
                    | where name == "{resource_graph_query_name}"
                    '''

    def __init__(self, resource_id: str):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.resource_id = resource_id
        self.client = None
        self._validate_resource_id()

    def _validate_resource_id(self):
        if not is_valid_resource_id(self.resource_id):
            raise ValueError(f"invalid resource id: [{self.resource_id}]")
        meta = parse_resource_id(self.resource_id)
        if meta.get('resource_namespace', '') != 'Microsoft.ResourceGraph' or meta.get('resource_type',
                                                                                       '') != 'queries':
            raise ValueError(f"invalid resource metadata, expected ResourceGraph/queries, got instead: {meta}")

    def with_graph_client(self, graph_client: graph.ResourceGraphClient):
        self.client = graph_client
        return self

    def get_query(self) -> str:
        meta = parse_resource_id(self.resource_id)
        self.logger.debug(f"Query metadata: {meta}")
        query: str = self.query_template.format(subscription_id=meta['subscription'],
                                                resource_group=meta['resource_group'],
                                                resource_graph_query_name=meta['resource_name'])
        if not self.client:
            raise RuntimeError(f"please use with_graph_client before to set the client first")

        self.logger.debug(f"Performing query:\n---\n{query}\n---")
        graph_query = graph.models.QueryRequest(subscriptions=[meta['subscription']], query=query)
        result = self.client.resources(graph_query)
        return result.data[0]['properties']['query']
