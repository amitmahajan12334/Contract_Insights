from azure.storage.blob import ContainerClient
from io import BytesIO

def download_pdf_from_blob(connection_string, container_name, blob_name):
    # Connect to the Blob Service
    blob_service_client = ContainerClient.from_connection_string(connection_string,container_name)
    blob_client = blob_service_client.get_blob_client( blob=blob_name)
    
    # Download the blob to an in-memory bytes buffer
    pdf_data = BytesIO()
    pdf_data.write(blob_client.download_blob().readall())
    pdf_data.seek(0)  # Reset buffer to the beginning
    return pdf_data