# Deployment Scripts Security Notice

⚠️ **SECURITY WARNING**: These deployment scripts contain infrastructure configuration and should be handled with care.

## Current Setup (MVP)

For MVP convenience, deployment scripts are co-located with application code in this repository. While this is acceptable for small teams and rapid development, it has security implications:

### Risks

1. **Exposure**: Anyone with repository access can view infrastructure configuration
2. **Access Control**: Cannot separate application developers from infrastructure operators
3. **Audit Trail**: Infrastructure changes mixed with application changes
4. **Secret Management**: Temptation to hardcode secrets in scripts (NEVER DO THIS)

### Mitigation (Current)

- ✅ No secrets stored in scripts (all via environment variables)
- ✅ Scripts designed to be idempotent and reviewable
- ✅ Clear documentation of security best practices
- ✅ All sensitive operations logged for audit
- ✅ GitHub Actions secrets for deployment credentials

## Best Practices for Production Scale

Before scaling beyond MVP, migrate to proper infrastructure-as-code setup:

### 1. Separate Infrastructure Repository

Create a private infrastructure repository with restricted access:

```
company-infra/
├── terraform/          # Infrastructure provisioning
├── ansible/            # Configuration management
├── kubernetes/         # Container orchestration (if applicable)
└── secrets/            # Encrypted secrets (git-crypt or similar)
```

**Access control**: Limit to DevOps/SRE team only.

### 2. Secret Management

Use external secrets manager instead of environment variables:

- **AWS Secrets Manager**: For AWS deployments
- **HashiCorp Vault**: Platform-agnostic secret management
- **Google Secret Manager**: For GCP deployments
- **Azure Key Vault**: For Azure deployments

**Never**:
- ❌ Commit secrets to git (even in .env.example)
- ❌ Store secrets in CI/CD logs
- ❌ Share secrets via Slack/email
- ❌ Use same secrets across environments

### 3. Infrastructure as Code (IaC)

Replace shell scripts with declarative IaC tools:

**Terraform** (recommended for infrastructure provisioning):
```hcl
resource "digitalocean_droplet" "boardofone" {
  image  = "ubuntu-22-04-x64"
  name   = "boardofone-prod"
  region = "nyc3"
  size   = "s-2vcpu-4gb"

  ssh_keys = [var.ssh_key_fingerprint]

  tags = ["production", "boardofone"]
}
```

**Ansible** (recommended for configuration management):
```yaml
- name: Configure Board of One server
  hosts: production
  roles:
    - docker
    - nginx
    - letsencrypt
    - boardofone
```

### 4. Deployment Pipeline

Implement proper CI/CD with security gates:

```
Code Push → Tests → Security Scan → Build → Staging → Production
                      ↓
              - SAST (Bandit)
              - Dependency Check
              - Secret Scanning
              - Container Scanning
```

**GitHub Actions** (current):
- ✅ Environment protection rules
- ✅ Required approvals for production
- ✅ Audit logging
- ⚠️ Add security scanning (see Fix 21)

### 5. Access Control

Implement principle of least privilege:

| Role | Access |
|------|--------|
| **Developers** | Application repository, staging deploy |
| **DevOps** | Infrastructure repository, production deploy |
| **Security** | Audit logs, secret rotation |
| **Compliance** | Read-only access to everything |

### 6. Audit Logging

Log all infrastructure operations:

- Who deployed what, when, and where
- What secrets were accessed
- What changes were made to infrastructure
- Failed authentication attempts

**Tools**: CloudTrail (AWS), Cloud Audit Logs (GCP), Azure Monitor (Azure)

## Migration Checklist (When Ready)

Before moving to production scale:

- [ ] Create separate infrastructure repository
- [ ] Set up Terraform for infrastructure provisioning
- [ ] Set up Ansible for configuration management
- [ ] Migrate secrets to external secrets manager
- [ ] Implement RBAC (Role-Based Access Control)
- [ ] Set up centralized audit logging
- [ ] Document incident response procedures
- [ ] Create runbooks for common operations
- [ ] Set up monitoring and alerting
- [ ] Implement automated backups
- [ ] Test disaster recovery procedures
- [ ] Security audit of infrastructure code
- [ ] Penetration testing of production environment

## Current Scripts

These scripts are safe for MVP use but follow the guidelines above for production:

### Server Setup
- `setup-production-server.sh` - Initial server configuration
- `verify-server-setup.sh` - Validate server configuration
- `setup-letsencrypt.sh` - SSL certificate setup

### Deployment
- `deploy-from-scratch.sh` - Full deployment automation
- `fix-deployment-issues.sh` - Common issue resolution

### Authentication
- `setup-github-ssh-keys.sh` - SSH key generation for GitHub Actions
- ~~`generate-supabase-keys.js`~~ - REMOVED (replaced with `openssl rand -base64 32` for SuperTokens)

## Security Review Frequency

For production systems:

- **Weekly**: Review access logs for anomalies
- **Monthly**: Rotate credentials and API keys
- **Quarterly**: Full security audit of infrastructure
- **Annually**: Penetration testing and compliance review

## Questions or Concerns?

If you're deploying Board of One at scale and need security guidance:

1. Review this document thoroughly
2. Consult with your security team
3. Consider hiring DevOps/SRE expertise
4. Schedule security audit before production launch

---

**Remember**: Security is not a one-time setup. It's an ongoing process of monitoring, updating, and improving your security posture.
