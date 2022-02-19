data "azurerm_user_assigned_identity" "identity" {
  name                = var.user_assigned_identity.name
  resource_group_name = var.user_assigned_identity.resource_group
}
