# NEXUS demo guide: follow this step by step

A 5–7 minute live demo you can run and explain yourself. Everything you click is real: a real
(simulated) shop, a real failure, real AI agents, a real fix.

## The story in one breath

> "This is a simulated online shop. I'll break its database on purpose. A team of AI agents will
> investigate, work out the cause from evidence, argue with themselves, and propose a fix. A human
> (me) approves it, it runs, and the shop is measured again to prove it's fixed."

## 1. What is on screen: three things

| Address | What it is | Role |
|---|---|---|
| `http://localhost:8001/shop` | **The shop** (simulated) | The patient. It gets broken and fixed. |
| `http://localhost:5174` (or `5173`) | **NEXUS dashboard** | The doctors' screen. Go to the **Presentation** page. |
| `http://localhost:8000` | NEXUS backend | Stores incidents. No page to look at. |

Put the **shop** and the **dashboard** in two browser windows side by side.

## 2. Start everything (before the audience arrives)

From the project folder, in three terminals (the agents start from the dashboard in step 3):

```bash
.venv/Scripts/python.exe -m uvicorn service:app --app-dir production --port 8001
```
```bash
.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --port 8000
```
```bash
npm --prefix dashboard run dev
```

(First time only: `npm --prefix dashboard install`.) Your DeepSeek key must be in the root `.env`
as `DEEPSEEK_API_KEY=...`.

Checks: `http://localhost:8001/health` and `http://localhost:8000/health` both say `ok`.

## 3. The demo, step by step

**Step 1: show the healthy shop.** Open `http://localhost:8001/shop`.
Tick **Simulate shoppers**. The **Demo monitor** strip under the menu says **Healthy**, and each bar is about 5 ms.
*Say:* "Every bar is a real customer request. Healthy means under 100 milliseconds."

**Step 1b: place an order as a customer.** Click **Add to cart** on two products, open the **Cart**, type a
name and press **Place order**. It confirms in a few milliseconds ("Took 5 ms").
*Say:* "This is a real checkout: it writes a row into the shop's database."

**Step 2: switch the agents on.** In the dashboard, Presentation page, flip **NEXUS AGENTS** to **ON**.
Wait about 20–30 seconds until it says **Live Connected (7/7)**.
*Say:* "Seven AI agents, each its own separate program. They talk to each other over a real
agent-to-agent protocol, and they only read the shop through approved diagnostic tools."

**Step 3: break the shop.** In the dashboard pick a failure (Slow database, Bad release, Wrong setting, Payment service
down, Out of memory), click **Inject: ...** and confirm. NEXUS first resets the shop to a clean state.
(It makes roughly 10–30 paid AI calls.)
Switch to the shop window. Within a few seconds the badge turns **Slow** and the bars jump to about 260 ms.
*Say:* "I just made every database query slower. Nothing says why. The agents have to find out."
Now **place another order** in the shop: it takes about a quarter of a second and the monitor strip turns
amber. (Browsing the product grid stays fast, because the catalog isn't stored in the database. Only the
database-backed parts slow down, like many real shops.)

**Step 4: watch the investigation (about 45–60 seconds).** On the dashboard watch the stages tick down:
1. **Gather evidence:** the Incident Manager calls only the specialists the complaint points at (2 to 4 of: speed and
   errors, logs, recent changes, database). Skipped agents show as "not called" with the reason.
2. **Form possible causes:** a ranked list with confidence.
3. **Challenge:** the Critic tries to knock the top cause down. It may ask for more evidence and send the
   team back for a second round. That is the loop working.
4. **Decide:** a supported cause, or an honest "not enough evidence".
*Say:* "The Critic's job is to disagree. NEXUS is allowed to say 'I don't know'."

**Step 5: the fix needs a human.** A banner appears: **Recovery is waiting for your approval**. Read the
proposed action out loud (for a slow database it should be **scale resources**). The safety checks have
already passed it.
*Say:* "The AI can only suggest. Safety rules checked this plan, and nothing runs until a person says yes."

