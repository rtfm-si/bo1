get new bank account for sico software
get companies house id sorted
get vat number
change business code on companies house

update to sico software ltd as 'company'

remove social links in bottom right of page

add other social login

add monitoring and analytics etc links to admin page (grafana, prometheus, umami, kuma...). can we extend our status page to show our api status publicly?

---

## Email to DigitalOcean (DDoS Incident Response)

**Subject:** Re: DDoS Activity Report - Droplet quark (167.99.196.50) - Issue Resolved

Hi,

Thank you for alerting us to the DDoS activity originating from our droplet. We have investigated and resolved the issue.

**Root Cause:**
A third-party container (Umami Analytics v2.15.0) running on our droplet was compromised via a remote code execution vulnerability. The attacker exploited this to deploy a DDoS botnet binary that participated in the attack against 87.196.81.42.

**Actions Taken:**
1. Identified and terminated all malicious processes (`uhavenobotsxd` botnet)
2. Stopped and removed the compromised container
3. Blocked attacker command & control IPs (94.154.35.154, 193.142.147.209) at the firewall level
4. Verified no host-level persistence or compromise of other containers
5. Persisted firewall rules across reboots
6. Removed the vulnerable Umami software from our stack

**Verification:**
- No remaining malicious processes or network connections
- SSH access logs show only authorized access from our IP
- All other containers scanned and confirmed clean

The droplet is now secure and we have implemented additional monitoring. Please let us know if you require any further information.

Best regards,
[Your Name]

---

## Security Hardening After Umami Incident

### Immediate Actions (Do Now)

1. **Rotate Postgres password** - Attacker had access to `bo1` credentials which can access ALL databases
   ```bash
   # Generate new password
   openssl rand -hex 32
   # Update in .env and restart all services using postgres
   ```

2. **Check for data exfiltration** - Review if any unusual queries hit `boardofone` DB during compromise window (Dec 17 ~13:19-13:57 UTC)

### Prevention Measures

| Measure | Implementation | Priority |
|---------|---------------|----------|
| **Separate DB users per service** | Create `umami_user` with access ONLY to `umami` DB | High |
| **Network isolation** | Put Umami on separate Docker network, only allow postgres access | High |
| **Pin image versions** | Use `umami:postgresql-3.0.3` not `latest` | Medium |
| **Read-only filesystem** | Add `read_only: true` to container, explicit tmpfs for /tmp | Medium |
| **Drop capabilities** | `cap_drop: [ALL]` in docker-compose | Medium |
| **No new privileges** | `security_opt: [no-new-privileges:true]` | Medium |

### Detection Measures

| Measure | Implementation | Priority |
|---------|---------------|----------|
| **Process monitoring** | Cron job checking for suspicious processes | High |
| **Outbound connection alerts** | Monitor for connections to non-whitelisted IPs | High |
| **Container image scanning** | Trivy/Grype scan on deploy | Medium |
| **Log anomaly detection** | Alert on wget/curl/nc in container logs | Medium |
| **File integrity** | Alert on new files in /tmp, /var/tmp | Medium |

### Quick Detection Script

Save to `/opt/boardofone/scripts/security-check.sh`:
```bash
#!/bin/bash
# Run via cron every 5 minutes

ALERT_FILE="/tmp/security-alert"

# Check for suspicious processes
SUSPICIOUS=$(docker ps -q | xargs -I {} docker exec {} ps aux 2>/dev/null | grep -E 'wget|curl|nc |ncat|/tmp/|miner|xmr|crypto' | grep -v grep)

# Check for outbound connections to unusual ports
OUTBOUND=$(ss -tupn | grep -E 'ESTAB.*:[0-9]{4,5}' | grep -vE ':(443|80|5432|6379|3000|8080|9090) ')

if [[ -n "$SUSPICIOUS" ]] || [[ -n "$OUTBOUND" ]]; then
    if [[ ! -f "$ALERT_FILE" ]]; then
        echo "SECURITY ALERT: $(date)" | tee "$ALERT_FILE"
        echo "$SUSPICIOUS" >> "$ALERT_FILE"
        echo "$OUTBOUND" >> "$ALERT_FILE"
        # Send to ntfy or other alerting
        curl -d "Security alert on quark - check $ALERT_FILE" ntfy.boardof.one/alerts 2>/dev/null
    fi
fi
```

### Hardened Umami Config Example

```yaml
umami:
  image: ghcr.io/umami-software/umami:postgresql-3.0.3  # Pinned version
  read_only: true
  tmpfs:
    - /tmp:size=100M,mode=1777
  security_opt:
    - no-new-privileges:true
  cap_drop:
    - ALL
  environment:
    - DATABASE_URL=postgresql://umami_user:${UMAMI_DB_PASSWORD}@postgres:5432/umami  # Dedicated user
  networks:
    - umami-internal  # Isolated network
  # ... rest of config
```
