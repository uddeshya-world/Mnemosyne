# Project Mnemosyne - Quick Start Guide

## Prerequisites

- Docker, to build and run the brain and proxy
- A Groq API key from https://console.groq.com/
- Python 3.11 or newer, if you run `tests/attack_sim.py`

The eBPF loader is documented separately in `ebpf_probe/README_EBPF.md`. It is not started by `docker-compose.yml`.

## Setup

### Step 1: Set the Groq API key

The proxy process exits at startup if `GROQ_API_KEY` is unset (`proxy/src/main.rs`).

**Windows (PowerShell):**

```powershell
$env:GROQ_API_KEY="gsk_your_actual_key_here"
```

**Linux/Mac:**

```bash
export GROQ_API_KEY=gsk_your_actual_key_here
```

`.env.example` at the repository root lists the same variable name. `docker-compose.yml` passes `GROQ_API_KEY` through to the proxy service.

### Step 2: Build and start the services

```bash
docker-compose up --build
```

The compose file builds `./brain` and `./proxy`, publishes ports 5000 and 8080, and places both containers on the `mnemosyne-net` bridge. The proxy `depends_on` the brain. There is no `healthcheck` field.

Log lines emitted by the current processes include:

```
mnemosyne-brain | INFO:     Application startup complete.
mnemosyne-proxy | Mnemosyne Proxy listening on 0.0.0.0:8080
```

### Step 3: Check the health routes

```bash
curl http://localhost:8080/health
curl http://localhost:5000/health
```

The handlers return JSON of this shape:

```json
{"status":"healthy","service":"mnemosyne-proxy"}
{"status":"healthy","active_sessions":0}
```

`active_sessions` is the number of entries in the in-process session map. After `POST /analyze` has run, that count is the single forced id `global_demo_session`, not a count of proxy clients.

### Step 4: Run the simulation script

```bash
python tests/attack_sim.py
```

The script requires the proxy to be reachable. It runs a warmup, a benign request, a gradual prompt sequence, a latency loop, and two further scenarios (a two-turn message list and a hyphenated string). The latency loop in the script treats an average under 2000 ms as acceptable. Results are written to `test_results.json` in the current directory. That filename is listed in `.gitignore`.

### Step 5: Send a request

```bash
curl -X POST http://localhost:8080/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3-8b-8192",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in one sentence."}
    ]
  }'
```

The proxy forwards `model` when it is present. HTTP 200 is the Groq body. HTTP 403 means the brain set `is_anomaly`. HTTP 503 means the brain could not be used.

## Troubleshooting

### "GROQ_API_KEY must be set"

Export the variable in the environment that runs `docker-compose up`, or provide it in a `.env` file that Compose reads for substitution.

### The proxy image fails to build

The proxy Dockerfile compiles Rust inside the image. To rebuild that image without using the cache:

```bash
docker-compose build --no-cache proxy
```

### The brain container exits

```bash
docker logs mnemosyne-brain
```

### Port 5000 or 8080 is already in use

Stop the process bound to that port, or change the host side of the port mapping in `docker-compose.yml`.

**Windows:**

```bash
netstat -ano | findstr :8080
taskkill /PID <PID> /F
```

**Linux/Mac:**

```bash
lsof -ti:8080 | xargs kill -9
```

## Stopping the services

```bash
docker-compose down
```

`docker-compose down -v` also removes named volumes. The current compose file does not declare any volumes.

## Logs

```bash
docker-compose logs -f
docker-compose logs -f mnemosyne-proxy
docker-compose logs -f mnemosyne-brain
```

## Further detail

- Request path and module behavior: `README.md`
- What the source shows, and which earlier completion claims it does not support: `docs/IMPLEMENTATION_NOTES.md`
- Default anomaly threshold: the `threshold` argument of `is_anomalous` in `brain/titans.py` (currently `4.2`)