**Step 6: approve and verify.** Click **Approve recovery**. The last stage goes: running, then measuring.
Watch the shop window: the monitor returns to **Healthy** and the bars drop back to a few milliseconds.
The dashboard shows the live check after the fix, for example "GET /orders median 5 ms (limit 100 ms)".
*Say:* "NEXUS doesn't take its own word for it. It re-measures the shop, and only then calls it fixed."

**Step 7 (optional): show the usage box.** In the dashboard the **LLM usage** panel shows how many AI calls
and tokens this investigation used, against the spending limits. Mention that NEXUS stops itself and says
"I don't know" if a limit is hit.

## 4. If something goes wrong

| What you see | What to do |
|---|---|
| Agents stay at 0/7 | Wait 30 s. If still 0, check `.env` has the key, then flip OFF and ON again. |
| Investigation ends "abstained", every agent "no response" | The AI key was rejected. Fix `.env`, flip OFF/ON (agents read `.env` only at start). |
| Ends **abstained** ("not enough evidence") | Normal sometimes. Click **Inject** again (the shop resets between runs if you clear it). |
| Fix says **not verified** | Honest outcome: the action ran but the shop is still slow. Say so, then clear it (below). |
| "Approval window closed" | Click **Approve saved plan**: it resumes the saved plan. |
| Shop still broken after the demo | Click Inject again (it resets first) or: `curl -X POST http://127.0.0.1:8001/admin/reset` |
| Results look odd after many runs | The shop keeps history of earlier incidents. Reset it (above); old errors look like evidence. |
| Dashboard blank page | Hard refresh. Two dev servers sharing one `node_modules` can clash. |

## 5. Questions your teacher may ask

- **"Where does the data come from?"** A simulated shop with 10 invented orders. Metrics, logs and
  traces are produced by real requests to it. We cause the fault ourselves, so we know the right
  answer and can grade the AI against it.
- **"Is this real AI or scripted?"** Real model calls (DeepSeek). The dashboard shows the exact call
  counts. Agents' tool results come from the live shop.
- **"What stops it doing something dangerous?"** Only 4 allowed actions, a safety check, a mandatory
  human approval, a kill switch, and an automatic re-measurement afterwards.
- **"What if it's wrong?"** The Critic challenges every cause, the fix is verified by measurement,
  and it can answer "not enough evidence".
- **"What's a package?"** Ready-made code we install instead of writing (see `docs/PROJECT_EXPLAINED.md`).

## 6. Be upfront about these limits

- It runs on a simulated shop, so it shows the method, not performance on a real company's systems.
- The accuracy comparison across the 5 fault types (one AI vs the team vs the team without the Critic)
  is built but **has not been run yet**. Don't quote accuracy numbers.
- The agents are real AI, so outcomes vary: in practice most runs diagnose the slow database and propose
  the right fix, but some end in an honest "not enough evidence". If that happens, just run it again.
  (The code-history tool that could leak the answer is disabled.)

## Which failure to pick

| Button | What breaks | Fix NEXUS proposes |
|---|---|---|
| Slow database | order lookups take about 260 ms | restore resources |
| Bad release | a new version fails some orders | roll back |
| Wrong setting | an invalid setting fails every order | reset config |
| Payment service down | single-order lookups hang then fail | restart |
| Out of memory | the whole shop slows and refuses some requests | restore resources or restart |

In practice runs (one each, not a benchmark) all five were diagnosed, fixed and verified, but the AI is not
deterministic: if one ends "abstained", click Inject again.

## Showing the shop on a phone (same Wi-Fi)

Run the shop on `0.0.0.0` (`uvicorn service:app --app-dir production --port 8001 --host 0.0.0.0`), allow TCP 8001 in
Windows Firewall for the Private profile, then open `http://<laptop-ip>:8001/shop`. Use your own network: the shop's
control endpoints become reachable to anyone on it.