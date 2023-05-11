import logging
import csv
import time

from azure.storage.blob import BlobServiceClient


class AzurePublisher(object):
    """
    A class to interact with Azure Storage Account Blob storage
    """

    def __init__(
        self,
        connection_string: str,
        container_name: str,
    ):
        """
        A high level convenience library to interact with the Azure Blob storage.

        Args:
            - connection_string: The Azure storage account connection string for accessing the containers.
            - container_name: The container's name for download/upload blobs.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.container_name = container_name
        self.connection_string = connection_string
        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string
        )
        self.container_client = self.blob_service_client.get_container_client(
            container=self.container_name
        )

    def publish(self, name: str, data: dict):
        """
        Create a CSV file given the name and data to persisted in an Azure blob container
        Args:
            - name: file's name to be created
            - data: file's content
        """
        filename = f"{name}-{time.strftime('%Y%m%d-%H%M%S')}.csv"
        rows = data
        with open(file=filename, mode="w", encoding="UTF8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys(), delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

        self.logger.info(
            f"Upload {filename} into Azure blob container: {self.container_name}"
        )
        with open(file=filename, mode="rb") as content:
            self.container_client.upload_blob(
                name=filename, data=content, overwrite=True
            )
