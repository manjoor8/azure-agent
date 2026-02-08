import requests
import json
from typing import Optional

class Tools:
    def __init__(self):
        # The internal URL for the azure-agent container
        self.url = "http://azure-agent:6003/v1/chat/completions"
        self.headers = {"Content-Type": "application/json"}

    def query_azure(self, query: str) -> str:
        """
        Query Azure infrastructure (VMs, Status, Metrics, Resource Groups) using natural language.
        :param query: The query for Azure (e.g., 'show all vms', 'status of vm MyVM', 'cpu metrics for web-server').
        :return: A formatted markdown response with the Azure data.
        """
        payload = {
            "model": "azure-agent",
            "messages": [{"role": "user", "content": query}],
            "stream": False
        }

        try:
            response = requests.post(self.url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data['choices'][0]['message']['content']
            
        except requests.exceptions.RequestException as e:
            return f"Error connecting to Azure-Agent: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
