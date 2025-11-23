# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI/CD pipeline with automated testing, linting, and security scanning
- Multi-architecture Docker builds (linux/amd64, linux/arm64)
- PyPI trusted publishing with OIDC (no tokens required)
- Comprehensive security scanning (Trivy, Grype, CodeQL, Bandit, Safety)
- Pre-commit hooks for code quality (Ruff, Black, isort, Mypy)
- Dependabot configuration for automated dependency updates
- Security hardened Docker images with non-root users
- Production-optimized Dockerfiles with multi-stage builds
- SECURITY.md with vulnerability reporting process
- CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- Pinned requirements files for reproducible builds
- .env.example template for environment configuration
- GitHub issue and PR templates
- Model provenance tracking (MODELS_USED.yaml)

### Changed
- Updated docker-compose.yml with security options (no-new-privileges, capability dropping)
- Changed volume paths to use non-root user home directory
- Enhanced documentation with deployment best practices

### Security
- Container images now run as non-root user (UID 1000)
- Added security_opt: no-new-privileges to all services
- Implemented capability dropping for minimal privilege
- Added automated vulnerability scanning in CI/CD
- Secret detection with TruffleHog
- SBOM generation for container images
- Container image signing with Cosign

## [0.1.0] - 2024-11-23

### Added
- Initial release of Two-Tier Document Parser
- Fast parser service using PyMuPDF4LLM (CPU-based, high throughput)
- Accurate parser service using MinerU with VLM support (GPU-accelerated)
- Automatic GPU detection with CPU fallback
- FastAPI-based REST API for both parsers
- Comprehensive API documentation with OpenAPI/Swagger
- Docker and Docker Compose deployment support
- Health check endpoints for monitoring
- Extensive documentation (README, SETUP_GUIDE, TESTING, etc.)
- Unit and integration test suites
- Example client and Jupyter notebooks

### Features

#### Fast Parser
- PyMuPDF4LLM-based text extraction
- No-GIL Python 3.12 for true thread parallelism
- Processes 10-50 pages/second
- Ideal for high-volume, simple documents

#### Accurate Parser
- MinerU-based advanced parsing
- Vision Language Model (VLM) support for images, tables, formulas
- Automatic GPU/CPU mode switching
- 95%+ accuracy on complex layouts
- Model caching with HuggingFace integration

### Documentation
- Comprehensive README with quick start guide
- Architecture diagrams
- Performance benchmarks
- Troubleshooting guide
- Contributing guidelines

---

## Release Process

This project uses semantic versioning:

- **MAJOR** version: Incompatible API changes
- **MINOR** version: Backwards-compatible functionality additions
- **PATCH** version: Backwards-compatible bug fixes

### Version Numbering

```
v{MAJOR}.{MINOR}.{PATCH}[-{PRE-RELEASE}][+{BUILD}]

Examples:
- v1.0.0          # Stable release
- v1.1.0-alpha.1  # Alpha pre-release
- v1.1.0-beta.2   # Beta pre-release
- v1.1.0-rc.1     # Release candidate
```

### Commit Message Format

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, missing semi colons, etc)
- `refactor`: Code refactoring (neither fixes a bug nor adds a feature)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Changes to build system or dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files
- `revert`: Reverts a previous commit

Examples:
```bash
feat(fast-parser): add support for PDF/A format
fix(accurate-parser): resolve memory leak in VLM mode
docs: update deployment guide with Kubernetes examples
ci: add automated Docker image scanning
```

### Creating a Release

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with new version section
3. Commit changes: `git commit -m "chore: bump version to X.Y.Z"`
4. Create and push tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
5. GitHub Actions will automatically:
   - Create GitHub release
   - Publish to PyPI
   - Build and publish Docker images
   - Generate release notes

---

## Links

- [GitHub Repository](https://github.com/daddal001/two_tier_document_parser)
- [Issue Tracker](https://github.com/daddal001/two_tier_document_parser/issues)
- [PyPI Package](https://pypi.org/project/two-tier-parser/)
- [Docker Images](https://github.com/daddal001/two_tier_document_parser/pkgs/container/two_tier_document_parser-fast)
- [Security Policy](./SECURITY.md)
- [Contributing Guide](./CONTRIBUTING.md)
- [Code of Conduct](./CODE_OF_CONDUCT.md)
