import datetime
from azure.identity import ClientSecretCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from azure.mgmt.resource import ResourceManagementClient
from config import AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_SUBSCRIPTION_ID, logger

class AzureService:
    def __init__(self):
        self.credential = ClientSecretCredential(
            tenant_id=AZURE_TENANT_ID,
            client_id=AZURE_CLIENT_ID,
            client_secret=AZURE_CLIENT_SECRET
        )
        self.subscription_id = AZURE_SUBSCRIPTION_ID
        
        # Initialize Clients
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)
        self.compute_client = ComputeManagementClient(self.credential, self.subscription_id)
        self.network_client = NetworkManagementClient(self.credential, self.subscription_id)
        self.monitor_client = MonitorManagementClient(self.credential, self.subscription_id)

    def list_vms(self, resource_group=None):
        """List all VMs in a subscription or specific resource group."""
        try:
            if resource_group:
                vms = self.compute_client.virtual_machines.list(resource_group)
            else:
                vms = self.compute_client.virtual_machines.list_all()
            
            result = []
            for vm in vms:
                # To get power state, we need an instance view or specific call
                # For Phase 1 simplified list, we fetch name, location, and hardware profile
                vm_data = {
                    "name": vm.name,
                    "location": vm.location,
                    "size": vm.hardware_profile.vm_size,
                    "os": vm.storage_profile.os_disk.os_type,
                    "provisioning_state": vm.provisioning_state,
                    "resource_group": vm.id.split('/')[4] if vm.id else "Unknown"
                }
                result.append(vm_data)
            return result
        except Exception as e:
            logger.error(f"Error listing VMs: {e}")
            return {"error": str(e)}

    def get_vm_status(self, resource_group, vm_name):
        """Get detailed status of a specific VM."""
        try:
            vm = self.compute_client.virtual_machines.get(resource_group, vm_name, expand='instanceView')
            status = "Unknown"
            for s in vm.instance_view.statuses:
                if s.code.startswith("PowerState/"):
                    status = s.display_status
            
            return {
                "name": vm.name,
                "status": status,
                "location": vm.location,
                "size": vm.hardware_profile.vm_size,
                "provisioning_state": vm.provisioning_state
            }
        except Exception as e:
            logger.error(f"Error getting VM status: {e}")
            return {"error": str(e)}

    def get_metrics(self, resource_id, metric_names=["Percentage CPU"], timespan="PT1H"):
        """Fetch metrics for a specific resource."""
        try:
            metrics_data = self.monitor_client.metrics.list(
                resource_id,
                timespan=timespan,
                interval='PT1M',
                metricnames=','.join(metric_names),
                aggregation='Average'
            )
            
            result = {}
            for item in metrics_data.value:
                name = item.name.localized_value
                values = [round(v.average, 2) for v in item.timeseries[0].data if v.average is not None]
                result[name] = values[-5:] if values else [] # Last 5 readings
            return result
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            return {"error": str(e)}

    def list_resource_groups(self):
        """List all resource groups."""
        try:
            groups = self.resource_client.resource_groups.list()
            return [{"name": g.name, "location": g.location} for g in groups]
        except Exception as e:
            logger.error(f"Error listing resource groups: {e}")
            return {"error": str(e)}
