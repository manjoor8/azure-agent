# Azure-Agent

Azure-Agent is a Python-based backend service that integrates with **Open WebUI** to allow natural language querying of Azure infrastructure. It operates in **read-only** mode (Phase 1).

## Features

- **OpenAI-Compatible API**: Works as a drop-in provider for Open WebUI.
- **Natural Language to Azure**: Query VMs, status, metrics, and resource groups using plain English.
- **Read-Only**: Secure by design (uses official Azure SDKs).
- **Formatted Responses**: Returns clean Markdown tables and lists.

## Setup

### 1. Azure AD App Registration
1. In the Azure Portal, create an **App Registration**.
2. Create a **Client Secret**.
3. Grant **Reader** and **Monitoring Reader** permissions to the subscription for this app.
4. Collect: `Tenant ID`, `Client ID`, `Client Secret`, and `Subscription ID`.

### 2. Configuration
Create a `.env` file in the root directory and fill in your Azure credentials (see `.env.example` for reference):
```bash
cp .env.example .env
# Edit .env and fill in your details
```

### 3. Running with Docker (Recommended)
You can run the agent as a containerized service:
```bash
# Build and start the container
docker-compose up -d --build

# Verify the container is running
docker ps

# Check logs for any startup errors
docker logs -f azure-agent
```

### 4. Running Manually
If you prefer to run it directly on your machine:
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the agent
python agent.py
```
The agent will start on `http://localhost:6003`.

## Open WebUI Integration

Follow these steps to connect the Azure-Agent to your Open WebUI instance:

1. **Access Settings**: In Open WebUI, click on your profile icon (bottom-left) and select **Settings**.
2. **Navigate to Connections**: Go to the **Connections** tab.
3. **Configure OpenAI API**:
   - Locate the **OpenAI API** section.
   - Set the **Base URL** to: `http://azure-agent:6003/v1`
   - Set the **API Key** to: `sk-azure-agent` (any non-empty string will work).
4. **Save and Refresh**: Click the **Save** button. You may need to click the refresh icon next to the model list to fetch the new agent.
5. **Select Model**: Go back to the chat interface, and from the model dropdown menu at the top, select **Azure-Agent**.
6. **Start Chatting**: You can now ask questions about your Azure infrastructure in natural language.

### Method 2: Integration via Tools (Recommended for HTTPS)
If you prefer not to use environment variables, you can add Azure-Agent as a **Tool** within Open WebUI. This bypasses the Mixed Content (HTTPS) error:

1. Go to **Workspace > Tools > Create Tool**.
2. Name it `Azure Infrastructure`.
3. Paste the contents of `webui_tool.py` into the code editor.
4. Save and enable the tool for your chats.

> **Note**: Since the agent is on the same `webui-net` network as Open WebUI, use `http://azure-agent:6003/v1` as the internal URL.

## Example Queries

- *"Show all my VMs"*
- *"What is the status of VM web-server-01?"*
- *"Show CPU metrics for db-vm"*
- *"List my resource groups"*

## Architecture

- `agent.py`: FastAPI entry point.
- `azure_service.py`: Wrapper for Azure SDKs (Compute, Network, Monitor).
- `intent_handler.py`: NL parsing and response formatting.
- `models.py`: OpenAI API data structures.
