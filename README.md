# InfraKit

InfraKit is a powerful CLI tool designed to automate service onboarding and GitOps deployments across multiple Kubernetes clusters using ArgoCD, Helm, PostgreSQL, and Redis.

## Table of Contents
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Examples](#examples)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Multi-cluster management**: Deploy across multiple Kubernetes environments
- **GitOps automation**: ArgoCD integration for declarative deployments
- **Helm support**: Template management and version control
- **State management**: PostgreSQL for config, Redis for caching
- **Validation**: Comprehensive pre-deployment checks
- **Security**: RBAC and secret management

## Architecture

```mermaid
graph TD
    CLI[Python CLI] -->|JSON API| GoService[Go Service]
    CLI --> ArgoCD
    CLI --> PostgreSQL
    CLI --> Redis
    GoService --> Helm
    GoService --> Kubernetes
```

## Prerequisites

- Python 3.7+
- Go 1.16+
- Helm 3+
- ArgoCD CLI
- PostgreSQL 12+
- Redis 6+
- Kubernetes clusters with ArgoCD

## Installation

### From Source

```bash
git clone https://github.com/yourorg/infrakit.git
cd infrakit

# Python dependencies
pip install -r requirements.txt

# Build Go service
cd go-service
go build -o /usr/local/bin/infrakit-go-service

# Install CLI
sudo ln -s $PWD/cli.py /usr/local/bin/infrakit
```

### Docker

```bash
docker build -t infrakit .
docker run -it --rm -v ~/.kube:/root/.kube infrakit
```

## Configuration

Create `~/.infrakit/config.yaml`:

```yaml
argocd:
  apiUrl: https://argocd.example.com
  username: admin
  password: admin123

postgresql:
  url: postgres://user:pass@postgres:5432/infrakit

redis:
  url: redis://redis:6379/0
```

## Usage

### Onboard Application

```bash
infrakit onboard \
  --name myapp \
  --cluster prod \
  --namespace default \
  --chart stable/nginx \
  --repo git@github.com:myorg/gitops.git \
  --path apps/myapp
```

### Common Commands

| Command             | Description                  |
|---------------------|-----------------------------|
| `infrakit onboard`  | Onboard new application     |
| `infrakit sync`     | Sync ArgoCD application     |
| `infrakit status`   | Check deployment status     |
| `infrakit list`     | List managed applications   |

## Examples

#### Simple Onboarding

```bash
infrakit onboard \
  --name frontend \
  --cluster staging \
  --namespace web \
  --chart bitnami/nginx \
  --values-file values.yaml \
  --repo git@github.com:myorg/gitops.git \
  --path apps/frontend
```

## Development

### Project Structure

```
infrakit/
├── cli.py            # Python CLI
├── go-service/       # Go binaries
├── config/           # Configuration
├── tests/            # Test suites
└── docs/             # Documentation
```

### Testing

```bash
# Unit tests
pytest tests/unit/

# Integration tests
make test-integration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a PR with tests

## License

Apache 2.0 © YourOrg