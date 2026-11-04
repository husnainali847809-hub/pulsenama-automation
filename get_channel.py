
import os
import requests
import json

API_KEY = os.environ["BUFFER_API_KEY"]

query = """
query {
  account {
    organizations {
      id
      name
    }
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

data = response.json()
print(json.dumps(data, indent=2))

if response.status_code != 200:
    raise SystemExit("Buffer API request failed")
