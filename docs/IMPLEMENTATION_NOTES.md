# Implementation notes

This file describes what the source tree contains. An earlier draft of this document was titled as if the project were finished. Those completion claims are not repeated here. Nothing in this note was re-measured at runtime.

In this repository, **Titans** means the neural memory module in `brain/titans.py` only. It does not name an agent or the proxy.

## Neural memory (`brain/titans.py`)

`NeuralMemory` is an embedding (`vocab_size` 100, `embed_dim` 16), an LSTM (`hidden_dim` 32), and a two-layer MLP (`Linear`, `ReLU`, `Linear`). Characters are mapped with `ord(c) % vocab_size`.

`SecurityAgent.calculate_surprise` returns next-character cross-entropy under `torch.no_grad`. `update_memory` runs one Adam step (`learning_rate` 0.01) with backpropagation. `is_anomalous` is `surprise_score > threshold`, and the default `threshold` argument is `4.2`.

`SessionManager` stores one `SecurityAgent` per session id. The class name `SecurityAgent` is only a wrapper around that memory module.

Older notes called this a Titans MAC architecture. The implemented network is the embedding, LSTM, and MLP above. There is no separate associative-memory update in the file beyond the LSTM state and the single Adam step in `update_memory`.

## Analysis server (`brain/server.py`)

FastAPI app `Mnemosyne Brain` on port 5000:

| Method | Path | Behavior in source |
| --- | --- | --- |
| GET | `/health` | Returns `status` and `active_sessions` |
| POST | `/analyze` | Scores `text` and schedules `update_memory` on a background task |
| GET | `/sessions` | Returns the count and ids held by `SessionManager` |

`POST /analyze` logs the request's `session_id` and then always loads the agent for the fixed id `global_demo_session`. The proxy's session id is not used to select a memory. On an exception the handler returns `surprise_score` `999.0` and `is_anomaly` true.

## Proxy (`proxy/src/main.rs`)

Axum process. It reads `GROQ_API_KEY` and `BRAIN_URL` (default `http://mnemosyne-brain:5000`) and listens on `0.0.0.0:8080`.

| Method | Path | Behavior in source |
| --- | --- | --- |
| POST | `/chat/completions` | Scores the latest `user` message, then either rejects or forwards |
| GET | `/health` | Returns `status` and `service` |

The session id sent to the brain is `session_` plus the MD5 hex of the first message's content. If the brain reports `is_anomaly`, the proxy responds with HTTP 403 and `error` `security_violation`. If the brain cannot be contacted or its JSON cannot be parsed, the proxy responds with HTTP 503. Otherwise the request JSON is POSTed to `https://api.groq.com/openai/v1/chat/completions`. The response body is buffered with `resp.text()` and returned as a whole. The handler does not stream. If `model` is omitted it sets `llama-3.1-8b-instant`.

## eBPF probe (`ebpf_probe/`)

`xdp_firewall` in `ebpf_program/src/main.rs` returns `XDP_PASS` for every packet. It does not read packet data and does not drop traffic. `user_loader` loads that object and attaches it to an interface (`--iface`, default `lo`). The image command in `ebpf_probe/Dockerfile` passes `--iface eth0`.

## Docker

| File | What the Dockerfile does |
| --- | --- |
| `brain/Dockerfile` | Single-stage `python:3.11-slim` image. Installs a CPU PyTorch wheel, then `requirements.txt`. |
| `proxy/Dockerfile` | Multi-stage image: `rust:latest` builder, `debian:bookworm-slim` runtime. |
| `ebpf_probe/Dockerfile` | Multi-stage image that builds the loader. |

`docker-compose.yml` builds and starts only `mnemosyne-brain` and `mnemosyne-proxy` on a bridge network named `mnemosyne-net`. The proxy `depends_on` the brain. The compose file has no `healthcheck` field. Host ports 5000 and 8080 are published. The brain enables CORS for any origin. The proxy enables a Tower CORS layer that allows any origin, method, and header.

## Dashboard (`dashboard/index.html`)

A static page. It requests `http://localhost:5000/health` and `http://localhost:8080/health`, and it can POST example prompts to the proxy. The eBPF row is not tied to a probe of the loader.

## Simulation script (`tests/attack_sim.py`)

This is a script that talks to a running proxy. The repository has no unit-test module, no test runner config, and no CI workflow. The script:

1. Sends a short warmup set (each prompt three times).
2. Sends one benign chat completion.
3. Sends a five-prompt sequence and returns on the first HTTP 403.
4. Sends five short completions and treats the average latency of HTTP 200 samples as acceptable when it is under 2000 ms.
5. Sends a two-turn message list and one hyphenated string.

It writes `test_results.json` in the current working directory. That file is gitignored. Running the script needs a reachable proxy and a Groq key. Those runs were not repeated for this note.

## Earlier completion claims that the source does not support

The previous text of this document asserted the items below. They are listed so the gap is explicit. They are not descriptions of current behavior.

- The project was described as implementation-complete, fully operational, production-ready, and ready to launch.
- Groq responses were described as streamed. The proxy buffers the body.
- Memory was described as isolated per user or per session. The server always uses `global_demo_session`.
- eBPF was described as inspecting and blocking packets. The program returns `XDP_PASS`.
- A latency target under 500 ms, a typical time of about 230 ms, a per-stage breakdown (about 2 ms, 30 ms, 2 ms, 200 ms, 2 ms), and sub-millisecond proxy overhead. No measurement of those figures is in the source.
- Memory use of 210 MB, CPU under 5% idle and about 20% under load, and startup of about 30 seconds. Not present in the source.
- Docker Compose health checks. The services expose `/health`; the compose file does not check them.
- Multi-stage Dockerfiles for every image. The brain Dockerfile is single-stage.
- Network isolation as a delivered property. There is a bridge network; ports are published and CORS allows any origin.
- An OpenAI-compatible API in general. One route, `POST /chat/completions`, is implemented.
- An anomaly threshold of 3.5. The default argument in `is_anomalous` is 4.2. A docstring in the same function previously said 4.5.
- Every brain or proxy failure returned HTTP 403. Unreachable-brain failures in the proxy return HTTP 503. The brain process itself returns `is_anomaly: true` on an internal exception, which the proxy then turns into 403.
- Counts of 16 files, about 1,200 lines, 2 Docker images, 4 API endpoints, and 3 test scenarios. The tree has more files than that list, three Dockerfiles, five HTTP routes across the two servers, and four routines plus warmup in `attack_sim.py`.
- Links to `walkthrough.md`, `implementation_plan.md`, and `file://` paths under a local `ebpf_agent` directory. Those files are not in this repository.
- Jailbreak and obfuscated prompts were marked as blocked. The script attempts those prompts. The source does not record a verified outcome.
- A checked-in MIT license. There is no license file.
