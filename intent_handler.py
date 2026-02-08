import re
from azure_service import AzureService
from config import logger, AZURE_SUBSCRIPTION_ID

# Mapping for Top 50+ Azure Services
AZURE_SERVICE_MAP = {
    # Compute
    "vm": "Microsoft.Compute/virtualMachines",
    "function": "Microsoft.Web/sites",
    "web app": "Microsoft.Web/sites",
    "app service": "Microsoft.Web/sites",
    "aks": "Microsoft.ContainerService/managedClusters",
    "kubernetes": "Microsoft.ContainerService/managedClusters",
    "acr": "Microsoft.ContainerRegistry/registries",
    
    # Storage & Data
    "storage": "Microsoft.Storage/storageAccounts",
    "sql": "Microsoft.Sql/servers/databases",
    "cosmos": "Microsoft.DocumentDB/databaseAccounts",
    "redis": "Microsoft.Cache/Redis",
    "postgresql": "Microsoft.DBforPostgreSQL/servers",
    "mysql": "Microsoft.DBforMySQL/servers",
    "synapse": "Microsoft.Synapse/workspaces",
    "databricks": "Microsoft.Databricks/workspaces",
    
    # Networking
    "vnet": "Microsoft.Network/virtualNetworks",
    "nsg": "Microsoft.Network/networkSecurityGroups",
    "load balancer": "Microsoft.Network/loadBalancers",
    "firewall": "Microsoft.Network/azureFirewalls",
    "application gateway": "Microsoft.Network/applicationGateways",
    "front door": "Microsoft.Network/frontdoors",
    "cdn": "Microsoft.Cdn/profiles",
    
    # Security & Management
    "key vault": "Microsoft.KeyVault/vaults",
    "monitor": "Microsoft.Insights/components",
    "log analytics": "Microsoft.OperationalInsights/workspaces",
    "automation": "Microsoft.Automation/automationAccounts",
    "policy": "Microsoft.Authorization/policyDefinitions",
    "sentinel": "Microsoft.OperationalInsights/workspaces",
    
    # Integration & AI
    "service bus": "Microsoft.ServiceBus/namespaces",
    "logic app": "Microsoft.Logic/workflows",
    "event grid": "Microsoft.EventGrid/topics",
    "event hub": "Microsoft.EventHub/namespaces",
    "api management": "Microsoft.ApiManagement/service",
    "search": "Microsoft.Search/searchServices",
    "cognitive": "Microsoft.CognitiveServices/accounts",
    "machine learning": "Microsoft.MachineLearningServices/workspaces",
    "purview": "Microsoft.Purview/accounts"
}

