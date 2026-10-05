# AgroSense Café Framework


# Git Workflow and Standards Guide

This guide establishes the standard development workflow, branch naming conventions, code quality checks, and release process for the project.

## 1. Starting a Task (New Branch)

Before starting work, update your local `main` branch and create a feature branch using the Jira issue key and task description:

```powershell
# Update main branch
git switch main; git pull

# Create and switch to the task branch
git switch -c feat/AGRO-123-add-sensor-endpoint
```

## 2. Quality Checks, Commit, and Push

Before committing and pushing changes, run the code formatter, linter, and test suite:

```powershell
# Format and lint fix with Ruff
uv run ruff check . --fix; uv run ruff format .

# Run test suite
uv run pytest

# Stage changes interactively
git add -p

# Commit using Conventional Commits
git commit -m "feat(api): add sensor readings endpoint"

# Push branch and set upstream
git push -u origin HEAD
```

## 3. Standards and Best Practices

### Branch Naming

Use standard semantic prefixes followed by the Jira issue key and a brief description in kebab-case:

* **Allowed prefixes:** `feat/`, `fix/`, `chore/`, `docs/`
* **Example:** `feat/AGRO-123-add-sensor-endpoint`

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

* **Format:** `<type>(<optional scope>): <description>`
* **Common types:** `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`
* **Example:** `feat(api): add sensor readings endpoint`

### PR Scope

* **Size:** Keep pull requests small (ideally under 400 lines of diff).
* **Testing:** Ensure all changes include corresponding unit or integration tests.

### Merging Strategy

* **Squash and Merge:** Always use **Squash and merge** on GitHub to maintain a clean, linear commit history on `main`.

## 4. Release Flow

* **Continuous Deployment:** Every merge integrated into the `main` branch automatically deploys to the Staging/Development environment via CI/CD pipelines.
* **Production Release:** Releases to Production are triggered by creating a version tag (Release Tag) in Git directly from `main`.
* **Tag format example:** `v1.0.0`
