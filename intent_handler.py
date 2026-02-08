import re
from azure_service import AzureService
from config import logger, AZURE_SUBSCRIPTION_ID

# Robust Mapping: Groups of aliases for each Azure Resource Provider
AZURE_RESOURCES = [
    {"provider": "Microsoft.Compute/virtualMachines", "aliases": ["vm", "virtual machine", "vms", "instances"]},
    {"provider": "Microsoft.Web/sites", "aliases": ["web app", "webapp", "function", "app service", "site", "serverless"]},
    {"provider": "Microsoft.ContainerService/managedClusters", "aliases": ["aks", "kubernetes", "k8s", "cluster"]},
    {"provider": "Microsoft.Storage/storageAccounts", "aliases": ["storage", "stg", "blob", "account", "file share"]},
    {"provider": "Microsoft.Sql/servers/databases", "aliases": ["sql", "database", "db"]},
    {"provider": "Microsoft.DocumentDB/databaseAccounts", "aliases": ["cosmos", "nosql", "documentdb"]},
    {"provider": "Microsoft.Network/virtualNetworks", "aliases": ["vnet", "network", "virtual network"]},
    {"provider": "Microsoft.Network/networkSecurityGroups", "aliases": ["nsg", "firewall", "security group"]},
    {"provider": "Microsoft.KeyVault/vaults", "aliases": ["key vault", "kv", "secret", "vault"]},
    {"provider": "Microsoft.Network/publicIPAddresses", "aliases": ["public ip", "pip", "ip address"]},
    {"provider": "Microsoft.Compute/disks", "aliases": ["disk", "vhd", "drive"]},
    {"provider": "Microsoft.Network/networkInterfaces", "aliases": ["nic", "network interface", "adapter"]},
    {"provider": "Microsoft.Insights/components", "aliases": ["app insights", "application insights", "monitor", "telemetry"]},
    {"provider": "Microsoft.OperationalInsights/workspaces", "aliases": ["log analytics", "workspace", "logs"]},
    {"provider": "Microsoft.ContainerRegistry/registries", "aliases": ["acr", "registry", "docker registry"]},
    {"provider": "Microsoft.ApiManagement/service", "aliases": ["apim", "api management"]},
    {"provider": "Microsoft.Logic/workflows", "aliases": ["logic app", "workflow"]},
    {"provider": "Microsoft.ServiceBus/namespaces", "aliases": ["service bus", "bus", "queue", "topic"]},
    {"provider": "Microsoft.EventHub/namespaces", "aliases": ["event hub", "hub"]},
    {"provider": "Microsoft.RecoveryServices/vaults", "aliases": ["recovery services", "asr", "backup", "vault"]},
    {"provider": "Microsoft.Cache/Redis", "aliases": ["redis", "cache"]}
]

