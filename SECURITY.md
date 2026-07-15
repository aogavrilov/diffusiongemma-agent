# Security

## Local execution model

DiffusionGemma Agent modifies repository files and can execute bounded local
commands and tests. Its checkpoint and rollback mechanisms are recovery tools,
not a security boundary or sandbox.

- Run it only on repositories you trust.
- Use a clean Git worktree and inspect the final diff.
- Do not expose cloud credentials, signing keys, production secrets, or SSH
  agents to an untrusted repository task.
- Keep the gateway bound to localhost unless you add independent
  authentication and network isolation.
- Stop the service when it is not in use to release GPU memory.

Native model-selected tool calls are disabled by default. Tool execution is
mediated by deterministic supervisor routes, but generated commands and tests
still require user review.

## Runtime supply chain

The PyPI package contains only the Python installer and CLI. The model, custom
backend, and CUDA redistributable libraries are downloaded from a pinned
Hugging Face revision. Source for the agent and custom backend is public and
linked from the main README. Third-party license texts ship with the runtime.

## Reporting a vulnerability

Use the private vulnerability reporting feature in the GitHub Security tab of
`aogavrilov/diffusiongemma-agent`. Do not publish credentials, exploit details,
or private repository contents in a public issue.
