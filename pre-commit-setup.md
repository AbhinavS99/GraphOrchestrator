# pre-commit-setup.md

## ⚡ Pre-commit + Black Setup Guide

This project uses **pre-commit** to automatically format code with **black** on every commit.

Follow these steps to set up your local environment:

---

### 1. Install Required Packages

```
pip install --user pre-commit black
```

> Make sure your installed Python version matches the project (Python 3.12+ recommended).

---

### 2. Install the Pre-commit Hook

```
python -m pre_commit install
```

This will set up a Git hook that runs **black** automatically before every commit.

---

### 3. (Optional) Manually Format Code

If you want to format the entire codebase manually:

```
python -m black .
```

> Useful for first-time setup or bulk formatting.

---

### 4. Commit as Usual

When you `git commit`, pre-commit will automatically:
- Check your staged `.py` files.
- Format them using `black`.
- If formatting changes are needed, it will modify the files and ask you to stage them again.

---

### 📜 Example Workflow:

```
# Make code changes
git add .
git commit -m "feat: add new feature"
# pre-commit will auto-run black before completing the commit
```

If black reformats your files during commit, you may see:

```
black................................................(files modified)Failed
```
✅ This is normal — it simply means black cleaned your code.  
✅ Just `git add` again and commit.

---

### 💡 Tips
- Always run `git add .` **after** black formats your code.
- Use semantic Git commit messages like:
  - `style: format codebase with black`
  - `feat: add new graph builder method`

---

# ✅ That's it! Happy coding!
