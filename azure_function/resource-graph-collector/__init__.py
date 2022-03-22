import logging
import os

import azure.functions as func
import azure.mgmt.resourcegraph as graph
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import SubscriptionClient

from .graph_query import GraphQuery
from .loki import LokiPublisher


def main(event: func.TimerRequest) -> None:
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('main')
    logger.info("Started main function")
    logger.info(f"Event data: {event}")

    credentials = DefaultAzureCredential(
        managed_identity_client_id=os.environ.get('USER_ASSIGNED_IDENTITY_APP_ID', None))

    rgraph_client = graph.ResourceGraphClient(credentials)

    # Get the query from the saved resource graph query
    resource_graph_query = GraphQuery(os.environ['RESOURCE_GRAPH_QUERY_ID'])
    logger.info(f"retrieving graph query from resource id: [{resource_graph_query.resource_id}]")
    query = resource_graph_query.with_graph_client(rgraph_client).get_query()
    logger.debug(f"loaded query:\n---\n{query}\n---")

    # build a list of applicable subscription ids
    subs_client = SubscriptionClient(credentials)
    subs_ids = [elem.subscription_id for elem in subs_client.subscriptions.list()]
    logger.info(f"target subscriptions total: {len(subs_ids)}")
    logger.debug(f"target subscriptions dump: {subs_ids}")

    # build the query
    gquery = graph.models.QueryRequest(subscriptions=subs_ids, query=query)
    result = rgraph_client.resources(gquery)
    logger.info(f"Query results, total: {result.as_dict().get('total_records')}:\n---\n{result.as_dict()}\n---")
    logger.debug(f"Query results dump:\n---\n{result.as_dict()}\n---")

    # publish to loki
    loki_logger = LokiPublisher(loki_endpoint=os.environ['LOKI_ENDPOINT'],
                                auth=(os.environ['LOKI_USERNAME'], os.environ['LOKI_PASSWORD']),
                                tags={'inventory_type': 'reference_architecture',
                                      'graph_query_name': resource_graph_query.name})
    for item in result.as_dict().get('data', []):
        loki_logger.publish(item)
