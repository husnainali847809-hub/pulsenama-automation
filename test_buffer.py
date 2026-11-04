
import os
import requests
import json

API_KEY = os.environ["BUFFER_API_KEY"]
CHANNEL_ID = "6aeb3cc2e29c69a1715d606e"

query = """
mutation CreateTestPost {
  createPost(input: {
    text: "TEST: PulseNama Buffer API connection is working successfully.",
    channelId: "6aeb3cc2e29c69a1715d606e",
    schedulingType: automatic,
    mode: addToQueue,
    metadata: {
      facebook: {
        type: post
      }
    }
  }) {
    ... on PostActionSuccess {
      post {
        id
        text
        dueAt
      }
    }
    ... on MutationError {
      message
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

response.raise_for_status()
result = response.json()

print(json.dumps(result, indent=2))

if result.get("errors"):
    raise SystemExit("Buffer API returned a GraphQL error.")

post = result.get("data", {}).get("createPost", {})

if post.get("post"):
    print("SUCCESS: Test post added to Buffer queue.")
else:
    print("FAILED:", post.get("message", "Unknown error"))
    raise SystemExit(1)
