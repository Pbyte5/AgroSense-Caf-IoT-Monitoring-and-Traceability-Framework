# 🚀 Onboarding & Offboarding Procedures — AgroSense Café

This document establishes the standard protocol for onboarding new contributors to the team and the secure access revocation procedure (offboarding).

---

## 1. Onboarding Process

To join the **AgroSense Café** development team, follow these steps:

### Step 1: Access Request

The Tech Lead or Scrum Master will provision the following credentials and permissions:

- **GitHub:** Repository invitation with Collaborator role (`Write`).
- **Jira & Confluence:** Access to the AgroSense project board for user story management.
- **AWS IAM / SSO:** Profile creation with least-privilege policies for the development environment (`AgroSense-Dev-Role`).
- **Communication Channels:** Addition to the official team channel on Slack / Teams.

### Step 2: Local Environment Setup

1. Review the complete development guide in `DEVELOPER_GUIDE.md`.
2. Clone the repository and install dependencies by running `uv sync`.
3. Configure your local `.env` environment variables file from the `.env.example` template.

### Step 3: First Task (Good First Issue)

1. Pick up your first assigned task in Jira.
2. Create your branch following the naming convention (`feat/AGRO-XXX-description`).
3. Run linters and tests using `uv run ruff check . --fix` and `uv run pytest`.
4. Submit your first Pull Request for Peer Review.

---

## 2. Offboarding Process (Access Revocation)

When a team member concludes their participation in the project, the Tech Lead / Administrator must execute this security checklist within a maximum of **24 hours**:

### Offboarding Checklist

- [ ] **GitHub:** Revoke repository access and remove the user from the organization.
- [ ] **AWS IAM:** Deactivate Access Keys, IAM users, and SSO roles.
- [ ] **Jira / Confluence:** Deactivate the account in the Atlassian workspace.
- [ ] **Secret Rotation:** If the contributor handled production/staging keys or tokens, perform immediate rotation in AWS Secrets Manager.
- [ ] **Code Handover:** Reassign open Pull Requests and active branches to another developer.
- [ ] **Communication Channels:** Remove the user from Slack / Teams channels and mailing lists.
