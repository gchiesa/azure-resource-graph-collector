data "azurerm_user_assigned_identity" "identity" {
  name                = var.user_assigned_identity.name
  resource_group_name = var.user_assigned_identity.resource_group
}

data "archive_file" "function_data" {
  depends_on = [
    local_file.function_json
  ]

  type        = "zip"
  output_path = "function.zip"
  excludes    = [
    "local.settings.json",
    ".venv"
  ]
  source_dir = "${path.module}/azure_function"
}
