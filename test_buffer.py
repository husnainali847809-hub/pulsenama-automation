
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
