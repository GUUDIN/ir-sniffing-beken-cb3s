# AGENTS

Repository-level agent instructions.

## Terminal Efficiency Rules
- Reuse the same terminal for sequential steps of the same task whenever possible.
- Avoid opening multiple background terminals unless there is a clear need.
- Before opening a new terminal, check whether an active one can be reused.
- Stop background jobs/processes as soon as they are no longer needed.
- Prefer short, objective command batches to reduce terminal clutter.
- When a long-running process is required (e.g., local server), keep only one instance unless redundancy is explicitly requested.

## Safety for This Repo
- Do not run destructive git commands.
- Do not kill infrastructure services (e.g., MQTT broker) unless explicitly requested.
- If cleanup is requested, prioritize stopping subscribers/watchers and duplicate app processes first.
