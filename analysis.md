# Written Analysis: Serving Models Your Way (Ollama, Modelfiles, REST API & vLLM)

**Course:** Agentic AI: Foundations and Open-Source Practice  
**Unit:** Unit 2: Open LLMs and Local Serving (Sub-topics 2.3 & 2.4)  
**Task Title:** Day 4 Task — Serving Models Your Way on a Scenario of Your Own  
**Scenario:** Campus IT Helpdesk Assistant (`it-helpdesk`)  
**Repository:** `Day4_Task`

---

## 1. Scenario Overview

For this task, the chosen domain is **Campus Tech Services**, an automated IT support desk assistant designed to assist university students and faculty with technical troubleshooting (Wi-Fi configuration, screen flickering, software issues, and account security).

In an IT support environment, model behavior must be strictly constrained:
1. **Determinism & Accuracy:** Troubleshooting steps must be direct, logical, and structured.
2. **Security Safeguards:** The assistant must **never** ask for or attempt to guess user passwords, directing all credential issues to the secure self-service portal (`https://it.campus.edu/reset`).
3. **Structured Format:** To integrate with campus ticket queues, answers must remain concise (under 40 words) and terminate with an explicit ticket urgency tag (e.g. `[Urgency: Low/Medium/High]`).

---

## 2. Explanation of Concepts

### 2.1 What is Ollama? Structure, Storage, and Request Lifecycle
**Ollama** is an open-source local LLM serving framework designed to simplify downloading, packaging, managing, and running open-weights language models on desktop and edge hardware.

Ollama consists of three core components:
1. **Ollama Server Daemon (`ollama serve`):** A background service running on port `11434`. It manages GPU/RAM memory allocation, handles model weight loading/unloading, executes matrix operations via GGUF/ggml backends, and exposes REST endpoints.
2. **Ollama Command Line Interface (CLI `ollama`):** A developer-facing CLI tool used to pull models (`ollama pull`), inspect metadata (`ollama show`), monitor active memory (`ollama ps`), and interact with models (`ollama run`).
3. **REST API & OpenAI Compatibility Layer:** HTTP endpoints (`/api/generate`, `/api/chat`, and `/v1/chat/completions`) that allow external applications and agent frameworks to interact with loaded models programmatically.

#### Model Storage and Request Execution Lifecycle
Model weights are stored locally in GGUF quantized format under `%USERPROFILE%\.ollama\models\` (on Windows) or `~/.ollama/models/` (on Linux/macOS) organized into manifest and blob directories.

When a client sends a request (e.g. `"How do I connect to campus Wi-Fi?"`):
1. **HTTP Ingestion:** The Ollama server receives the JSON payload at `http://localhost:11434/api/chat`.
2. **Model State Verification:** The server checks `/api/ps`. If `it-helpdesk` is not currently in memory, Ollama loads the GGUF model tensors from disk into system RAM/VRAM.
3. **Tokenization:** The text prompt is processed by the model's tokenizer into numerical token IDs.
4. **Autoregressive Inference:** The model executes forward passes through transformer layers. Each output token is generated based on context probability distributions.
5. **Decoding & Streaming:** Tokens are decoded back into text characters and returned over an HTTP connection either as a buffered JSON response or as a real-time chunked stream.

---

### 2.2 What is a Modelfile? Instructions, Custom Models & Disk Efficiency
A **Modelfile** is a declarative configuration manifest (similar to a Dockerfile) that customizes an existing base model's default behavior, system prompt, and hyperparameter configuration.

In our `Day4_Task/Modelfile`, the following instructions were used:
- **`FROM qwen2.5:1.5b`:** Specifies `qwen2.5:1.5b` (a 1.5-billion parameter base model) as the underlying neural network weights.
- **`PARAMETER temperature 0.2`:** Lowers sampling randomness to ensure repeatable, deterministic technical instructions.
- **`PARAMETER num_ctx 4096`:** Sets context window size to 4,096 tokens to accommodate multi-turn troubleshooting conversations.
- **`PARAMETER repeat_penalty 1.15`:** Prevents repetitive phrasing in step-by-step technical lists.
- **`SYSTEM """..."""`:** Establishes the default persona, enforcing security rules (never guess passwords; direct users to reset link) and requiring answers under 40 words with `[Urgency: Level]` tagging.

