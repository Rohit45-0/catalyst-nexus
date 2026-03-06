# =============================================================================
# Catalyst Nexus Core - Azure Resource Manager Template
# =============================================================================
# Deploy: az deployment group create --resource-group catalyst-nexus-rg \
#         --template-file main.bicep --parameters @parameters.json
# =============================================================================

@description('The location for all resources')
param location string = resourceGroup().location

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('The name prefix for all resources')
param namePrefix string = 'catalyst'

@description('PostgreSQL administrator login')
param postgresAdminLogin string = 'catalystadmin'

@secure()
@description('PostgreSQL administrator password')
param postgresAdminPassword string

@description('VM size for the compute instance')
param vmSize string = 'Standard_NC6s_v3'

// Variables
var uniqueSuffix = uniqueString(resourceGroup().id)
var storageAccountName = '${namePrefix}storage${uniqueSuffix}'
var containerRegistryName = '${namePrefix}acr${uniqueSuffix}'
var keyVaultName = '${namePrefix}-kv-${environment}'
var postgresServerName = '${namePrefix}-postgres-${environment}'
var redisCacheName = '${namePrefix}-redis-${environment}'
var appServicePlanName = '${namePrefix}-asp-${environment}'
var appServiceName = '${namePrefix}-api-${environment}'

// =============================================================================
// Storage Account
// =============================================================================
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource assetsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'assets'
  properties: {
    publicAccess: 'None'
  }
}

// =============================================================================
// Container Registry
// =============================================================================
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: containerRegistryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// =============================================================================
// Key Vault
// =============================================================================
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: subscription().tenantId
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enableRbacAuthorization: true
  }
}

// =============================================================================
// PostgreSQL Flexible Server
// =============================================================================
resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: postgresServerName
  location: location
  sku: {
    name: 'Standard_B2s'
    tier: 'Burstable'
  }
  properties: {
    version: '15'
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

resource postgresDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgresServer
  name: 'catalyst_nexus'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource postgresFirewallRule 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: postgresServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// =============================================================================
// Redis Cache
// =============================================================================
resource redisCache 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisCacheName
  location: location
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
  }
}

// =============================================================================
// App Service Plan
// =============================================================================
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'B2'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// =============================================================================
// App Service (Backend API)
// =============================================================================
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: appServiceName
  location: location
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: true
      appSettings: [
        {
          name: 'DATABASE_URL'
          value: 'postgresql+asyncpg://${postgresAdminLogin}:${postgresAdminPassword}@${postgresServer.properties.fullyQualifiedDomainName}:5432/catalyst_nexus'
        }
        {
          name: 'REDIS_URL'
          value: 'rediss://:${redisCache.listKeys().primaryKey}@${redisCache.properties.hostName}:6380/0'
        }
        {
          name: 'ENVIRONMENT'
          value: environment
        }
      ]
    }
    httpsOnly: true
  }
}

// =============================================================================
// Outputs
// =============================================================================
output storageAccountName string = storageAccount.name
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output postgresServerFqdn string = postgresServer.properties.fullyQualifiedDomainName
output redisCacheHostName string = redisCache.properties.hostName
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
