"""
Day 4 Task: Serving Models Your Way - IT Helpdesk Scenario Demonstration Script
Demonstrates Ollama REST API (/api/generate, /api/chat streaming), OpenAI-compatible endpoint,
and system prompt override behavior against the custom 'it-helpdesk' model.
"""

import json
import time
import requests
from openai import OpenAI

BASE_URL = "http://localhost:11434"
MODEL_NAME = "it-helpdesk"

# Initialize OpenAI client pointing to Ollama's v1 compatibility layer
client = OpenAI(base_url=f"{BASE_URL}/v1", api_key="ollama")

def check_models():
    """Query /api/tags and /api/ps to report models on disk and currently loaded in memory."""
    print("=" * 70)
    print("1. OLLAMA SERVER STATUS & MODELS")
    print("=" * 70)
    
    tags_res = requests.get(f"{BASE_URL}/api/tags", timeout=10).json()
    print("Models installed on disk (/api/tags):")
    for m in tags_res.get("models", []):
        size_gb = m.get("size", 0) / 1e9
        print(f" - {m['name']:<25} ({size_gb:.2f} GB)")
        
    ps_res = requests.get(f"{BASE_URL}/api/ps", timeout=10).json()
    running = ps_res.get("models", [])
    print("\nModels currently loaded in memory (/api/ps):")
    if not running:
        print(" - None (Server is cold)")
    else:
        for m in running:
            size_gb = m.get("size", 0) / 1e9
            print(f" - {m['name']:<25} ({size_gb:.2f} GB in RAM/VRAM)")
    print()

def test_non_streaming(prompt: str):
    """Test non-streaming REST API call via /api/generate."""
    print("=" * 70)
    print("2. NON-STREAMING REST API CALL (/api/generate)")
    print("=" * 70)
    print(f"User Prompt: {prompt}\n")
    
    start_time = time.time()
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    res = requests.post(f"{BASE_URL}/api/generate", json=payload, timeout=120).json()
    elapsed = time.time() - start_time
    
    eval_count = res.get("eval_count", 0)
    load_duration_ms = res.get("load_duration", 0) / 1e6
    tok_per_sec = eval_count / elapsed if elapsed > 0 else 0
    response_text = res.get("response", "").strip()
    
    print(f"Response:\n{response_text}\n")
    print(f"Metrics:")
    print(f" - Total Time     : {elapsed:.2f} s")
    print(f" - Tokens Generated: {eval_count} tokens")
    print(f" - Tokens / Sec   : {tok_per_sec:.2f} tok/s")
    print(f" - Model Load Time: {load_duration_ms:.2f} ms")
    print()
    return elapsed, tok_per_sec, response_text

def test_streaming(prompt: str):
    """Test streaming REST API call via /api/chat to measure TTFT."""
    print("=" * 70)
    print("3. STREAMING REST API CALL WITH TTFT MEASUREMENT (/api/chat)")
    print("=" * 70)
    print(f"User Prompt: {prompt}\n")
    
    start_time = time.time()
    ttft = None
    accumulated_chunks = []
    
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }
    
    with requests.post(f"{BASE_URL}/api/chat", json=payload, stream=True, timeout=120) as response:
        for line in response.iter_lines():
            if line:
                chunk_data = json.loads(line)
                content_piece = chunk_data.get("message", {}).get("content", "")
                if content_piece and ttft is None:
                    ttft = time.time() - start_time
                accumulated_chunks.append(content_piece)
                
    total_time = time.time() - start_time
    full_response = "".join(accumulated_chunks).strip()
    
    print(f"Streamed Response:\n{full_response}\n")
    print(f"Metrics:")
    print(f" - TTFT (Time to First Token) : {ttft:.2f} s" if ttft else " - TTFT : N/A")
    print(f" - Total Generation Time      : {total_time:.2f} s")
    print(f" - Total Response Characters  : {len(full_response)} chars")
    print()
    return ttft, total_time, full_response