class IntentHandler:
    def __init__(self):
        self.azure = AzureService()

    def process_query(self, query: str) -> str:
        """Parse query, fetch data, and return a markdown response."""
        query = query.lower()
        logger.info(f"Processing query: {query}")

        # Intent: List VMs
        if any(kw in query for kw in ["list vms", "show vms", "show all vms", "get vms"]):
            return self._handle_list_vms()

        # Intent: VM Status/Health
        vm_status_match = re.search(r"(status|health|state) of (?:vm|virtual machine) ([\w-]+)", query)
        if vm_status_match:
            vm_name = vm_status_match.group(2)
            return self._handle_vm_status(vm_name)

        # Intent: CPU/Metrics
        metrics_match = re.search(r"(cpu|memory|metrics) (?:for|of) ([\w-]+)", query)
        if metrics_match:
            resource_name = metrics_match.group(2)
            return self._handle_metrics(resource_name)

        # Intent: List Resource Groups
        if any(kw in query for kw in ["resource groups", "list rgs", "show rgs"]):
            return self._handle_list_rgs()

        # Intent: List Virtual Networks
        if any(kw in query for kw in ["vnets", "networks", "virtual network"]):
            return self._handle_list_vnets()

        # Intent: List Public IPs
        if any(kw in query for kw in ["public ips", "ip addresses", "ips"]):
            return self._handle_list_public_ips()

        # Generic Intent: Top 50 Services Discovery
        for keyword, provider in AZURE_SERVICE_MAP.items():
            if keyword in query:
                return self._handle_generic_discovery(keyword, provider)

        # Default fallback
        return (
            "I'm sorry, I couldn't determine the specific Azure action for that query.\n\n"
            "Try asking things like:\n"
            "- 'Show all VMs'\n"
            "- 'Status of VM MyVMName'\n"
            "- 'CPU for MyVMName'\n"
            "- 'List resource groups'"
        )

    def _handle_list_vms(self):
        vms = self.azure.list_vms()
        if isinstance(vms, dict) and "error" in vms:
            return f"Error fetching VMs: {vms['error']}"
        
        if not vms:
            return "No Virtual Machines found in the current subscription."

        response = f"### Virtual Machines (Subscription: `{AZURE_SUBSCRIPTION_ID}`)\n\n"
        response += "| Name | Resource Group | Location | Size | OS | State |\n"
        response += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for vm in vms:
            response += f"| {vm['name']} | {vm['resource_group']} | {vm['location']} | {vm['size']} | {vm['os']} | {vm['provisioning_state']} |\n"
        
        return response

    def _handle_vm_status(self, vm_name):
        # We need the resource group. For simplicity in Phase 1, let's search for it.
        vms = self.azure.list_vms()
        target_vm = next((v for v in vms if v['name'].lower() == vm_name.lower()), None)
        
        if not target_vm:
            return f"Could not find VM named `{vm_name}` in the subscription."

        status = self.azure.get_vm_status(target_vm['resource_group'], target_vm['name'])
        if "error" in status:
            return f"Error fetching status for `{vm_name}`: {status['error']}"

        return (
            f"### Health Status: `{status['name']}`\n\n"
            f"- **Power State:** {status['status']}\n"
            f"- **Provisioning State:** {status['provisioning_state']}\n"
            f"- **Resource Group:** {target_vm['resource_group']}\n"
            f"- **Size:** {status['size']}\n"
            f"- **Location:** {status['location']}"
        )

    def _handle_metrics(self, resource_name):
        # Again, search for resource ID
        vms = self.azure.list_vms()
        target_vm = next((v for v in vms if v['name'].lower() == resource_name.lower()), None)
        
        if not target_vm:
            # Maybe it's not a VM, but for Phase 1 we focus on VMs
            return f"Could not find a Virtual Machine named `{resource_name}` to fetch metrics."

        # Reconstruct resource ID (approximated for Phase 1)
        resource_id = f"/subscriptions/{AZURE_SUBSCRIPTION_ID}/resourceGroups/{target_vm['resource_group']}/providers/Microsoft.Compute/virtualMachines/{target_vm['name']}"
        
        metrics = self.azure.get_metrics(resource_id)
        if "error" in metrics:
            return f"Error fetching metrics: {metrics['error']}"

        response = f"### Latest Metrics for `{target_vm['name']}`\n\n"
        for name, values in metrics.items():
            val_str = ", ".join([f"{v}%" for v in values]) if values else "N/A"
            response += f"- **{name}:** {val_str} (Last 5 mins)\n"
        
        if not metrics:
            response += "No metric data available for this resource in the last hour."
            
        return response

    def _handle_list_rgs(self):
        rgs = self.azure.list_resource_groups()
        if isinstance(rgs, dict) and "error" in rgs:
            return f"Error fetching Resource Groups: {rgs['error']}"

        response = "### Resource Groups\n\n"
        for rg in rgs:
            response += f"- `{rg['name']}` ({rg['location']})\n"
        return response

    def _handle_list_vnets(self):
        vnets = self.azure.list_vnets()
        if isinstance(vnets, dict) and "error" in vnets:
            return f"Error fetching VNets: {vnets['error']}"

        if not vnets:
            return "No Virtual Networks found in the current subscription."

        response = f"### Virtual Networks (Subscription: `{AZURE_SUBSCRIPTION_ID}`)\n\n"
        response += "| Name | Resource Group | Location | Address Prefix |\n"
        response += "| :--- | :--- | :--- | :--- |\n"
        for vnet in vnets:
            prefixes = ", ".join(vnet['address_space'])
            response += f"| {vnet['name']} | {vnet['resource_group']} | {vnet['location']} | {prefixes} |\n"
        return response

    def _handle_list_public_ips(self):
        ips = self.azure.list_public_ips()
        if isinstance(ips, dict) and "error" in ips:
            return f"Error fetching Public IPs: {ips['error']}"

        if not ips:
            return "No Public IP Addresses found."

        response = f"### Public IP Addresses (Subscription: `{AZURE_SUBSCRIPTION_ID}`)\n\n"
        response += "| Name | IP Address | Resource Group | Location | SKU |\n"
        response += "| :--- | :--- | :--- | :--- | :--- |\n"
        for ip in ips:
            response += f"| {ip['name']} | {ip['ip_address']} | {ip['resource_group']} | {ip['location']} | {ip['sku']} |\n"
        return response

    def _handle_generic_discovery(self, keyword, provider):
        resources = self.azure.query_resources(provider)
        if isinstance(resources, dict) and "error" in resources:
            return f"Error discoverying {keyword}: {resources['error']}"

        if not resources:
            return f"No `{keyword}` resources found in the current subscription."

        response = f"### Azure {keyword.title()} Resources\n\n"
        response += "| Name | Resource Group | Location | Type |\n"
        response += "| :--- | :--- | :--- | :--- |\n"
        for res in resources:
            # Type is often long, so we take the last part
            short_type = res['type'].split('/')[-1]
            response += f"| {res['name']} | {res['resourceGroup']} | {res['location']} | {short_type} |\n"
        
        return response
