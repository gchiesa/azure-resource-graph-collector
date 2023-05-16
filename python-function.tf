resource "local_file" "function_json" {
  filename = "${path.module}/azure_function/resource-graph-collector/function.json"
  content  = <<EOT
{
  "scriptFile": "__init__.py",
  "bindings": [
    {
      "name": "event",
      "type": "timerTrigger",
      "direction": "in",
      "schedule": "${var.schedule_cron}"
    }
  ]
}
EOT
}

resource "local_file" "host_json" {
  filename = "${path.module}/azure_function/host.json"
  content  = <<EOT
{
  "version": "2.0",
  "logging": {
    "fileLoggingMode": "always",
    "logLevel": {
      "default": "${var.log_level}"
    },
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[2.*, 3.0.0)"
  }
}
EOT
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
    code   = data.archive_file.function_data.output_sha
    config = sha1(jsonencode(azurerm_function_app.function_app.app_settings))
  }
  provisioner "local-exec" {
    command = <<EXEC
    python tools/deploy_function_app.py \
      --root-dir azure_function \
      --function-dir resource-graph-collector \
      --subscription ${data.azurerm_subscription.current.display_name} \
      --resource-group ${azurerm_resource_group.rg.name} \
      --app-name ${azurerm_function_app.function_app.name}
EXEC
  }
}