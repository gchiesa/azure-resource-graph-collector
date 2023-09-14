import os
from csv import DictReader
from azure.data.tables import TableClient
from azure.core.exceptions import ResourceExistsError, HttpResponseError


class AzureTable(object):
    def __init__(self):
        self.connection_string = os.getenv("STORAGE_ACCOUNT_CONNECTION")
        self.table_name = os.getenv("TABLE_NAME")
        self.table_is_created = False

    def create_entity(self, entity):
        with TableClient.from_connection_string(
            self.connection_string, self.table_name
        ) as table_client:
            if not self.table_is_created:
                try:
                    table_client.create_table()
                except HttpResponseError:
                    self.table_is_created = True
                    print("Table already exists")
            try:
                resp = table_client.create_entity(entity=entity)
                print(resp)
            except ResourceExistsError:
                print("Entity already exists")

    def query_entities(self, filter):
        with TableClient.from_connection_string(
            self.connection_string, self.table_name
        ) as table_client:
            try:
                return list(table_client.query_entities(filter))
            except HttpResponseError as e:
                raise
