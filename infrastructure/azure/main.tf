# =============================================================================
# Catalyst Nexus Core - Terraform Configuration
# =============================================================================
# Alternative to ARM/Bicep for multi-cloud deployments
# Initialize: terraform init
# Plan:       terraform plan -var-file="terraform.tfvars"
# Apply:      terraform apply -var-file="terraform.tfvars"
# =============================================================================

terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.80"
    }
  }
  
  backend "azurerm" {
    resource_group_name  = "catalyst-nexus-tfstate"
    storage_account_name = "catalystnexustfstate"
    container_name       = "tfstate"
    key                  = "catalyst-nexus.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# =============================================================================
# Variables
# =============================================================================

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "postgres_admin_password" {
  description = "PostgreSQL administrator password"
  type        = string
  sensitive   = true
}

# =============================================================================
# Local Values
# =============================================================================

locals {
  name_prefix    = "catalyst"
  resource_group = "catalyst-nexus-${var.environment}-rg"
  
  common_tags = {
    Environment = var.environment
    Project     = "Catalyst Nexus"
    ManagedBy   = "Terraform"
  }
}

# =============================================================================
# Resource Group
# =============================================================================

resource "azurerm_resource_group" "main" {
  name     = local.resource_group
  location = var.location
  tags     = local.common_tags
}

# =============================================================================
# Storage Account
# =============================================================================

resource "azurerm_storage_account" "main" {
  name                     = "${local.name_prefix}storage${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  
  blob_properties {
    versioning_enabled = true
    
    delete_retention_policy {
      days = 7
    }
  }
  
  tags = local.common_tags
}

resource "azurerm_storage_container" "assets" {
  name                  = "assets"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# =============================================================================
# PostgreSQL Flexible Server
# =============================================================================

resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "${local.name_prefix}-postgres-${var.environment}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = "15"
  administrator_login    = "catalystadmin"
  administrator_password = var.postgres_admin_password
  
  storage_mb = 32768
  sku_name   = "B_Standard_B2s"
  
  backup_retention_days = 7
  
  tags = local.common_tags
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "catalyst_nexus"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# =============================================================================
# Redis Cache
# =============================================================================

resource "azurerm_redis_cache" "main" {
  name                = "${local.name_prefix}-redis-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  capacity            = 0
  family              = "C"
  sku_name            = "Basic"
  enable_non_ssl_port = false
  minimum_tls_version = "1.2"
  
  tags = local.common_tags
}

# =============================================================================
# App Service
# =============================================================================

resource "azurerm_service_plan" "main" {
  name                = "${local.name_prefix}-asp-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "B2"
  
  tags = local.common_tags
}

resource "azurerm_linux_web_app" "main" {
  name                = "${local.name_prefix}-api-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.main.id
  
  site_config {
    always_on = true
    
    application_stack {
      python_version = "3.11"
    }
  }
  
  app_settings = {
    "DATABASE_URL"  = "postgresql+asyncpg://catalystadmin:${var.postgres_admin_password}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/catalyst_nexus"
    "REDIS_URL"     = "rediss://:${azurerm_redis_cache.main.primary_access_key}@${azurerm_redis_cache.main.hostname}:6380/0"
    "ENVIRONMENT"   = var.environment
  }
  
  tags = local.common_tags
}

# =============================================================================
# Outputs
# =============================================================================

output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "storage_account_name" {
  value = azurerm_storage_account.main.name
}

output "postgres_fqdn" {
  value     = azurerm_postgresql_flexible_server.main.fqdn
  sensitive = true
}

output "redis_hostname" {
  value = azurerm_redis_cache.main.hostname
}

output "app_service_url" {
  value = "https://${azurerm_linux_web_app.main.default_hostname}"
}
