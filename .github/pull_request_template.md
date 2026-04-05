## Description
<!-- Describe the changes you have made and why. -->

## Related Issues
<!-- Link to any related issues, e.g., Fixes #123 -->

## Affected Components
<!-- Check all that apply -->
- [ ] Orchestrator
- [ ] Training Worker
- [ ] Inference Service
- [ ] Monitoring Service
- [ ] Shared / Utils
- [ ] Infrastructure (Docker, CI/CD)

## Testing Performed
<!-- Describe how you tested your changes. -->
- [ ] Local testing via `docker-compose up`
- [ ] Unit tests added / updated
- [ ] Manual API testing (e.g., Postman / cURL)

## Checklist
- [ ] Code passes `pre-commit` hooks (Black, Flake8)
- [ ] Documentation updated (if applicable)
- [ ] No sensitive data (secrets, API keys) included in commits

# Enforce Conventional Commits standard for commit messages
- repo: https://github.com/commitizen-tools/commitizen
rev: v3.12.0
hooks:
  - id: commitizen
    stages: [commit-msg]

# Secrets Protection
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.4.0
  hooks:
    - id: detect-secrets
      args: ['--baseline', '.secrets.baseline']
