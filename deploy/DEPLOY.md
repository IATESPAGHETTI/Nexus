# Deploying NEXUS (course requirement 11)

NEXUS runs as 11 containers from one `docker-compose.yml`: the simulated shop (`production`), `backend`, `orchestrator`,
7 independent A2A agent services, and the `dashboard` (nginx, the only public port). A CrewAI critic is an optional 12th
(`--profile crewai`). Status: **compose file validated (`docker compose config`); images not yet built or run here
because Docker Desktop's engine was not running** (see `docs/PROJECT_STATE.md` for the latest verification).

## 0. Free, no credit card: Hugging Face Spaces (single container)

A free Space can run one Docker container (2 vCPU, 16 GB RAM) with no card. `Dockerfile.space` packs everything into that one
container (nginx + backend + shop + orchestrator + 7 agents under supervisord, talking over localhost).

1. Create a free account at huggingface.co, then **New Space -> SDK: Docker -> Blank**; choose *Private* if you do not want it public.
2. Space **Settings -> Variables and secrets**, add secrets: `DEEPSEEK_API_KEY`, `DASHBOARD_PASSWORD`, `NEXUS_APPROVER_TOKEN`, `NEXUS_INTERNAL_TOKEN`.
3. From a clone of this repository, build the upload folder and push it (use a Hugging Face access token with *write* permission as the password):

```bash
sh deploy/space/make_bundle.sh /tmp/nexus-space
cd /tmp/nexus-space && git init && git add -A && git commit -m "NEXUS"
git remote add space https://huggingface.co/spaces/<your-user>/<space-name>
git push space HEAD:main
```

The Space builds the image (about 10 minutes the first time) and serves the dashboard at `https://<your-user>-<space-name>.hf.space`
(log in with `nexus` / your `DASHBOARD_PASSWORD`). Limits: the free tier sleeps after inactivity, the disk is not persistent
(incident history is lost on restart), and only the dashboard port is public. Check Hugging Face's current free-tier terms.
Status: `Dockerfile.space` is written; see `docs/PROJECT_STATE.md` for whether it has been built and run locally.

## 1. Run it locally first

```bash
cp .env.example .env     # set DEEPSEEK_API_KEY, DASHBOARD_PASSWORD, NEXUS_APPROVER_TOKEN, NEXUS_INTERNAL_TOKEN
docker compose up --build
# dashboard: http://localhost:8080   (basic auth: DASHBOARD_USER / DASHBOARD_PASSWORD)
```

CrewAI critic instead of the ADK critic:

```bash
CRITIC_URL=http://crewai-critic:8106 NEXUS_CRITIC_FRAMEWORK=crewai docker compose --profile crewai up --build
```

Experiment switches (set in `.env`): `NEXUS_TOPOLOGY=hub|blackboard`, `NEXUS_PROMPT_VARIANT=default|react|fewshot|persona_sre|persona_auditor`,
`NEXUS_GUARDRAILS=1|0`. After changing a variant, `docker compose up -d --force-recreate` (agents read it at start).

## 2. Put it on a cloud VM (works on any provider)

One small VM running Docker Compose is the cheapest and simplest fit: the agents are always-on, talk to each other
by name, and the shop has a single fault state, so there is nothing to autoscale. Example on Google Compute Engine
(the same steps apply to AWS EC2/Lightsail or an Azure VM):

```bash
gcloud compute instances create nexus --zone=us-central1-a --machine-type=e2-standard-2 \
  --image-family=debian-12 --image-project=debian-cloud --boot-disk-size=30GB --tags=nexus-web
gcloud compute firewall-rules create nexus-web --allow=tcp:443,tcp:80 --target-tags=nexus-web
gcloud compute ssh nexus
# on the VM:
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin git
git clone <your repository URL> nexus && cd nexus
cp .env.example .env && nano .env        # real values; DASHBOARD_PASSWORD is REQUIRED on a public IP
sudo docker compose up -d --build
```

2 vCPU / 8 GB is enough (the images are light; the model runs at the provider). Expect roughly 5-10 GB of images.

## 3. Security checklist before the URL goes public

- [ ] `DASHBOARD_PASSWORD` set (nginx refuses everything without it, including the **Approve** buttons).
- [ ] `NEXUS_APPROVER_TOKEN` set: nginx attaches it server-side, so only the dashboard can approve recoveries.
- [ ] `NEXUS_INTERNAL_TOKEN` set: backend -> orchestrator calls are authenticated.
- [ ] Only port 80/443 open. Put TLS in front (Caddy, a cloud load balancer, or `certbot` on nginx): basic auth over plain HTTP leaks the password.
- [ ] `DEEPSEEK_API_KEY` only in the VM's `.env` or the platform's secret store; never in an image or the repository.
- [ ] A spending limit on the provider account (NEXUS also has per-incident limits: `MAX_*_PER_INCIDENT`).
- [ ] Remember the recovery actions only ever touch the simulated shop container.

## 4. What is shared and what is not

| Thing | Where | Notes |
|---|---|---|
| Incidents, board, events | `nexus-data` volume (SQLite) | back it up with `docker run --rm -v nexus_nexus-data:/d -v $PWD:/b alpine tar czf /b/nexus-data.tgz /d` |
| Shop state (faults, orders) | in memory in `production` | reset by the dashboard's inject flow |
| Kill switch | file inside `orchestrator` | `docker compose exec orchestrator python guardrails/kill_switch.py engage` |

## 5. Other platforms

- **Cloud Run / Azure Container Apps / ECS**: each service becomes one container app; set `NEXUS_AGENT_URL_<AGENT>` on the
  backend and orchestrator to the internal service URLs, `NEXUS_ADVERTISE_HOST` to each agent's own hostname, and keep
  `max instances = 1` for `production` and `orchestrator` (single shop, one investigation at a time). The orchestrator
  returns 429 if a second investigation is requested while one runs. SQLite needs a persistent disk or a swap for a managed DB.
- The agents need no inbound internet access; only outbound HTTPS to the model provider.
