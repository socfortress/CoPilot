# Talon v2 stream fixtures

Copied unchanged from talon-analyst `tests/contract/golden/v2_*.txt` at talon-analyst `main`
`17c941e` (the files last changed in `8735b31`, M5-10). They are the wire of
`POST /v2/chat/{thread_id}` (talon-analyst SPEC §8 "v2 API"): the Vercel AI UI message stream,
one `data: <json>` chunk per block, ending with `data: [DONE]` and a blank line. CoPilot's
backend proxy keeps its own copy in `backend/tests/fixtures/talon_v2/`.

| File              | Turn                                                                           |
| ----------------- | ------------------------------------------------------------------------------ |
| `v2_text.txt`     | A text reply                                                                   |
| `v2_tool.txt`     | Text, one tool call (name, input, fixed summary), then a second step's text    |
| `v2_approval.txt` | Text, a proposed action call, then its approval card (`tool-approval-request`) |
| `v2_error.txt`    | A model error after some text: the fixed `error` chunk                         |

The files are wire bytes, so `end-of-file-fixer` skips this directory (`.pre-commit-config.yaml`).
`talon-v2-parser.spec.ts` reads them at every byte split point. Refresh them by copying the
talon-analyst files again and noting its commit here.
