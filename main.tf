resource "azurerm_resource_group" "rg" {
  location = var.location
  name     = var.resource_group
}

resource "azurerm_storage_account" "sa" {
  account_replication_type = "LRS"
  account_tier             = "Standard"
  location                 = var.location
  name                     = "sa${format("%.22s", replace(var.function_app_identifier, "-", ""))}"
  resource_group_name      = azurerm_resource_group.rg.name
}

resource "azurerm_storage_container" "sacontainer" {
  name                  = "contents"
  storage_account_name  = azurerm_storage_account.sa.name
  container_access_type = "private"
}

resource "azurerm_application_insights" "appinsight" {
  application_type    = "web"
  location            = var.location
  name                = "${var.function_app_identifier}-appinsights"
  resource_group_name = azurerm_resource_group.rg.name

  tags = merge(
    var.tags,
    {
      # https://github.com/terraform-providers/terraform-provider-azurerm/issues/1303
      "hidden-link:${azurerm_resource_group.rg.id}/providers/Microsoft.Web/sites/${var.function_app_identifier}-function-app" = "Resource"
    })
}

resource "azurerm_app_service_plan" "service_plan" {
  location            = var.location
  name                = "${var.function_app_identifier}-service-plan"
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "FunctionApp"
  reserved            = true

  sku {
    size = "Y1"
    tier = "Dynamic"
  }
}

resource "azurerm_function_app" "function_app" {
  location                   = var.location
  name                       = "${var.function_app_identifier}-function-app"
  app_service_plan_id        = azurerm_app_service_plan.service_plan.id
  resource_group_name        = azurerm_resource_group.rg.name
  storage_account_name       = azurerm_storage_account.sa.name
  storage_account_access_key = azurerm_storage_account.sa.primary_access_key
  version                    = "~3"
  os_type                    = "linux"
  app_settings               = {
    "WEBSITE_RUN_FROM_PACKAGE"              = "1"
    "FUNCTIONS_WORKER_RUNTIME"              = "python"
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = azurerm_application_insights.appinsight.instrumentation_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = "InstrumentationKey=${azurerm_application_insights.appinsight.instrumentation_key};IngestionEndpoint=https://${var.location}-0.in.applicationinsights.azure.com/"
    "USER_ASSIGNED_IDENTITY_APP_ID"         = data.azurerm_user_assigned_identity.identity.client_id,
    "LOKI_USERNAME"                         = var.loki_authentication.username,
    "LOKI_PASSWORD"                         = var.loki_authentication.password,
    "LOKI_ENDPOINT"                         = var.loki_endpoint_url,
    "RESOURCE_GRAPH_QUERY_ID"               = var.resource_graph_query_id,
  }
  identity {
    type         = "UserAssigned"
    identity_ids = data.azurerm_user_assigned_identity.identity[*].id
  }
}

data "archive_file" "function_data" {
  type        = "zip"
  output_path = "function.zip"
  excludes    = [
    "local.settings.json",
    ".venv"
  ]
  source_dir = "${path.module}/azure_function"
}

resource "time_sleep" "wait_for_app" {
  depends_on = [
    azurerm_function_app.function_app
  ]

  create_duration = "30s"
}

resource "null_resource" "deploy_function" {
  depends_on = [
    time_sleep.wait_for_app
  ]

  triggers = {
    always = data.archive_file.function_data.output_sha
  }
  provisioner "local-exec" {
    command = "cd ${path.module}/azure_function; func azure functionapp publish ${azurerm_function_app.function_app.name}"
  }
}