```dockerfile
FROM qwen2.5:1.5b
PARAMETER temperature 0.2
PARAMETER num_ctx 4096
PARAMETER repeat_penalty 1.15
SYSTEM """
You are an IT Support Assistant for Campus Tech Services.
Rules:
1. Provide concise, step-by-step technical troubleshooting.
2. Never ask for or guess user passwords; direct password reset requests to https://it.campus.edu/reset.
3. Keep answers under 40 words and end every response with a tag like [Urgency: Low], [Urgency: Medium], or [Urgency: High].
"""
```

#### What is a Custom Model Made Of?
Building a custom model via `ollama create it-helpdesk -f Modelfile` does **not** download or duplicate model parameter weights. A custom model consists solely of a lightweight **JSON manifest blob** (a few kilobytes) stored in Ollama's registry. This manifest points to the existing GGUF weight layers of `qwen2.5:1.5b` on disk while overriding the default system prompt and parameter pointers.

---

### 2.3 System Prompt Override Mechanics
When an application calls `it-helpdesk` through the OpenAI-compatible endpoint (`/v1/chat/completions`) and supplies its own `system` message (e.g. `"You are a pirate IT Technician..."`), **the program's system prompt wins**, overriding the Modelfile's system prompt.

#### Why This is the Correct Design for Agent Frameworks
This hierarchy is essential for agentic software development:
- **Modelfile System Prompt = Baseline Safeguard / Default Personality:** Acts as a sensible fallback when no explicit runtime instructions are provided.
- **Program System Prompt = Dynamic Context Injection:** Agent frameworks (like LangChain, AutoGen, or custom agent loops) must dynamically inject real-time context—such as user session state, available tool schemas, retrieved RAG documents, and scratchpad memory—on a per-turn basis. If the Modelfile forced immutability, agent frameworks could not reconfigure behavior dynamically.

---

### 2.4 REST API Endpoints & OpenAI Compatibility
Ollama exposes two main native endpoints and one compatibility endpoint:
1. **`/api/generate`:** Accepts a raw text prompt string (`"prompt": "..."`). Suitable for simple text completion tasks.
2. **`/api/chat`:** Accepts a structured array of message objects (`"messages": [{"role": "user", "content": "..."}]`). Preserves role definitions (`system`, `user`, `assistant`).
3. **`/v1/chat/completions`:** Implements OpenAI's standard REST API schema.

#### Importance of OpenAI Compatibility
The `/v1/chat/completions` endpoint allows developers to write agent code using standard SDKs (`from openai import OpenAI`). When moving from local desktop prototyping (Ollama) to production serving infrastructure (vLLM, TGI, or cloud endpoints), **zero client application code changes are required**—only the `base_url` parameter needs to be updated.

---

### 2.5 Streaming, TTFT, and Perceived Latency
LLM generation consists of two distinct computational phases:
1. **Prefill Phase:** The model processes the input prompt tokens in parallel, populating the initial Key-Value (KV) cache.
2. **Decode Phase:** The model generates output tokens sequentially (autoregressively), one token at a time.

- **TTFT (Time To First Token):** The time elapsed from sending the request until the client receives the very first generated token. TTFT measures the prefill latency plus initial network overhead.
- **Total Time:** The cumulative duration required to complete the entire generation sequence.

#### Why Streaming Improves User Experience
In non-streaming requests (`stream: false`), the user sees nothing until the entire generation is finished, resulting in high perceived latency. In streaming requests (`stream: true`), tokens are transmitted over HTTP chunked transfer as soon as they are decoded. Even if total generation time remains 5 seconds, a TTFT of **2.3 seconds** allows the user to begin reading immediately, creating a responsive experience.

---

### 2.6 Memory & Concurrency Controls
- **`num_ctx`:** Sets the maximum context token window. Larger `num_ctx` values linearly and quadratically increase VRAM/RAM required for storing Key-Value tensors.
- **`OLLAMA_KEEP_ALIVE`:** Controls how long a model remains loaded in memory after a request completes (default: 5 minutes). On active desktops, keeping models warm eliminates model reload overhead (~4.5 seconds for cold start) on subsequent queries.
- **`OLLAMA_NUM_PARALLEL`:** Specifies how many concurrent requests Ollama will attempt to process by splitting context windows.

---

### 2.7 GPU Memory Waste, PagedAttention, and Prefix Caching

#### Why Simple Servers Waste Memory on KV Cache
Traditional LLM serving frameworks pre-allocate contiguous memory blocks for the KV cache based on the maximum context length (`num_ctx`). Because actual request lengths vary unpredictable, this leads to severe **internal memory fragmentation** and over-reservation (up to 60–80% of VRAM is wasted on empty, reserved tensor slots).

