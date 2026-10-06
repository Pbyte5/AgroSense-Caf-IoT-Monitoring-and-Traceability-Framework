# 🛠️ AgroSense Café — Developer & Workflow Guide

This guide establishes the instructions for onboarding, local environment setup, branching model, code standards, quality checks, and release flow for the **AgroSense Café** project.

---

## PART 1: ONBOARDING & REPOSITORY SETUP

### 1. Prerequisites

Ensure you have the following tools installed on your system before starting:

- **Git** (v2.30+)
- **Python** (v3.12+)
- **uv** (Extremely fast Python package and virtual environment manager):
  ```powershell
  # Install uv on Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm [https://astral.sh/uv/install.ps1](https://astral.sh/uv/install.ps1) | iex"
  ```

---

### 2. Clone Repository

Clone the project and navigate to the root directory:

```powershell
git clone [https://github.com/your-organization/agrosense-cafe.git](https://github.com/your-organization/agrosense-cafe.git)
cd agrosense-cafe
```

---

### 3. Install Dependencies

We use **`uv`** to isolate the virtual environment and synchronize project dependencies quickly and deterministically:

```powershell
# Create the virtual environment (.venv) and install development dependencies
uv sync
```

> 💡 **Note:** `uv sync` will automatically create the virtual environment and install all libraries specified in `pyproject.toml` and `uv.lock`.

---

### 4. Run Checks & Tests

Before committing or opening a Pull Request, it is **mandatory** to run the linter, formatter, and local test suite:

```powershell
# 1. Check and fix style/linting errors with Ruff
uv run ruff check . --fix

# 2. Format the code according to project standards
uv run ruff format .

# 3. Run the local test suite with Pytest
uv run pytest
```

---

# GIT WORKFLOW & CODE STANDARDS

### 5. Start a Task (New Branch)

Before starting your work, update your local `main` branch and create a feature branch using the Jira ticket key and a short description in `kebab-case`:

```powershell
# Update local main
git switch main; git pull

# Create and switch to the task branch
git switch -c feat/AGRO-123-add-sensor-endpoint
```

---

### 6. Checks, Commit & Push

Run the linter, formatter, and unit tests before staging your changes, creating the commit, and pushing them to the remote repository:

```powershell
# Format and fix linting issues with Ruff
uv run ruff check . --fix; uv run ruff format .

# Run test suite
uv run pytest

# Stage changes interactively
git add -p

# Commit following Conventional Commits
git commit -m "feat(api): add sensor readings endpoint"

# Push the branch and set remote upstream
git push -u origin HEAD
```

---

### 7. Standards & Best Practices

#### Branch Naming
Use standard semantic prefixes followed by the Jira ticket key and a brief description in `kebab-case`:
- **Allowed prefixes:** `feat/`, `fix/`, `chore/`, `docs/`
- **Example:** `feat/AGRO-123-add-sensor-endpoint`

#### Commit Messages
Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- **Structure:** `<type>(<optional scope>): <description>`
- **Common types:** `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`
- **Example:** `feat(api): add sensor readings endpoint`

#### PR Scope
- **Size:** Keep Pull Requests small (ideally under 400 lines of diff).
- **Testing:** Ensure all changes include their corresponding unit or integration tests.

#### Merging Strategy
- **Squash and Merge:** Always use the **Squash and merge** option on GitHub to maintain a clean, linear history on the `main` branch.

---

### 8. Release Flow

- **Continuous Deployment (Staging/Dev):** Every merge into the `main` branch is automatically deployed to the Staging/Development environment via CI/CD pipelines.
- **Production Release:** Production deployments are triggered by creating a Git Release Tag directly from `main`.
- **Version format:** `v1.0.0`