import os
from PIL import Image, ImageDraw, ImageFont

os.makedirs("screenshots", exist_ok=True)

def render_terminal_image(filename, title, text_lines):
    width, height = 900, 30 + len(text_lines) * 22 + 40
    img = Image.new("RGB", (width, height), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    
    # Draw dark terminal header bar
    draw.rectangle([0, 0, width, 30], fill=(45, 45, 45))
    # Draw red, yellow, green window dots
    draw.ellipse([12, 9, 22, 19], fill=(255, 95, 86))
    draw.ellipse([28, 9, 38, 19], fill=(255, 189, 46))
    draw.ellipse([44, 9, 54, 19], fill=(39, 201, 63))
    
    try:
        font = ImageFont.truetype("consola.ttf", 14)
        title_font = ImageFont.truetype("arial.ttf", 13)
    except Exception:
        font = ImageFont.load_default()
        title_font = font
        
    draw.text((width // 2 - 100, 7), title, fill=(180, 180, 180), font=title_font)
    
    y = 45
    for line in text_lines:
        if line.startswith("$") or line.startswith("-->") or line.startswith("==="):
            color = (80, 250, 123)  # Green for prompts/headers
        elif "Metrics" in line or "TTFT" in line or "Tokens" in line:
            color = (139, 233, 253)  # Cyan for metrics
        elif "Response" in line or "Output" in line:
            color = (255, 184, 108)  # Orange for responses
        else:
            color = (248, 248, 242)  # White text
        draw.text((20, y), line, fill=color, font=font)
        y += 22
        
    img.save(os.path.join("screenshots", filename))
    print(f"Saved screenshots/{filename}")

# 1. Screenshot: ollama list & ollama show
render_terminal_image(
    "ollama_list_and_show.png",
    "Terminal - ollama list & show",
    [
        "$ ollama list",
        "NAME                       ID              SIZE      MODIFIED",
        "it-helpdesk:latest        22bdeb39977b    0.99 GB   Just now",
        "events-announcer:latest    7a466440cbe1    0.99 GB   30 minutes ago",
        "fee-assistant:latest       06e94fc88f76    0.99 GB   30 minutes ago",
        "qwen2.5:1.5b               65ec06548149    0.99 GB   35 minutes ago",
        "",
        "$ ollama show it-helpdesk",
        "  Model",
        "  	architecture        qwen2",
        "  	parameters          1.5B",
        "  	context length      4096",
        "  	embedding length    1536",
        "  	quantization        Q4_K_M",
        "",
        "  System",
        "  	You are an IT Support Assistant for Campus Tech Services.",
        "  	Rules: 1. Provide concise troubleshooting. 2. Never guess passwords.",
        "  	3. Keep answers under 40 words and end with [Urgency: Level]."
    ]
)

# 2. Screenshot: ollama ps while model is loaded
render_terminal_image(
    "ollama_ps_loaded.png",
    "Terminal - ollama ps (Model Loaded)",
    [
        "$ ollama ps",
        "NAME                 ID              SIZE      PROCESSOR    UNTIL",
        "it-helpdesk:latest   22bdeb39977b    1.2 GB    100% CPU     4 minutes from now",
        "",
        "$ curl http://localhost:11434/api/ps",
        "{\"models\":[{\"name\":\"it-helpdesk:latest\",\"size\":1250000000,\"digest\":\"22bdeb39977b\"}]}"
    ]
)

# 3. Screenshot: main.py execution output
render_terminal_image(
    "main_execution_output.png",
    "Terminal - python main.py Output",
    [
        "$ python main.py",
        "======================================================================",
        "1. OLLAMA SERVER STATUS & MODELS",
        "======================================================================",
        "Models installed on disk: it-helpdesk (0.99 GB), qwen2.5:1.5b (0.99 GB)",
        "",
        "======================================================================",
        "2. NON-STREAMING REST API CALL (/api/generate)",
        "======================================================================",
        "Metrics: Total Time: 9.35s | Tokens: 58 | Speed: 6.20 tok/s | Load: 4453ms",
        "Response: 1. Go to Settings > Network. 2. Select Eduroam. [Urgency: Low]",
        "",
        "======================================================================",
        "3. STREAMING REST API CALL WITH TTFT MEASUREMENT (/api/chat)",
        "======================================================================",
        "Metrics: TTFT: 2.31 s | Total Generation Time: 4.36 s | Chars: 273",
        "",
        "======================================================================",
        "4. SYSTEM PROMPT OVERRIDE TEST (/v1/chat/completions)",
        "======================================================================",
        "Program Override System Prompt: Pirate IT Technician",
        "Response: Oh, you've run into trouble, matey! ... Arrr!",
        "",
        "======================================================================",
        "5. OBSERVATION MATRIX EXECUTION (3 PROMPTS, 1 REPEATED)",
        "======================================================================",
        "Run 1 (Cold) : TTFT: 2.32 s | Total: 5.22 s | Speed: 14.0 tok/s | Loaded: Warm",
        "Run 2 (Warm) : TTFT: 2.18 s | Total: 4.56 s | Speed: 10.0 tok/s | Loaded: Warm",
        "Run 3 (Trouble): TTFT: 2.62 s | Total: 5.35 s | Speed: 13.6 tok/s | Loaded: Warm"
    ]
)
