import logging
import os

import azure.functions as func
import azure.mgmt.resourcegraph as graph
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import SubscriptionClient

from .graph_query import GraphQuery
from .loki import LokiPublisher, MAX_LABELS
from .azure_blob import AzurePublisher
from .azure_table import AzureTable

# default root level
logging.Logger.root.level = logging.DEBUG


def is_enabled(publisher_flag: str) -> bool:
    """
    Given the publisher flag returns True or False
    Args:
        publisher_flag: Flag containing string 'true'|'false'
    """
    if publisher_flag.lower() == "true":
        return True
    else:
        return False


def main(event: func.TimerRequest) -> None:
    logger = logging.getLogger("main")
    logger.info("Started main function")
    logger.debug(f"Event data: {event}")

    credentials = DefaultAzureCredential(
        managed_identity_client_id=os.environ.get("USER_ASSIGNED_IDENTITY_APP_ID", None)
    )

    rgraph_client = graph.ResourceGraphClient(credentials)

    # Get the query from the saved resource graph query
    resource_graph_queries = os.environ["RESOURCE_GRAPH_QUERY_IDS"].split(",")
    for query in resource_graph_queries:
        resource_graph_query = GraphQuery(query)
        logger.info(
            f"retrieving graph query from resource id: [{resource_graph_query.resource_id}]"
        )
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
        logger.info(f"Query results, total: {result.as_dict().get('total_records')}")
        logger.debug(f"Query results dump:\n---\n{result.as_dict()}\n---")

        # enrich result with data in Azure Table
        result_2publish = result.as_dict().get("data", [])
        for item in result_2publish:
            row_key = item["subscriptionId"]
            filter = f"RowKey eq '{row_key}'"
            azure_table = AzureTable()
            azure_table_entities = azure_table.query_entities(filter)
            pu = azure_table_entities[0]["PU"]
            techcontact = azure_table_entities[0]["techContact"]
            item["pu"] = pu
            item["techcontact"] = techcontact

        # publish to loki
        if is_enabled(os.environ.get("ENABLE_LOKI_PUBLISHER", "true")):
            loki_logger = LokiPublisher(
                loki_endpoint=os.environ["LOKI_ENDPOINT"],
                auth=(os.environ["LOKI_USERNAME"], os.environ["LOKI_PASSWORD"]),
                tags={
                    "inventory_type": "reference_architecture",
                    "graph_query_name": resource_graph_query.name,
                },
            )

            fields_to_labels_string = os.environ.get("LOKI_LABEL_NAMES", None)
            fields_to_labels = []
            if fields_to_labels_string:
                fields_to_labels = [
                    e.strip() for e in fields_to_labels_string.split(",")
                ]

            if len(fields_to_labels) > MAX_LABELS:
                raise ValueError(
                    f"A maximum of {MAX_LABELS} is supported. You requested: {len(fields_to_labels)} labels, "
                    f"namely: [{', '.join(fields_to_labels)}]"
                )

            for item in result_2publish:
                loki_logger.publish(item, fields_to_labels)

        # publish to Azure Blob container
        if is_enabled(os.environ.get("ENABLE_AZURE_BLOB_PUBLISHER", "false")):
            azure_publisher = AzurePublisher(
                connection_string=os.environ["STORAGE_ACCOUNT_CONNECTION"],
                container_name=os.environ["CONTAINER_NAME"],
            )
            azure_publisher.publish(
                name=resource_graph_query.name, data=result_2publish
            )
