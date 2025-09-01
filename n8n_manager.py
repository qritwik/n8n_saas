import json
import requests
import uuid
import config


class N8NManager:
    def __init__(self):
        self.base_url = config.N8N_URL
        self.headers = {
            "Content-Type": "application/json",
            "X-N8N-API-KEY": config.N8N_API_KEY,
        }

    def create_credential(
        self, email: str, access_token: str, refresh_token: str
    ) -> dict:
        """Create Gmail credential in n8n following API documentation format"""
        data = {
            "name": f"Gmail - {email}",
            "type": "gmailOAuth2",
            "data": {
                "clientId": config.GOOGLE_CLIENT_ID,
                "clientSecret": config.GOOGLE_CLIENT_SECRET,
                "sendAdditionalBodyProperties": False,
                "additionalBodyProperties": {},
                "oauthTokenData": {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send",
                    "token_type": "Bearer",
                    "expiry_date": 1640995200000,
                },
            },
        }

        print(f"Creating credential with data: {json.dumps(data, indent=2)}")

        response = requests.post(
            f"{self.base_url}/api/v1/credentials", json=data, headers=self.headers
        )

        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")

        return response.json()

    def create_or_update_workflow(self, email: str, credential_id: str) -> dict:
        """Create or update Gmail to Telegram workflow"""

        workflow_name = f"gmail_telegram_{email.replace('@', '_').replace('.', '_')}"

        clean_workflow_data = {
            "name": workflow_name,
            "nodes": [
                {
                    "parameters": {
                        "pollTimes": {"item": [{"mode": "everyMinute"}]},
                        "simple": False,
                        "filters": {"readStatus": "unread"},
                        "options": {},
                    },
                    "type": "n8n-nodes-base.gmailTrigger",
                    "typeVersion": 1.3,
                    "position": [0, 0],
                    "id": str(uuid.uuid4()),
                    "name": "Gmail Trigger",
                    "credentials": {"gmailOAuth2": {"id": credential_id}},
                },
                {
                    "parameters": {
                        "chatId": config.TELEGRAM_CHAT_ID,
                        "text": f"=📧 New email for {email}\n\n📋 Subject: {{{{ $json.subject }}}}\n👤 From: {{{{ $json.from }}}}\n📅 Date: {{{{ $json.date }}}}",
                        "additionalFields": {"appendAttribution": False},
                    },
                    "type": "n8n-nodes-base.telegram",
                    "typeVersion": 1.2,
                    "position": [300, 0],
                    "id": str(uuid.uuid4()),
                    "name": "Send Telegram",
                    "credentials": {"telegramApi": {"id": config.TELEGRAM_CRED_ID}},
                },
            ],
            "connections": {
                "Gmail Trigger": {
                    "main": [[{"node": "Send Telegram", "type": "main", "index": 0}]]
                }
            },
            "settings": {"executionOrder": "v1"},
        }

        try:
            response = requests.get(
                f"{self.base_url}/api/v1/workflows", headers=self.headers
            )
            if response.status_code == 200:
                workflows_data = response.json()

                # Handle both response formats
                if isinstance(workflows_data, dict) and "data" in workflows_data:
                    workflows = workflows_data["data"]
                else:
                    workflows = workflows_data

                existing_workflow = None
                for workflow in workflows:
                    if workflow["name"] == workflow_name:
                        existing_workflow = workflow
                        break

                if existing_workflow:
                    print(f"Updating existing workflow: {workflow_name}")
                    response = requests.put(
                        f"{self.base_url}/api/v1/workflows/{existing_workflow['id']}",
                        json=clean_workflow_data,
                        headers=self.headers,
                    )
                else:
                    print(f"Creating new workflow: {workflow_name}")
                    response = requests.post(
                        f"{self.base_url}/api/v1/workflows",
                        json=clean_workflow_data,
                        headers=self.headers,
                    )

                if response.status_code in [200, 201]:
                    result = response.json()
                    print(f"✅ Success! Workflow ID: {result['id']}")

                    # Activate the workflow
                    self._activate_workflow(result["id"])

                    return result
                else:
                    raise Exception(
                        f"Workflow creation failed: {response.status_code} - {response.text}"
                    )

            else:
                raise Exception(f"Cannot connect to n8n: {response.status_code}")

        except Exception as e:
            raise Exception(f"Workflow operation failed: {str(e)}")

    def _activate_workflow(self, workflow_id: str) -> bool:
        """Activate workflow"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/workflows/{workflow_id}/activate",
                headers=self.headers,
            )
            return response.status_code in [200, 201]
        except:
            return False

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow from n8n"""
        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/workflows/{workflow_id}", headers=self.headers
            )
            return response.status_code in [200, 204]
        except:
            return False

    def delete_credential(self, credential_id: str) -> bool:
        """Delete credential from n8n"""
        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/credentials/{credential_id}",
                headers=self.headers,
            )
            return response.status_code in [200, 204]
        except:
            return False

    def get_workflows(self) -> list:
        """Get all workflows"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/workflows", headers=self.headers
            )
            if response.status_code == 200:
                workflows_data = response.json()
                if isinstance(workflows_data, dict) and "data" in workflows_data:
                    return workflows_data["data"]
                else:
                    return workflows_data
            return []
        except:
            return []

    def get_credentials(self) -> list:
        """Get all credentials for debugging"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/credentials", headers=self.headers
            )
            if response.status_code == 200:
                return response.json()
            return []
        except:
            return []
