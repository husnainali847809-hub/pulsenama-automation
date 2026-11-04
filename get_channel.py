
import os
import json
import requests

API_KEY = os.environ["BUFFER_API_KEY"]
ORG_ID = "6aeb3bc99a6868c13ac5db02"

query = """
query GetChannels {
  channels(input: {
    organizationId: "6aeb3bc99a6868c13ac5db02"
  }) {
    id
    name
    displayName
    service
  }
}
"""

response = requests.post(
    "https://api.buffer.com",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    },
    json={"query": query},
    timeout=30
)

response.raise_for_status()
data = response.json()
print(json.dumps(data, indent=2))

if "errors" in data:
    raise SystemExit("Buffer returned a GraphQL error.")

channels = data.get("data", {}).get("channels", [])

if not channels:
    print("No channels found in this organization.")

for channel in channels:
    print("Channel:", channel.get("displayName"))
    print("Service:", channel.get("service"))
    print("Channel ID:", channel.get("id"))
