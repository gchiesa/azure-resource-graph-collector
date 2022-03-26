# azure-resource-graph-collector

Azure Resource Graph is a powerful tool to query Azure Cloud over a set of subscription or management groups. 
The result are still the result at the moment of the query. 
If you want to depict a trend over some information available via Azure Resource Graph you need to have some way to 
collect and ingest the result of the queries overtime. 

## What is azure-resource-graph-collector
This project is composed by infrastructure as code and includes an Azure Function that get a pre-saved Azure Resource 
Graph Query and periodically collect the result and send them to a backend. 

It uses a managed identities to access the resources (saved graph query and subscription to run the query against).

## Supported backends
Currently, the only backend supported is [Loki](https://grafana.com/logs/). 
You can get a free [Grafanacloud account](https://grafana.com/auth/sign-up/create-user) and configure it to expose a 
Loki endpoint to collect the results.

# Usage
Check the terraform [variables](variables.tf) to understand what information you need to provide through the 
infrastructure deployment.

## Pre-requisites
- You need to prepare the Azure Resource Graph query and save it in a Resource Group in your subscription.
- You need to create a User Assigned Managed Identity and set the following IAM role assignment:
  - `Reader` over the Resource Group that contains you saved query
  - `Reader` with scope the subscriptions / management groups you want to run the query against

## Time Trigger 
The function is periodically executed via Function App. You can configure your own time trigger via the 
`schedule_cron` terraform variable.

## Loki Specifics 
You can configure you Loki backend by provisioning the variables: 
- `loki_endpoint_url`
- `loki_authentication`

Whilst the endpoint is public, it's recommended to use environment variable to pass the authentication credentials 
(basic auth) in the form:

```shell 
export TF_VAR_loki_authentication='{"username"="<your_loki_id>", "password"="<your_loki_api_key>"}'
```

### Loki Labels
The tool supports the generation of Loki labels based on the values you ingest via the resource graph query. The 
tool supports up to 10 labels. You can specify what fields in the resource graph query you want to promote as labels 
via the variable `loki_label_names`


## Local testing 

### Prerequisites 
- Python virtualenv tools (I use pyenv): ```brew install pyenv pyenv-virtualenv```
- Azure CLI: ```brew install azcli```
- Azure Functions tools: ```brew install azure/functions/azure-functions-core-tools```

### Run it locally
You can run the Azure Function in your local development workstation by creating a 
[azure_function/local.settings.json](azure_function/local.settings.json) file with the following content (sensitive 
information have been redacted):

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "USER_ASSIGNED_IDENTITY_APP_ID": "****",
    "LOKI_USERNAME": "****",
    "LOKI_PASSWORD": "****",
    "LOKI_ENDPOINT": "****",
    "RESOURCE_GRAPH_QUERY_ID": "****",
    "AzureWebJobsStorage": ""
  }
}
```
**NOTES**: 
1. This file is ignored in the [.funcignore](azure_function/.funcignore) and it will not be deployed on the cloud.
2. In the local development you need to authenticate in Azure via Azure CLI (`az login`) first.
3. Local development requires you to have a virtual environment for python in the `.venv` folder. 
   I'm using [pyenv](https://github.com/pyenv/pyenv) and `pyenv-virtualenv` (installed with brew). To create the 
   environment I ran(from the project dir):
   ```shell
   pyenv virtualenv azure_resource_graph_collector
   ln -sf $(pyenv virtualenv-prefix azure_resource_graph_collector) ./.venv
   ```
