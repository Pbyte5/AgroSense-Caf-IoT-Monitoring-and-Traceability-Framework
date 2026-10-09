# Git Workflow & Code Standards

This guide establishes the branching model, code standards, quality checks, and release flow for the **AgroSense Café** project.

---

### 1. Start a Task (New Branch)

Before starting your work, update your local `main` branch and create a feature branch using the Jira ticket key and a short description in `kebab-case`:

```powershell
# Update local main
git switch main; git pull

# Create and switch to the task branch
git switch -c feat/AGRO-123-add-sensor-endpoint
```

---

### 2. Checks, Commit & Push

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

### 3. Standards & Best Practices

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

### 4. Release Flow

- **Continuous Deployment (Staging/Dev):** Every merge into the `main` branch is automatically deployed to the Staging/Development environment via CI/CD pipelines.
- **Production Release:** Production deployments are triggered by creating a Git Release Tag directly from `main`.
- **Version format:** `v1.0.0`
