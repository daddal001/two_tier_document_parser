# Security Policy

## Supported Versions

We actively support the following versions with security updates:

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 0.1.x   | :white_check_mark: | Active Development |

## Security Commitment

The Two-Tier Document Parser project takes security seriously. We are committed to:

- Responding to security reports within **3 business days**
- Providing security patches for supported versions
- Maintaining transparency about security issues once resolved
- Following responsible disclosure practices

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

### Preferred Method: Private Security Advisory

1. Go to the [Security tab](https://github.com/YOUR_ORG/two_tier_document_parser/security) of this repository
2. Click "Report a vulnerability"
3. Fill out the vulnerability details form
4. Submit the report

### Alternative Method: Email

If you prefer, you can report security vulnerabilities via email:

- **Email:** security@yourdomain.com (replace with your actual security contact)
- **PGP Key:** Available at [KEYBASE/YOUR_KEY] (optional, if you provide one)

### What to Include

Please include the following information in your report:

- **Description:** A clear description of the vulnerability
- **Impact:** Potential impact and severity assessment
- **Reproduction:** Detailed steps to reproduce the issue
- **Environment:** Version, OS, Docker image details, etc.
- **Proof of Concept:** Code or commands demonstrating the vulnerability (if applicable)
- **Suggested Fix:** Any recommendations for remediation (optional)

## Response Process

### Timeline

- **Initial Response:** Within 3 business days
- **Triage & Assessment:** Within 7 days
- **Fix Development:** Varies by severity (Critical: <7 days, High: <14 days, Medium: <30 days)
- **Public Disclosure:** After fix is released and users have time to update (typically 7-14 days)

### Severity Assessment

We use the CVSS v3.1 scoring system:

| Severity | CVSS Score | Response Time | Example |
|----------|-----------|---------------|---------|
| Critical | 9.0-10.0 | <48 hours | RCE, Authentication bypass |
| High | 7.0-8.9 | <7 days | Privilege escalation, Data exposure |
| Medium | 4.0-6.9 | <30 days | XSS, Information disclosure |
| Low | 0.1-3.9 | Next release | Minor information leaks |

## Security Measures

### Container Security

- **Non-root User:** All containers run as unprivileged users (UID 1000)
- **Read-only Filesystem:** Where possible, containers use read-only root filesystems
- **Security Scanning:** Automated Trivy and Grype scanning in CI/CD
- **Base Image Updates:** Regular updates to base images for security patches
- **Multi-stage Builds:** Minimal attack surface in production images

### Dependency Management

- **Automated Updates:** Dependabot monitors dependencies for vulnerabilities
- **Version Pinning:** Lockfiles ensure reproducible builds
- **Security Audits:** Regular `pip-audit` and `safety` scans
- **Submodule Review:** MinerU submodule security is monitored

### API Security

- **Input Validation:** All API inputs are validated using Pydantic models
- **File Upload Limits:** Maximum file size enforced (100MB default)
- **Type Validation:** Only PDF files accepted
- **Timeout Protection:** Request timeouts prevent DoS
- **Error Handling:** Secure error messages that don't leak sensitive information

### Secrets Management

- **No Hardcoded Secrets:** All secrets passed via environment variables
- **Secret Scanning:** TruffleHog scans prevent accidental commits
- **HuggingFace Tokens:** Read-only tokens recommended
- **Docker Secrets:** Support for Docker/Kubernetes secrets

### GPU Security

- **Device Access:** Containers only request necessary GPU access
- **VRAM Limits:** Configurable VRAM usage prevents resource exhaustion
- **Fallback Mode:** Automatic CPU fallback if GPU unavailable

## Known Security Considerations

### PDF Processing

- **Malicious PDFs:** PDF parsing libraries may be vulnerable to crafted inputs
- **Memory Usage:** Large PDFs can consume significant memory
- **Mitigation:** File size limits, timeouts, resource constraints

### Model Files

- **Model Provenance:** Use models from trusted sources (HuggingFace official repos)
- **Checksum Verification:** Verify model file integrity (see `models/MODELS_USED.yaml`)
- **Model Risks:** ML models may produce unexpected outputs on adversarial inputs

### Docker Deployment

- **Privileged Access:** GPU access requires some elevated permissions
- **Network Exposure:** Services expose HTTP ports - use reverse proxy in production
- **Volume Mounts:** Model cache volumes should have restricted permissions

## Security Best Practices for Users

### Production Deployment

1. **Use HTTPS:** Always deploy behind a reverse proxy with TLS
2. **Authentication:** Add authentication layer (not included in base project)
3. **Rate Limiting:** Implement rate limiting to prevent abuse
4. **Network Isolation:** Use Docker networks or Kubernetes network policies
5. **Resource Limits:** Set CPU/memory limits in production
6. **Monitoring:** Enable logging and monitoring for anomaly detection

### Docker Security

```yaml
# Recommended docker-compose.yml additions
services:
  fast-parser:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed
```

### Environment Configuration

```bash
# .env (never commit this file!)
HF_TOKEN=your_read_only_token  # Use read-only tokens
LOG_LEVEL=INFO                  # Enable logging
MINERU_VIRTUAL_VRAM_SIZE=15     # Limit VRAM usage
```

## Security Updates

Security updates will be:

1. **Announced:** GitHub Security Advisories and release notes
2. **Documented:** CHANGELOG.md with clear severity indicators
3. **Tagged:** Git tags for security releases (e.g., `v0.1.1-security`)
4. **Published:** Updated Docker images and PyPI packages

### Subscribing to Updates

- **Watch this repository:** Enable "Security alerts" notifications
- **GitHub Advisories:** https://github.com/YOUR_ORG/two_tier_document_parser/security/advisories
- **Release Feed:** Subscribe to releases via RSS or GitHub notifications

## Vulnerability Disclosure Policy

We follow **Coordinated Vulnerability Disclosure**:

1. **Private Reporting:** Researchers report vulnerabilities privately
2. **Acknowledgment:** We acknowledge receipt within 3 days
3. **Investigation:** We investigate and develop fixes
4. **Coordination:** We coordinate disclosure timeline with reporter
5. **Public Disclosure:** After fix is released and users can update
6. **Credit:** We credit reporters (unless they prefer anonymity)

### Hall of Fame

We maintain a security researchers hall of fame in our release notes to acknowledge contributors who help improve our security.

## Compliance & Standards

This project follows:

- **OWASP Top 10:** Web application security risks
- **CIS Docker Benchmark:** Container security best practices
- **OpenSSF Best Practices:** Open source security guidelines
- **NIST Cybersecurity Framework:** Security standards alignment

## Contact

- **Security Email:** security@yourdomain.com (replace with your contact)
- **Project Maintainers:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **GitHub Security:** https://github.com/YOUR_ORG/two_tier_document_parser/security

## Acknowledgments

We thank the security research community for helping keep this project secure. Special thanks to:

- The Python security team
- Docker security community
- HuggingFace security team
- GitHub security research community

---

**Last Updated:** 2024-11-23

This security policy is regularly reviewed and updated to reflect current best practices.
