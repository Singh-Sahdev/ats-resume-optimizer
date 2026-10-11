# Contributing to Free ATS LaTeX Resume Optimizer

Thank you for your interest in contributing to the **Free ATS LaTeX Resume Optimizer Pipeline**! We welcome community contributions from developers, recruiters, and LaTeX enthusiasts.

---

## 🛠️ Development Setup

1. **Fork and Clone the Repository**:
   ```bash
   git clone https://github.com/<your-username>/ats-resume-optimizer.git
   cd ats-resume-optimizer
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the App Locally**:
   ```bash
   streamlit run app.py
   ```

---

## 🧪 Running Tests

Before submitting a Pull Request, ensure all automated tests pass:

```bash
python -m unittest discover tests
```

---

## 📌 Contribution Guidelines

- **LaTeX Safety**: The core architecture must guarantee 100% preservation of custom commands, packages, and preamble formatting. Never make changes that rewrite raw LaTeX from unconstrained strings.
- **Zero Cost Mandate**: All integrated tools, search engines, and AI endpoints must have a genuine 100% free tier or offline capability without demanding credit cards.
- **Code Style**: Write clean, PEP 8 compliant Python code with clear docstrings and type annotations.
- **Commit Messages**: Use concise, conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`).

---

## 📄 License
By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