#### How PagedAttention Resolves Memory Waste
**PagedAttention** (pioneered by vLLM) applies virtual memory paging principles to LLM inference:
- KV caches are partitioned into small, non-contiguous fixed-size physical memory blocks (e.g. 16 tokens per block).
- A dynamic **Block Table** maps virtual token sequence positions to physical memory blocks allocated on demand.
- **Result:** Memory waste is reduced to under 4% (occurring only in the last unfilled block of a sequence), allowing 3x–5x more requests to fit into GPU memory simultaneously.

#### The Role of Prefix Caching for Agents
Agent workflows frequently resend identical system prompts (e.g. 900-token IT support instructions) across multi-turn user turns. **Prefix Caching** allows multiple requests to share physical KV cache blocks containing the common prefix. Instead of recomputing prompt prefill on every turn, the server reuses cached KV blocks instantly, reducing TTFT to near-zero.

---

### 2.8 Batching Mechanics & Trade-Off Metrics

#### Static Batching vs. Continuous Batching
- **Static Batching:** Requests are grouped into fixed batch sizes. The GPU must wait until the longest request in the batch completes before freeing memory and accepting new requests. Shorter requests sit idle while waiting for longer requests to terminate.
- **Continuous Batching (Iteration-level Scheduling):** Operates at the individual token generation step. As soon as a request finishes generating its end-of-sequence token, it is evicted from the batch and a new incoming request is inserted into the execution queue immediately.

#### System Performance Trade-Off Metrics
- **Throughput:** Total tokens generated across all users per second (tokens/sec/server).
- **TTFT (Time to First Token):** Latency before initial token delivery.
- **TPOT (Time Per Output Token):** Inter-token generation latency during decoding.
- **P95 Latency:** 95th percentile completion time for requests.

#### The Fundamental Trade-Off
Raising throughput requires larger batch sizes (`--max-num-seqs`), saturating GPU compute cores. However, larger batch sizes force GPU memory bandwidth and compute attention to be shared across more active sequences, which **increases per-request TTFT and TPOT**. Optimization requires balancing throughput against latency SLAs based on user count.

---

## 3. Comparison Table: Ollama vs. vLLM

| Basis for Comparison | Ollama | vLLM |
| :--- | :--- | :--- |
| **Built for (who and how many users)** | Individual developers, local desktop experimentation, single-user desktop workflows (1–3 concurrent users). | High-concurrency production deployments, enterprise APIs, multi-tenant cloud services (10–1000+ concurrent users). |
| **Hardware it needs** | Standard laptop/desktop CPU, Apple Silicon, or a single consumer GPU (8GB–16GB RAM/VRAM). | High-performance workstation or server-grade GPUs (e.g. NVIDIA A100, H100, L40S) with high VRAM bandwidth. |
| **How it handles several requests at once** | Processes requests sequentially by default; queues concurrent queries or relies on simple context splitting (`OLLAMA_NUM_PARALLEL`). | Continuous batching (iteration-level scheduling) dynamically interleaves dozens of requests simultaneously without idle GPU cycles. |
| **How it manages memory** | Allocates static contiguous memory blocks for model weights and KV cache per request; prone to memory fragmentation. | PagedAttention maps KV caches into non-contiguous 16-token virtual blocks; prefix caching reuses shared prompt blocks across streams. |
| **Setup effort and model format** | Single executable installer, instant GGUF model pulling, simple Modelfile syntax. Extremely low setup effort. | Requires Linux environment, Python CUDA dependencies, HuggingFace unquantized/AWQ weights, and command-line serve flags. |
| **Your choice if only you use the scenario, and why** | **Ollama:** Simple setup, minimal resource consumption, and zero configuration needed for single-user local IT Helpdesk testing on a laptop. | Not recommended for local solo use due to heavy setup overhead and unneeded infrastructure complexity. |
| **Your choice if 100 people use it at once, and why** | Not viable; sequential queuing causes massive request backlogs and high response latency for multi-user workloads. | **vLLM:** Essential; PagedAttention and continuous batching allow 100 student queries to run concurrently on shared GPU memory. |

---

## 4. Minimal Implementation & Empirical Observations

### 4.1 Script Structure (`main.py`)
The implementation in `Day4_Task/main.py` executes:
1. **Status Checks:** Queries `/api/tags` (models on disk) and `/api/ps` (models loaded in memory).
2. **Non-Streaming Call (`/api/generate`):** Evaluates single-request execution, load duration, total generation time, and tokens/sec.
3. **Streaming Call (`/api/chat`):** Measures TTFT and total generation time.
4. **System Prompt Override (`/v1/chat/completions`):** Tests program prompt override against Modelfile default.
5. **Observation Matrix:** Runs 3 distinct queries (with 1 repeated query) to observe cold vs. warm start latency.

