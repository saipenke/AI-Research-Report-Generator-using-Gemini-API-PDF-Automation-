# 🤖 Multi-Agent AI Research PDF Generator

A production-style multi-agent AI system that automatically generates professional
PDF research reports on any topic using a three-agent pipeline.

```
User Topic
  → 1️⃣  Research Agent   (web search + LLM synthesis)
  → 2️⃣  Validator Agent  (quality check + de-duplication)
  → 3️⃣  PDF Generator    (professional ReportLab PDF)
  → generated_reports/<Topic>_Report.pdf
```

---

## 📁 Project Structure

```
research_pdf_agent/
│
├── agents/
│   ├── __init__.py
│   ├── research_agent.py        # Agent 1: Web research + LLM synthesis
│   ├── validator_agent.py       # Agent 2: Quality validation
│   └── pdf_generator_agent.py  # Agent 3: PDF generation coordinator
│
├── tools/
│   ├── __init__.py
│   ├── web_search_tool.py       # Tavily / DuckDuckGo search
│   └── scraping_tool.py        # BeautifulSoup page scraper
│
├── utils/
│   ├── __init__.py
│   └── pdf_generator.py        # ReportLab PDF builder
│
├── generated_reports/           # Output PDFs saved here
│
├── main.py                      # Pipeline entry point
├── requirements.txt
├── .env.example                 # Copy to .env and fill in keys
├── agent_run.log                # Created at runtime
└── README.md
```

---

## ⚙️ VS Code Setup (Step-by-Step)

### 1. Clone / create the project folder

```bash
# If you received a zip, extract it. Otherwise create the folder:
mkdir research_pdf_agent
cd research_pdf_agent
```

### 2. Open in VS Code

```bash
code .
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

**Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**Mac / Linux:**
```bash
source venv/bin/activate
```

> In VS Code: press `Ctrl+Shift+P` → **Python: Select Interpreter** → choose `venv`.

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure API keys

```bash
# Copy the example file
cp .env.example .env
```

Open `.env` and fill in your keys:

| Key | Required | Where to get it |
|-----|----------|----------------|
| `OPENAI_API_KEY` | ✅ Yes | https://platform.openai.com/api-keys |
| `TAVILY_API_KEY` | ❌ Optional | https://tavily.com (free tier available) |
| `SEARCH_PROVIDER` | ❌ Optional | `duckduckgo` (default, no key needed) or `tavily` |
| `LLM_MODEL` | ❌ Optional | default: `gpt-4o-mini` |

> **No API key?** Set `SEARCH_PROVIDER=duckduckgo` in `.env`. You still need
> `OPENAI_API_KEY` for the LLM synthesis step. Get a free key at OpenAI.

### 7. Run the project

```bash
python main.py
```

You'll see:
```
Enter research topic: Machine Learning in Agriculture
```

Type your topic and press Enter. The system will print progress for each agent
and save the PDF to `generated_reports/`.

### 8. Optional — pass topic as argument

```bash
python main.py "Quantum Computing in Finance"
```

---

## 📤 Example Output

```
generated_reports/Machine_Learning_in_Agriculture_Report.pdf
```

The PDF includes:
- **Cover page** with topic, date, and branding
- **Table of Contents**
- **Introduction** — overview
- **Background** — history and context
- **Key Concepts** — definitions and principles
- **Important Insights** — findings and trends
- **Applications** — real-world use cases
- **Conclusion** — summary and outlook
- **References** — source list

---

## 🔧 Configuration Options (`.env`)

```env
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...       # optional
SEARCH_PROVIDER=duckduckgo    # or "tavily"
LLM_MODEL=gpt-4o-mini         # or gpt-4o, gpt-3.5-turbo
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Re-run `pip install -r requirements.txt` with venv active |
| `OPENAI_API_KEY not set` | Ensure `.env` exists and key is correct |
| `No search results` | Check internet connection; try `SEARCH_PROVIDER=duckduckgo` |
| PDF not generated | Check `agent_run.log` for error details |
| Slow execution | Normal — LLM synthesis takes 15–60s per agent |

---

## 📝 Logging

All agent activity is logged to:
- **Console** — real-time progress
- **`agent_run.log`** — full debug log (created each run)

---

## 🔄 Agent Pipeline Detail

```
main.py
  │
  ├─► ResearchAgent
  │     ├─ search_web()          # 4 queries × 5 results = ~20 URLs
  │     ├─ scrape_multiple()     # Deep scrape top 6 pages
  │     └─ _llm_synthesise()    # GPT formats into JSON sections
  │
  ├─► ValidatorAgent
  │     ├─ _check_structure()   # Flags missing/short sections
  │     ├─ _local_clean()       # De-duplicate sentences + refs
  │     └─ _llm_improve()       # GPT editor pass
  │
  └─► PDFGeneratorAgent
        └─ generate_pdf()       # ReportLab: cover + TOC + body + refs
```
