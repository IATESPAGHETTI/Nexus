// Plain-English glossary. Two groups:
//  - NEXUS_WORDS: vocabulary of the screen itself (always shown).
//  - AGENT_WORDS: technical words the AI agents tend to use; each one is shown
//    ONLY when it actually appears in text on the current incident, so the
//    box explains what the viewer is really looking at.
// Definitions are fixed, general-knowledge explanations. They are not generated
// by a model and never claim anything about the incident.

export interface GlossaryEntry {
  term: string;
  plain: string;
  /** matches text on screen; omitted for always-shown entries */
  pattern?: RegExp;
}

export const NEXUS_WORDS: GlossaryEntry[] = [
  { term: "Agent", plain: "A separate AI program with one job (for example “look at the database”). Each one runs as its own service." },
  {
    term: "A2A (agent-to-agent message)",
    plain: "How two agents talk: one sends a request over the network, the other sends a reply back (the “callback”). It is like one person phoning another, not one person muttering to themselves.",
  },
  {
    term: "MCP / system check",
    plain: "The only tools an agent may use to look at the shop (metrics, logs, traces, database stats, deployment history). Agents cannot touch anything else, so every claim traces back to a real check.",
  },
  { term: "Triage (which agents get called)", plain: "Like a lead deciding who to page. The Incident Manager reads the symptoms and only calls the specialists they point at. If the Critic later asks for something an unused specialist covers, that specialist is called then." },
  { term: "Evidence", plain: "A recorded result from one system check, with an id like ev-1a2b3c4d so anyone can find exactly what was measured." },
  { term: "Possible cause (hypothesis)", plain: "A guess about what broke, written down together with the evidence for and against it. It is not treated as true yet." },
  { term: "Root-Cause Critic", plain: "A second AI whose only job is to try to prove the first guess wrong. A guess must survive it before NEXUS acts." },
  { term: "Confidence", plain: "How sure the Evidence Agent says it is. It is the AI’s own estimate, not a measured probability, which is why the Critic double-checks." },
  { term: "Abstain", plain: "NEXUS chooses to say “I am not sure enough” instead of guessing. This is a feature: a confident wrong answer is worse." },
  { term: "Blast radius", plain: "How much could be affected if a fix goes wrong. Small is safer." },
  { term: "Human approval", plain: "Nothing is changed on the shop until a person clicks Approve. The AI proposes, a person decides." },
  { term: "Live check after the fix", plain: "NEXUS does not trust itself. After the fix it sends real requests to the shop and measures the speed. Only if they pass the limit is the incident called recovered." },
  { term: "Median", plain: "The middle value of several timings. It ignores one unusually slow or fast request, so it is a fair “typical speed”." },
];

export const AGENT_WORDS: GlossaryEntry[] = [
  { term: "Latency / ms", plain: "How long a request takes to be answered. ms = millisecond, a thousandth of a second (1000 ms = 1 second).", pattern: /latency|\bms\b/i },
  { term: "p99", plain: "The speed that 99 out of 100 requests beat. It shows how bad the slowest 1% are. A big gap between the average and p99 means a few requests are very slow.", pattern: /\bp99\b|tail/i },
  { term: "Endpoint (/orders)", plain: "One address on the shop that does one job. /orders lists orders, /orders/1 fetches order number 1.", pattern: /endpoint|\/orders|\/health/i },
  { term: "Trace / span", plain: "A trace is the diary of one request from start to finish. A span is one step inside that diary (for example “ran the database query”).", pattern: /\btrace|span/i },
  { term: "Onset / step change", plain: "The moment things changed. “Step change” means it was fast, then suddenly slow and stayed slow, rather than flickering.", pattern: /onset|step change|bimodal/i },
  { term: "Intermittent", plain: "Happening on and off instead of all the time.", pattern: /intermittent/i },
  { term: "Query / SELECT", plain: "A question asked to the database. SELECT * FROM orders ORDER BY id means “give me every order, sorted by number”.", pattern: /\bquery|queries|select\b/i },
  { term: "Full-table scan", plain: "The database reading every row to answer a question instead of jumping straight to the right one. Fine for 11 rows, slow for millions.", pattern: /table scan|full-table|scan/i },
  { term: "Index", plain: "A lookup shortcut a database keeps, like a book’s index, so it does not read every page.", pattern: /\bindex|indexes|indices/i },
  { term: "Execution plan (EXPLAIN)", plain: "The database’s own explanation of how it will answer a query. Reading it shows whether the query is doing too much work.", pattern: /execution plan|explain/i },
  { term: "Contention / lock", plain: "Several things waiting for the same resource, like people queueing for one till.", pattern: /contention|lock\b|locks\b/i },
  { term: "Connection pool", plain: "A fixed set of ready-made database connections that requests borrow. If they are all busy, new requests wait.", pattern: /connection pool|pool exhaust/i },
  { term: "Throttle / penalty", plain: "A deliberate or accidental fixed delay added to every request, regardless of how much work it really does.", pattern: /throttl|penalty|constant delay|artificial/i },
  { term: "Serialization / handler / middleware", plain: "Application steps around the database: turning data into a reply (serialization), the code that handles a request (handler), and shared code that runs before it (middleware).", pattern: /serializ|handler|middleware/i },
  { term: "Instrumentation", plain: "The code that measures and records how long things take. It is the thermometer, not the fever.", pattern: /instrumentation/i },
  { term: "Deployment / rollback", plain: "A deployment publishes a new version of the software. A rollback returns to the previous version.", pattern: /deploy|rollback|roll back/i },
  { term: "Config / feature flag", plain: "Settings that change behaviour without changing code. A feature flag is an on/off switch for a feature.", pattern: /\bconfig|feature flag/i },
  { term: "Baseline", plain: "How the system behaved when it was healthy. Used for comparison with how it behaves now.", pattern: /baseline|pre-change/i },
  { term: "Evidence pool", plain: "Everything the investigators found, gathered in one place so the Critic can read all of it, not only what supports the guess.", pattern: /evidence_pool|evidence pool/i },
  { term: "Error rate / error count", plain: "How many requests failed outright. Zero errors with high latency means “slow but working”, which points away from crashes.", pattern: /error[_ ]?(rate|count)|errors/i },
  { term: "remedy_guidance / scale_resources", plain: "A built-in guide that maps a diagnosed symptom to the few fixes allowed for it. scale_resources means “give the service more capacity”; here it also clears the injected slowdown.", pattern: /remedy_guidance|scale_resources|restore service resources/i },
  { term: "SQLite", plain: "A small database stored in one file, used by the simulated shop.", pattern: /sqlite/i },
];

export function wordsUsedIn(text: string): GlossaryEntry[] {
  return AGENT_WORDS.filter((w) => w.pattern?.test(text));
}