---

### 4.2 Observation Matrix Table

| Run ID | User Prompt | Model Memory State (`/api/ps`) | TTFT (s) | Total Time (s) | Generation Speed (tok/s) | Modelfile Rule Followed? | Program Override Applied? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Non-Streaming `/api/generate`** | How do I connect to Eduroam Wi-Fi? | Cold Load (4453 ms load) | N/A | 9.35 s | 6.20 tok/s | Yes (`[Urgency: Low]` attached, <40 words) | No (Modelfile default used) |
| **Streaming `/api/chat`** | Screen flickering in video meetings? | Warm (`it-helpdesk` loaded) | 2.31 s | 4.36 s | 12.8 tok/s | Yes (`[Urgency: Low]` attached, step-by-step) | No (Modelfile default used) |
| **Override `/v1/chat/completions`** | I lost my password and need help! | Warm (`it-helpdesk` loaded) | N/A | 3.80 s | 14.2 tok/s | No (Overridden by pirate persona) | **Yes** (Responded in pirate slang: *"Ahoy matey! Arrr!"*) |
| **Run 1 (Cold Start)** | Password reset query | Warm in VRAM (1.17 GB) | 2.32 s | 5.22 s | 14.0 tok/s | Yes (Password reset link `https://...` referenced) | No (Modelfile default used) |
| **Run 2 (Warm Repeated)** | Password reset query (Duplicate) | Warm in VRAM (1.17 GB) | 2.18 s | 4.56 s | 10.0 tok/s | Yes (Concise reset steps, <40 words) | No (Modelfile default used) |
| **Run 3 (Troubleshooting)** | Wi-Fi disconnecting in library | Warm in VRAM (1.17 GB) | 2.62 s | 5.35 s | 13.6 tok/s | Yes (Step-by-step steps & `[Urgency: Low]`) | No (Modelfile default used) |

#### Written Observations and Insights
1. **Cold Start vs. Warm Start Penalty:** The initial non-streaming request required **4,453 ms (4.45 seconds)** just to load model weights from disk into RAM/VRAM. Subsequent requests ran warm with load times under **10 ms**, resulting in significantly faster response times.
2. **TTFT vs. Total Time Impact:** In streaming requests, the user receives the first token in **2.31 seconds**, whereas non-streaming required over **9 seconds** before delivering output. This demonstrates why streaming is vital for interactive user interfaces.
3. **Modelfile Rule Enforcement:** The custom model strictly adhered to the SYSTEM instructions: answers were formatted as step-by-step bullet points under 40 words, credential requests were redirected to `https://it.campus.edu/reset`, and responses ended with `[Urgency: Low]`.
4. **Program Override Precedence:** Supplying a pirate persona system prompt through `/v1/chat/completions` completely overrode the default IT Helpdesk persona, proving that program-level prompts take precedence over Modelfiles.

---

## 5. Suitability and Conclusion

### 5.1 When Single-Machine Ollama is Sufficient
Single-machine Ollama (running locally on CPU or consumer GPU) is ideal for:
- **Individual Developer Prototyping:** Rapid iteration of Modelfiles, system prompts, and local agent tools.
- **Single-User Desktop Applications:** Personal AI assistants, local document Q&A (RAG), and offline code generation.
- **Privacy-Sensitive Local Tasks:** Processing confidential data locally without sending traffic to third-party cloud APIs.

### 5.2 When Shared Deployment Requires vLLM
Moving to a high-concurrency server framework like **vLLM** becomes necessary when:
- **Serving Multi-Tenant Workloads:** Serving tens to hundreds of concurrent users simultaneously (e.g. 100 students accessing the Campus IT Helpdesk during finals week).
- **Maximizing Hardware ROI:** Operating expensive GPU clusters where static allocation would leave tensor cores idle up to 70% of the time.
- **High-Frequency Multi-Turn Agent Swarms:** Running automated multi-agent systems that repeatedly send shared system prompts, where prefix caching and continuous batching drastically reduce latency and operational costs.

### 5.3 Summary Statement
Local serving via Ollama provides an easy-to-use foundation for single-user LLM application development, using Modelfiles to establish baseline model personalities. However, when transitioning from local prototypes to production environments serving concurrent traffic, architecture must evolve to specialized serving engines like vLLM that leverage PagedAttention and continuous batching to unlock hardware scalability.
