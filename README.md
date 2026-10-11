# 📄 Free ATS LaTeX Resume Optimizer Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![CI Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)](tests/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Zero Cost](https://img.shields.io/badge/Cost-%240%20(Free%20Tier)-success.svg)](#)

> A zero-cost, open-source application that parses LaTeX resumes and target Job Descriptions (JD), extracts keyword gaps, performs keyless DuckDuckGo industry trend discovery, aligns target job titles, injects believable bluffs, rewrites experience bullets using Google's XYZ formula, enforces a strict 1-page fit, maximizes Jobscan ATS match percentages, and outputs ready-to-compile, 100% syntactically valid LaTeX (`.tex`) and rendered PDF (`.pdf`) files.

---

## 🌟 Key Features

1. **100% LaTeX Syntax & Template Preservation**:
   - Preserves all `\documentclass`, custom macros (`\newcommand`), packages, document layout, and spacing untouched.
   - Deterministic LaTeX character escaping (`\%`, `\&`, `\_`, `\$`, `\#`).
   - Integrated syntax validator for brace balance `{}` and environment integrity (`\begin{...}` vs `\end{...}`).
   - **Primary & Fallback Guarantee**: Downloadable clean `.tex` source code is always front and center, ensuring you are never locked into any proprietary format.
2. **🎯 Job Title Match & Alignment (Jobscan Optimization)**:
   - Aligns the resume headline and primary role title with the target job title from the JD.
   - Directly solves the title mismatch penalty in ATS systems like Jobscan!
3. **📏 Strict 1-Page Resume Layout Constraint**:
   - Constrains bullet lengths (16 to 22 words max, approx 1.5 printed lines) to prevent rambling sentences.
   - Fine-tunes margins and spacing so your resume stays strictly on 1 page without 2nd page overflow.
4. **AI-Driven Content Optimization**:
   - **Believable Bluffs**: Injects high-demand adjacent industry tools that naturally fit the candidate's existing background (e.g., Docker ➔ Kubernetes & Helm; React ➔ TypeScript & Next.js; Python ➔ FastAPI & Celery).
   - **Jobscan In-Context Placement**: Integrates target skills directly inside experience and project bullets (not just in the skills list), satisfying Jobscan's work-history verification.
   - **Google XYZ Bullet Rewriter**: Rephrases bullets as *"Accomplished [X] as measured by [Y], by doing [Z]"* with action verbs and quantifiable metrics.
5. **📑 PDF Upload & Zero-Cost PDF Rendering**:
   - **PDF Upload**: Upload an existing `.pdf` resume to automatically extract text via `pypdf`.
   - **PDF Rendering**: 1-click compile LaTeX to PDF directly inside the web app for free.
   - **Overleaf Integration**: Direct link to open and compile in Overleaf.
6. **DuckDuckGo Live Trend Intelligence**:
   - Zero-cost, keyless real-time web search for trending industry skills and tooling for the target role.
7. **ATS & Jobscan Gap Analysis**:
   - Composite ATS Match score + Simulated Jobscan match score.
   - Categorized breakdown: Job Title Match, Hard Skills, In-Context Placement, Cloud/DevOps, and Impact Metrics.
   - Visual Keyword Matrix showing matched keywords, newly unlocked keywords, skills-only warnings, and remaining gaps.
8. **Zero-Cost Multi-Provider AI Engine**:
   - **Google Gemini** (Free Tier via [Google AI Studio](https://aistudio.google.com/app/apikey) — 1,500 req/day, `gemini-2.0-flash`)
   - **Groq** (Free Tier via [Groq Console](https://console.groq.com/keys) — `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`)
   - **Cerebras Cloud** (Free Tier via [Cerebras Cloud](https://cloud.cerebras.ai) — `llama-3.3-70b`)
   - **OpenRouter** (Free models via [OpenRouter](https://openrouter.ai/keys))
   - **Demo Mode** (100% Offline — runs with smart heuristic engine without any API key)

---

## 📁 Project Architecture

```
ats-resume-optimizer/
├── app.py                      # Streamlit interactive web application
├── core/
│   ├── __init__.py
│   ├── latex_engine.py         # LaTeX AST parser, escaper, syntax validator & reconstructor
│   ├── pdf_engine.py           # PDF text extraction (pypdf) & zero-cost compilation
│   ├── jd_analyzer.py          # Job description keyword & multi-word phrase extractor
│   ├── trend_search.py         # Keyless DuckDuckGo search for live role skill trends
│   ├── ats_scorer.py           # ATS & Jobscan scoring engine (Before vs After match % & delta)
│   ├── llm_optimizer.py        # Multi-provider free LLM client & heuristic demo engine
│   └── optimizer_pipeline.py   # End-to-end orchestrator pipeline
├── sample_data/
│   ├── sample_resume.tex       # Standard ATS-friendly LaTeX resume (Jake's Resume template)
│   └── sample_jd.txt           # Realistic Senior Full Stack / Cloud JD for 1-click testing
├── tests/
│   └── test_latex_engine.py    # Unit tests ensuring LaTeX syntax preservation & scoring
├── .github/
│   └── workflows/ci.yml        # GitHub Actions CI workflow (automated testing)
├── .streamlit/
│   └── config.toml             # Streamlit visual theme and server settings
├── requirements.txt            # Production dependencies
├── render.yaml                 # 1-click Render.com deployment manifest
├── Dockerfile                  # Container definition for containerized hosting
├── LICENSE                     # MIT License
├── CONTRIBUTING.md             # Open source contribution guidelines
└── README.md                   # Project documentation
```

---

## 🚀 Quick Start (Local Run)

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/<your-username>/ats-resume-optimizer.git
cd ats-resume-optimizer
pip install -r requirements.txt
```

### 2. Launch Streamlit Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

### 3. One-Click Instant Test
In the web interface:
1. Click **"📋 Load Sample Resume & JD"** in the sidebar.
2. Select your AI provider (**Google Gemini**, **Groq**, or **Demo Mode**).
3. Paste your free API key (or use Demo Mode without any key).
4. Keep **"🎯 Align Job Title"** and **"📏 Enforce 1-Page Tight Fit"** enabled.
5. Click **"🚀 Optimize Resume for ATS & Jobscan"**.
6. View before/after scores, inspect bullet diffs, and download your optimized `optimized_resume.tex` or `optimized_resume.pdf`!

---

## 🌐 Free Cloud Deployment Options

### Option A: Streamlit Community Cloud (Recommended — 100% Free)
1. Push this repository to your GitHub account.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **"New App"**, select this repository and set Main file path to `app.py`.
4. (Optional) In **Advanced Settings > Secrets**, you can set:
   ```toml
   GEMINI_API_KEY = "your-gemini-key"
   GROQ_API_KEY = "your-groq-key"
   ```
5. Click **Deploy**. Your app is live with a public URL!

### Option B: Render.com (Free Web Service)
1. Create a free account at [render.com](https://render.com).
2. Connect your GitHub repository.
3. Select **New Web Service** and Render will automatically detect `render.yaml`.
4. Choose the **Free Plan** and click **Create Web Service**.

---

## 🧪 Running Unit Tests

Run the test suite to verify LaTeX parsing, escaping, syntax validation, Jobscan scoring, and PDF engine:
```bash
python -m unittest discover tests
```

---

## 🤝 Contributing
Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on setting up your development environment and submitting pull requests.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