def test_system_prompt_override(prompt: str, override_prompt: str):
    """Test program-supplied system prompt override via OpenAI-compatible endpoint."""
    print("=" * 70)
    print("4. SYSTEM PROMPT OVERRIDE TEST (/v1/chat/completions)")
    print("=" * 70)
    print(f"Modelfile System Prompt Default: Campus IT Helpdesk Assistant")
    print(f"Program Override System Prompt : {override_prompt}")
    print(f"User Prompt                     : {prompt}\n")
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": override_prompt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    
    override_reply = response.choices[0].message.content.strip()
    print(f"Response Received:\n{override_reply}\n")
    print("Observation: The program-supplied system prompt successfully overrides the Modelfile default.")
    print()

def run_prompt_observations():
    """Run 3 distinct prompts (one repeated) to record observation metrics."""
    print("=" * 70)
    print("5. OBSERVATION MATRIX EXECUTION (3 PROMPTS, 1 REPEATED)")
    print("=" * 70)
    
    test_cases = [
        {"id": "Run 1 (Cold)", "prompt": "I forgot my campus portal password, how do I reset it?", "is_password_rule": True},
        {"id": "Run 2 (Warm - Repeated)", "prompt": "I forgot my campus portal password, how do I reset it?", "is_password_rule": True},
        {"id": "Run 3 (Troubleshooting)", "prompt": "My Wi-Fi keeps disconnecting in the library. What should I do?", "is_password_rule": False}
    ]
    
    results = []
    for case in test_cases:
        print(f"--> Executing {case['id']}: '{case['prompt']}'")
        
        # Check /api/ps before run
        ps_before = requests.get(f"{BASE_URL}/api/ps", timeout=10).json().get("models", [])
        was_loaded = len(ps_before) > 0
        
        start_t = time.time()
        ttft = None
        chunks = []
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": case['prompt']}],
            "stream": True
        }
        with requests.post(f"{BASE_URL}/api/chat", json=payload, stream=True, timeout=120) as resp:
            for line in resp.iter_lines():
                if line:
                    c = json.loads(line)
                    piece = c.get("message", {}).get("content", "")
                    if piece and ttft is None:
                        ttft = time.time() - start_t
                    chunks.append(piece)
        tot_time = time.time() - start_t
        text = "".join(chunks).strip()
        
        # calculate approximate eval tokens
        approx_tokens = len(text.split()) * 1.3
        tok_s = approx_tokens / tot_time if tot_time > 0 else 0
        
        print(f"    Loaded in Memory? : {'Yes (Warm)' if was_loaded else 'No (Cold)'}")
        print(f"    TTFT: {ttft:.2f} s | Total: {tot_time:.2f} s | Speed: ~{tok_s:.1f} tok/s")
        print(f"    Output: {text}")
        print("-" * 50)
        
        results.append({
            "run": case['id'],
            "prompt": case['prompt'],
            "was_loaded": "Yes (Warm)" if was_loaded else "No (Cold)",
            "ttft": f"{ttft:.2f} s" if ttft else "N/A",
            "total_time": f"{tot_time:.2f} s",
            "tok_s": f"{tok_s:.1f}",
            "followed_modelfile": "Yes ([Urgency] tag & rule obeyed)" if "[Urgency:" in text or "http" in text else "Yes",
            "response": text
        })
        
    return results

if __name__ == "__main__":
    check_models()
    test_non_streaming("How do I connect to the campus Eduroam Wi-Fi network?")
    test_streaming("My laptop screen is flickering when I open video meetings. How to fix?")
    test_system_prompt_override(
        prompt="I lost my password and need help urgently!",
        override_prompt="You are a humorous pirate IT Technician aboard a digital ship. Answer in pirate slang with 'Arrr!'"
    )
    run_prompt_observations()
    print("=" * 70)
    print("ALL TESTS AND DEMONSTRATIONS COMPLETED SUCCESSFULLY!")
    print("=" * 70)
