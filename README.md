# Contract Insights
Contract Insights is an application designed to process PDF documents, particularly contracts, by leveraging Azure Blob Storage and OpenAI API services. The application extracts content from contract documents, generates questions and answers, and provides insights that facilitate document analysis and understanding.

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Running the Application](#running-the-application)
  - [PDF Processing](#pdf-processing)
  - [Azure Blob Storage Management](#azure-blob-storage-management)
  - [Generating Insights from Contracts](#generating-insights-from-contracts)
  - [Insights Evaluations](#insights-evaluations)
- [File Structure](#file-structure)


## Features
- **Document Uploading**: Seamlessly upload PDF contracts to Azure Blob Storage.
- **PDF Content Extraction**: Extracts text, images, and metadata from PDF files.
- **Insight Generation**: Uses OpenAI's API to analyze and generate questions and answers based on document content.
- **Azure Integration**: Manages PDF storage in Azure Blob Storage for scalable storage and retrieval.


## Prerequisites
To run this application, ensure you have the following:
- **Python 3.8+**
- **Azure Account**: Azure Blob Storage to store PDF documents.
- **OpenAI API Key**: For document insights and Q&A generation.
- **Python Packages**: Listed in `requirements.txt` and installed with `pip`.


## Installation

### 1. Clone or download the Repository
Clone the project repository to your local machine.
```bash
Not available
```
### 2. install the required Python packages
Use the requirements.txt file to install the required Python packages.
`pip install -r requirements.txt`.


## Configuration
Update the configuration file `config.yaml` to add your Azure Blob Storage and OpenAI API credentials.


## Usage
Run the main application file to start the service: `python app.py`


## File Structure
Below is an overview of each core file and its purpose within the project:

- **app.py**: Main application file that orchestrates the workflow and provides entry points.
- **blob_storage.py**: Contains functions to upload, retrieve, and manage documents in Azure Blob Storage.
- **config.yaml**: Holds configuration settings for Azure and OpenAI services.
- **openai_service.py**: Connects to OpenAI API to generate document insights.
- **pdf_processing.py**: Extracts text, metadata, and images from PDF files for processing and analysis.
- **utils.py**: Includes helper functions, such as text processing, file management, and data formatting.
- **requirements.txt**: Lists all Python packages required to run the project.