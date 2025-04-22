# Contributing to GraphOrchestrator

🎉 Thanks for your interest in contributing to **GraphOrchestrator**! Whether it's fixing bugs, improving docs, or adding new features — we welcome all contributions.

---

## 🛠️ Getting Started

1. **Fork the Repository**  
   Click the **Fork** button at the top right of the [GitHub repo](https://github.com/yourusername/graphorchestrator).

2. **Clone Your Fork Locally**
   ```bash
   git clone https://github.com/AbhinavS99/graphorchestrator.git
   cd graphorchestrator
   ```

3. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

4. **Install Dev Dependencies**
   ```bash
   pip install -e .[dev]
   ```

---

## 💡 How to Contribute

### 🐞 Report Bugs

Open an issue with:
- A clear title
- Steps to reproduce
- Expected behavior
- Screenshots or logs (if any)

### ✨ Suggest Features

Open an issue and prefix it with `[Feature]`  
Include:
- Use case
- Why it’s useful
- Any technical ideas

### 👨‍💻 Code Contributions

1. Create a new branch:
   ```bash
   git checkout -b fix/your-branch-name
   ```

2. Make your changes, write tests if needed.

3. Run tests:
   ```bash
   pytest
   ```

4. Commit using meaningful messages:
   ```bash
   git commit -m "Fix: handle null input in orchestrator"
   ```

5. Push and open a Pull Request:
   ```bash
   git push origin fix/your-branch-name
   ```

---

## ✅ Coding Guidelines

- Follow [PEP8](https://pep8.org/) style.
- Keep functions small and readable.
- Include docstrings and type hints.

---

## 📦 Releasing

Only maintainers can push new versions to PyPI via GitHub Actions.  
To trigger a release:
```bash
git tag v0.X.Y
git push origin v0.X.Y
```

---

## 🙌 Thanks for Contributing!

You're helping make GraphOrchestrator better for everyone. 🌟
