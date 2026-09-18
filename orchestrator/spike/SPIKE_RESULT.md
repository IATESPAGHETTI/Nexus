# Phase 2.5 Spike Result — ADK + GPT-OSS 120B via Groq

**Status: PASS (implemented + tested)**

## What was proven

Using a real (not mocked) call to Groq:

1. An ADK `Agent` (`google.adk.agents.Agent`, backed by `LlmAgent`) was built with
   `model=LiteLlm(model="groq/openai/gpt-oss-120b", include_reasoning=False)`.
2. The model actually responded (non-empty final text).
3. The model actually performed a real tool call (`get_incident_severity_code`),
   observed as a `function_call` part in the ADK event stream.
4. The tool's return value (an arbitrary, non-guessable constant `8271`, unrelated
   to anything the model could infer from the prompt) reached the model and was
   correctly restated in its final answer: *"The current incident severity code is
   **8271**."*

Run: `orchestrator/spike/adk_groq_spike.py` (manual) and
`orchestrator/tests/test_adk_groq_spike.py` (pytest form). Both pass, exit code 0.

## Exact dependency versions (isolated venv: `.venv-orchestrator/`)

```text
google-adk==2.9.1
litellm==1.101.0
python-dotenv==1.2.3
pytest==9.1.1
python 3.10 (Windows)
```

Recorded in `orchestrator/requirements.txt`.

## Model identifier actually used

`groq/openai/gpt-oss-120b` (confirmed via `GROQ_MODEL` env var read from `.env` and
echoed by the spike script's own log line — no substitution occurred).

## Blocking issue found, and the fix

**Issue:** Groq's GPT-OSS models return a `reasoning_content`/`reasoning` field on
assistant messages. When ADK/LiteLLM replay that assistant message back to Groq on
the next turn of a tool-calling conversation (as required for the model to see its
own prior tool call and produce a final answer), Groq's own chat-completions schema
rejects it:

```text
litellm.BadRequestError: GroqException - {"error":{"message":"'messages.2' :
for 'role:assistant' the following must be satisfied[('messages.2' : property
'reasoning_content' is unsupported)]","type":"invalid_request_error"}}
```

This is a known, currently-unresolved LiteLLM/Groq compatibility issue — not
specific to this project or to ADK. See BerriAI/litellm#8136, #14163, #16129, and
karthink/gptel#774 for other reports of the same root cause (Groq's reasoning
models attach reasoning content to responses; providers/clients that echo full
message history back reproduce this error on the next turn).

Tried and rejected: `litellm.drop_params = True` — does **not** fix this, because
the unsupported field is embedded inside a message object's content, not a
top-level request parameter that `drop_params` strips.

**Working fix:** pass Groq's own `include_reasoning=False` parameter through to the
`LiteLlm` model wrapper:

```python
LiteLlm(model="groq/openai/gpt-oss-120b", include_reasoning=False)
```

This stops Groq from attaching `reasoning_content` to responses in the first place,
so there is nothing invalid to echo back on the next turn.

## Consequence for all future agent code

**Every ADK agent in this project that uses the Groq/GPT-OSS runtime model must
set `include_reasoning=False` on its `LiteLlm` wrapper**, or multi-turn tool-calling
will fail on the second turn. This applies to Phase 4 diagnostic agents, the
evidence agent, the critic, and the recovery agent alike. Document this in each
new agent's local `CLAUDE.md`/code comment rather than rediscovering it.

## Regression check

Phase 1/2 test suite (`pytest`, main `.venv/`) re-run after the spike: **8/8 passed**,
unaffected — the spike ran entirely inside the isolated `.venv-orchestrator/` and
never touched the shared backend/production environment.

## Cosmetic (non-blocking) noise observed

After the spike script prints its result and exits 0, Python's asyncio Proactor
event loop on Windows logs a `Fatal error on SSL transport` /
`RuntimeError: Event loop is closed` traceback during interpreter shutdown. This is
a known asyncio/Windows + aiohttp/httpx client-teardown-ordering artifact, not a
test failure — confirmed by explicit exit-code checks (`echo $?` → `0`) both for the
standalone script and the pytest run. Not investigated further since it does not
affect correctness; revisit only if it starts affecting CI exit codes.

## Verdict

Spike **PASSED**. Proceed to Phase 3 (MCP) with Google ADK as the agent framework,
GPT-OSS 120B via Groq (with `include_reasoning=False`) as the runtime LLM.