class IntentHandler:
    def __init__(self):
        self.azure = AzureService()

    def process_query(self, query: str) -> str:
        """Parse query, fetch data, and return a markdown response."""
        query = query.lower()
        logger.info(f"Processing query: {query}")

        # Intent: Advanced Metrics Filtering (e.g., CPU > 60%)
        # Matches: "CPU greater than 60", "cpu utilization was higher than 80%", "memory below 20%"
        perf_match = re.search(r"(cpu|memory)(?:\s+\w+){0,3}\s+(?:is|was|were|are|of)?\s*(?:greater|higher|more|above|less|below|under)\s*(?:than|to|of)?\s*(\d+)(?:%)?", query)
        if perf_match:
            logger.info(f"Matched Intent: Advanced Metrics Filtering (Regex: {perf_match.group(0)})")
            metric_type = perf_match.group(1)
            # Find the direction manually for better accuracy
            direction = "greater" if any(kw in query for kw in ["greater", "higher", "more", "above"]) else "less"
            threshold = int(perf_match.group(2))
            return self._handle_performance_filter(metric_type, direction, threshold)

        # Intent: Capabilities / Help
        if any(kw in query for kw in ["what can you do", "help", "capabilities", "list features"]):
            logger.info("Matched Intent: Capabilities/Help")
            return self._handle_help()

        # Intent: List VMs
        if any(kw in query for kw in ["list vms", "show vms", "show all vms", "get vms"]):
            logger.info("Matched Intent: List VMs")
            return self._handle_list_vms()

        # Intent: VM Disk Inventory/Count
        if any(kw in query for kw in ["disk count", "no of disks", "number of disks", "disks attached"]):
            logger.info("Matched Intent: VM Disk Inventory/Count")
            return self._handle_vm_disk_count()

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

        # Intent: List Subscriptions
        if any(kw in query for kw in ["list subscriptions", "show subscriptions"]):
            logger.info("Matched Intent: List Subscriptions")
            return self._handle_list_subscriptions()

        # Enhanced Resource Discovery
        # We check every alias for every resource group defined above
        for resource in AZURE_RESOURCES:
            provider = resource["provider"]
            for alias in resource["aliases"]:
                # Use regex for word-boundary matching (prevents "vm" matching "vmname")
                # Also handles optional trailing 's' for plurals
                pattern = rf"\b{alias}s?\b"
                if re.search(pattern, query):
                    logger.info(f"Matched Resource: {alias} -> {provider}")
                    state_filter = None
                    if "unattached" in query:
                        state_filter = "properties.diskState == 'Unattached' or properties.state == 'Unattached' or isempty(managedBy)"
                    elif any(kw in query for kw in ["stopped", "deallocated", "shutdown"]):
                        state_filter = "properties.extended.instanceView.powerState.displayStatus has 'stopped' or properties.state == 'Stopped'"
                    
                    return self._handle_generic_discovery(alias, provider, state_filter)

        # FINAL FALLBACK: Semantic Discovery
        # We query Azure to see what types actually exist, then fuzzy-match against the user's query
        logger.info("Starting Semantic Discovery Fallback...")
        available_types = self.azure.get_resource_types()
        
        # Look for a type that contains any word from the user's query
        words = [w for w in query.split() if len(w) > 3]
        for azure_type in available_types:
            type_parts = azure_type.lower().split('/')
            # Check if any word from the query matches any part of the resource type
            if any(word in type_parts[-1] or word in azure_type.lower() for word in words):
                logger.info(f"Semantically Matched: {azure_type}")
                return self._handle_generic_discovery(words[0], azure_type)

        # Still nothing? Try a broad property search
        if words:
            return self._handle_dynamic_search(words[:3])

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
        if isinstance(status, dict) and "error" in status:
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

    def _handle_generic_discovery(self, keyword, provider, state_filter=None):
        resources = self.azure.query_resources(provider, custom_where=state_filter)
        if isinstance(resources, dict) and "error" in resources:
            return f"Error discoverying {keyword}: {resources['error']}"

        if not resources:
            return f"No `{keyword}` resources found in the current subscription."

        response = f"### Azure {keyword.title()} Resources\n\n"
        response += "| Name | Resource Group | Location | Type |\n"
        response += "| :--- | :--- | :--- | :--- |\n"
        for res in resources:
            response += f"| {res['name']} | {res['resourceGroup']} | {res['location']} | {res['type'].split('/')[-1]} |\n"
        
        return response

    def _handle_dynamic_search(self, keywords):
        """Try to find any resource where the type or name contains the provided keywords."""
        filters = " or ".join([f"type contains '{kw}' or name contains '{kw}'" for kw in keywords])
        resources = self.azure.query_resources(custom_where=filters, limit=10)
        
        if not resources:
            return "I couldn't find any resources matching those keywords in your subscription."

        response = "### 🔍 Discovery Results\n\n"
        response += "I found these resources that might match your query:\n\n"
        response += "| Name | Type | Resource Group | Location |\n"
        response += "| :--- | :--- | :--- | :--- |\n"
        for res in resources:
            response += f"| {res['name']} | `{res['type'].split('/')[-1]}` | {res['resourceGroup']} | {res['location']} |\n"
        
        return response

    def _handle_list_subscriptions(self):
        subs = self.azure.list_subscriptions()
        if isinstance(subs, dict) and "error" in subs:
            return f"Error fetching subscriptions: {subs['error']}"

        if not subs:
            return "No subscriptions found for the current credential."

        response = "### Accessible Azure Subscriptions\n\n"
        response += "| Subscription Name | Subscription ID | State |\n"
        response += "| :--- | :--- | :--- |\n"
        for sub in subs:
            response += f"| {sub['display_name']} | `{sub['id']}` | {sub['state']} |\n"
        
        return response

    def _handle_performance_filter(self, metric_type, direction, threshold):
        # 1. Get List of VMs with IDs from Resource Graph (Fast)
        project = "id, name, resourceGroup, location"
        vms = self.azure.query_resources("Microsoft.Compute/virtualMachines", project_fields=project, limit=20)
        
        if not vms:
            return "No VMs found to analyze performance."

        metric_name = "Percentage CPU" if metric_type == "cpu" else "Available Memory Bytes"
        
        results = []
        for vm in vms:
            # Note: In a real production env, you'd use a background task / orchestration here
            # But for Phase 1, we do a targeted batch scan.
            val = self.azure.get_resource_metrics(vm['id'], metric_name)
            
            # Simple filtering logic
            if direction in ["greater", "higher", "more"] and val > threshold:
                results.append({"name": vm['name'], "rg": vm['resourceGroup'], "val": val})
            elif direction in ["less", "below"] and val < threshold:
                results.append({"name": vm['name'], "rg": vm['resourceGroup'], "val": val})

        if not results:
            return f"No VMs found with {metric_type.upper()} usage {direction} than {threshold}%."

        response = f"### 🚀 VMs with {metric_type.upper()} {direction} than {threshold}%\n"
        response += f"*Analysis period: Last 24 hours (Max Aggregation)*\n\n"
        response += "| VM Name | Resource Group | Peak Usage |\n"
        response += "| :--- | :--- | :--- |\n"
        for r in results:
            unit = "%" if metric_type == "cpu" else " MB"
            val_display = f"{r['val']:.1f}{unit}"
            response += f"| {r['name']} | {r['rg']} | **{val_display}** |\n"
        
        return response

    def _handle_help(self):
        return (
            "### 🤖 Azure-Agent Capabilities\n\n"
            "I can help you monitor and discover your Azure infrastructure using natural language. "
            "Here are the specific things I can do:\n\n"
            "#### 🖥️ Compute\n"
            "- **List VMs**: 'Show all my virtual machines'\n"
            "- **VM Status**: 'What is the status of VM web-server-01?'\n"
            "- **Metrics**: 'Show CPU for MyVMName' or 'Memory for analytics-db'\n"
            "- **Inventory**: 'Disk count for all VMs'\n\n"
            "#### 🌐 Networking\n"
            "- **VNets**: 'List all virtual networks'\n"
            "- **Public IPs**: 'Show my public IP addresses'\n"
            "- **State Alerts**: 'List unattached disks' or 'Show stopped VMs'\n\n"
            "#### 📂 Organization & Discovery\n"
            "- **Subscriptions**: 'List all my subscriptions'\n"
            "- **Resource Groups**: 'List resource groups'\n"
            "- **Wide Discovery**: I can find **100+ resource types** (SQL, Storage, Key Vaults, AKS, Firewalls, etc.). "
            "Just ask: 'Show all storage accounts' or 'List my key vaults'.\n\n"
            "--- \n"
            "*Note: I am currently in read-only mode (Phase 1).* "
        )

    def _handle_vm_disk_count(self):
        # Optimized Kusto query to project Name and calculate Disk Count
        # (array_length of dataDisks + 1 for OS disk)
        project = "name, resourceGroup, disk_count = array_length(properties.storageProfile.dataDisks) + 1"
        resources = self.azure.query_resources("Microsoft.Compute/virtualMachines", project_fields=project)
        
        if isinstance(resources, dict) and "error" in resources:
            return f"Error fetching disk counts: {resources['error']}"

        if not resources:
            return "No Virtual Machines found to count disks."

        response = "### VM Disk Inventory\n\n"
        response += "| VM Name | Resource Group | Total Disks |\n"
        response += "| :--- | :--- | :--- |\n"
        for res in resources:
            count = res.get('disk_count', 1)
            response += f"| {res['name']} | {res['resourceGroup']} | {count} |\n"
        
        return response
