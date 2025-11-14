# Security Documentation

## Overview

The Allianz Fraud Middleware provides comprehensive security at two critical levels:

1. **Customer Protection** - Real-time fraud detection protecting end customers
2. **Institute Protection** - Organization-level security preventing data breaches and insider threats

This document describes the security architecture, controls, and compliance considerations.

---

## Table of Contents

- [Authentication & Authorization](#authentication--authorization)
- [Data Encryption](#data-encryption)
- [PII & Sensitive Data Handling](#pii--sensitive-data-handling)
- [Institute Security Features](#institute-security-features)
- [Rate Limiting & API Protection](#rate-limiting--api-protection)
- [Audit Logging](#audit-logging)
- [Compliance](#compliance)
- [Incident Response](#incident-response)
- [Security Best Practices](#security-best-practices)

---

## Authentication & Authorization

### API Authentication

**Current MVP Implementation:**
- Source identification via IP address (demonstration purposes)
- Supports header-based authentication extension

**Production Requirements:**

```http
Authorization: Bearer <API_KEY>
X-API-Client-ID: <CLIENT_ID>
```

**Recommended Authentication Methods:**

1. **API Keys** (Basic)
   - Unique per client/system
   - Scoped permissions (read-only, write, admin)
   - Rotation policy: 90 days
   - Secure storage in secrets manager

2. **OAuth 2.0** (Advanced)
   - Token-based authentication
   - Short-lived access tokens (15 min)
   - Refresh tokens (7 days)
   - Integration with enterprise IdP (Azure AD, Okta)

3. **Mutual TLS** (High Security)
   - Certificate-based authentication
   - For internal system-to-system communication
   - Certificate pinning

### Authorization Levels

| Role | Permissions | Use Case |
|------|-------------|----------|
| **Public API** | Transaction decision only | Customer-facing systems |
| **Internal Systems** | Full API access, high rate limits | Core banking integration |
| **SOC Analyst** | Security dashboard, review queue | Security operations |
| **Administrator** | All endpoints, config changes | System management |

### Implementation

```python
# Example: Extract API key from headers
api_key = request.headers.get("Authorization", "").replace("Bearer ", "")

# Validate and get permissions
permissions = auth_service.validate_api_key(api_key)

if not permissions.can_access(endpoint):
    raise HTTPException(status_code=403, detail="Forbidden")
```

---

## Data Encryption

### Transport Layer Security (TLS)

**Requirements:**
- **TLS 1.3** required (TLS 1.2 minimum)
- **Strong ciphers only:**
  - `TLS_AES_256_GCM_SHA384`
  - `TLS_CHACHA20_POLY1305_SHA256`
  - `TLS_AES_128_GCM_SHA256`
- **Certificate requirements:**
  - Valid certificate from trusted CA
  - 2048-bit RSA or 256-bit ECDSA minimum
  - Certificate renewal: 90 days before expiry

**Configuration:**

```nginx
# Nginx example
ssl_protocols TLSv1.3 TLSv1.2;
ssl_ciphers 'TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256';
ssl_prefer_server_ciphers on;
```

### Data at Rest

**Sensitive Fields Requiring Encryption:**
- User IDs (hashed)
- Card numbers (tokenized, last 4 digits only)
- IP addresses (anonymized after 30 days)
- Device IDs (hashed)

**Encryption Standards:**
- **Algorithm:** AES-256-GCM
- **Key Management:** AWS KMS, Azure Key Vault, or HashiCorp Vault
- **Key Rotation:** Every 90 days

**Database Encryption:**

```sql
-- SQLite encryption (production should use PostgreSQL with pgcrypto)
PRAGMA key = '<encryption_key>';
PRAGMA cipher = 'aes-256-gcm';
```

### Field-Level Encryption

Critical fields are encrypted individually:

```python
from cryptography.fernet import Fernet

# Encrypt PII before storage
def encrypt_field(plaintext: str, key: bytes) -> str:
    f = Fernet(key)
    return f.encrypt(plaintext.encode()).decode()

# Example: Encrypt user ID
encrypted_user_id = encrypt_field(user_id, encryption_key)
```

---

## PII & Sensitive Data Handling

### Data Classification

| Level | Examples | Handling |
|-------|----------|----------|
| **Public** | Decision codes, timestamps | No special handling |
| **Internal** | Feature values, scores | Encrypt in transit |
| **Confidential** | User IDs, device IDs | Encrypt at rest + transit |
| **Restricted** | Full card numbers, SSNs | Never store, tokenize only |

### PII Masking

**Automatic masking in logs:**

```python
# Before logging
user_id = "user_12345"
masked_id = f"user_***{user_id[-4:]}"  # user_***2345

# Card masking
card = "1234567890123456"
masked_card = f"****-****-****-{card[-4:]}"  # ****-****-****-3456
```

**Log Sanitization:**
- No full card numbers in logs
- User IDs hashed or masked
- IP addresses anonymized after analysis
- Automatic PII detection and redaction

### Data Retention

| Data Type | Retention Period | Justification |
|-----------|------------------|---------------|
| Transaction decisions | 7 years | Regulatory compliance (PCI-DSS) |
| Audit logs | 3 years | Compliance, investigations |
| Security events | 1 year | Threat analysis, SOC review |
| API access logs | 90 days | Performance monitoring |
| Temporary blocks | 30 days | Rate limiting, abuse prevention |

**Automatic Deletion:**

```python
# Scheduled cleanup job
def cleanup_old_data():
    # Delete logs older than retention period
    db.execute("""
        DELETE FROM api_access_logs
        WHERE created_at < DATE('now', '-90 days')
    """)
```

### Data Minimization

**Principle:** Only collect what's necessary.

- **Don't store:** Full card numbers, CVVs, PINs
- **Tokenize:** Use last 4 digits + token reference
- **Hash:** User identifiers when full value not needed
- **Anonymize:** IP addresses after analysis

---

## Institute Security Features

### Threat Detection

The **Institute Security Engine** monitors for:

#### 1. **API Abuse Detection**
- Request rate anomalies (>100 req/min warning, >500 req/min critical)
- Error rate spikes (>10% warning, >25% critical)
- Unusual endpoint access patterns

#### 2. **Insider Threat Monitoring**
- Off-hours access (22:00 - 06:00)
- First-time sensitive endpoint access
- Unusual data volume requests (>3x normal)

#### 3. **Brute Force Protection**
- Failed authentication tracking
- Automatic blocking (10 failures in 15 minutes)
- Progressive delays

#### 4. **Data Exfiltration Prevention**
- Large data request monitoring
- Rapid sequential requests (>50 in 60 seconds)
- Volume anomaly detection

#### 5. **Privilege Escalation Detection**
- Access to admin/internal endpoints
- Unusual permission scope requests

### Security Event Levels

| Level | Severity | Action | Examples |
|-------|----------|--------|----------|
| **0 - INFO** | Informational | Log only | Normal access patterns |
| **1 - LOW** | Minor anomaly | Log + monitor | Slight rate increase |
| **2 - MEDIUM** | Suspicious | Flag for review | Off-hours access |
| **3 - HIGH** | Serious threat | Alert + review | High error rate |
| **4 - CRITICAL** | Active breach | Auto-block + escalate | Brute force, data exfiltration |

### Automatic Response

```python
# Automatic blocking on critical threats
if event.threat_level >= ThreatLevel.HIGH.value:
    # Block source immediately
    security_engine.block_source(source_id)
    rate_limiter.block_source(source_id)

    # Alert SOC team (webhook/email)
    soc_alert.send(event)

    # Log for audit
    event_store.store_event(event)
```

---

## Rate Limiting & API Protection

### Rate Limit Tiers

| Tier | Requests/Minute | Burst Capacity | Use Case |
|------|-----------------|----------------|----------|
| **Free** | 20 | 10 | Public/unauthenticated |
| **Basic** | 100 | 30 | Standard authenticated |
| **Premium** | 500 | 100 | High-volume customers |
| **Internal** | 2000 | 500 | Internal systems |
| **Unlimited** | ∞ | ∞ | Admin/monitoring |

### Token Bucket Algorithm

Allows bursts while enforcing average limits:

```
Capacity: 30 tokens (burst)
Refill: 100 tokens/minute = 1.67 tokens/second

Request → Consume 1 token
If tokens available → Allow
If no tokens → Rate limit (429)
```

### Rate Limit Response

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 5

{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again in 5 seconds.",
  "retry_after_seconds": 5,
  "limit": 100,
  "tier": "basic"
}
```

### Automatic Blocking

**Triggers:**
- 3+ rate limit violations in 5 minutes
- Block duration: 5 minutes (configurable by tier)
- Escalates to permanent block after repeated violations

**Override:**
SOC analysts can manually unblock sources via API:

```bash
POST /v1/security/sources/{source_id}/unblock
{
  "analyst_id": "analyst_001",
  "reason": "False positive, legitimate traffic spike"
}
```

---

## Audit Logging

### What We Log

#### 1. **Security Events**
- All threat detections (INFO and above)
- Automatic blocks/unblocks
- Manual analyst actions

#### 2. **API Access Logs**
- Endpoint, method, timestamp
- Source ID, IP address
- Status code, latency
- Rate limit decisions

#### 3. **Audit Trail**
- Who accessed what resource
- When action occurred
- Success/failure status
- IP, user agent, metadata

### Log Format

**Structured JSON Logging:**

```json
{
  "timestamp": "2024-01-15T14:32:10.123Z",
  "level": "INFO",
  "event_type": "api_access",
  "source_id": "api_key_abc123",
  "endpoint": "/v1/decision",
  "method": "POST",
  "status_code": 200,
  "latency_ms": 45.2,
  "ip_address": "10.0.1.42",
  "metadata": {
    "decision_code": 0,
    "fraud_score": 0.12
  }
}
```

### Log Storage

- **Location:** SQLite (MVP), PostgreSQL (production)
- **Retention:** 90 days (API access), 1 year (security events), 3 years (audit trail)
- **Access:** Restricted to SOC analysts and admins
- **Integrity:** Write-only, append-only logs with checksums

### SIEM Integration

Export logs to SIEM systems:

```python
# Forward to Splunk/ELK/Azure Sentinel
def forward_to_siem(event: dict):
    siem_client.send_event(
        source="fraud_middleware",
        event_type=event["event_type"],
        data=event
    )
```

---

## Compliance

### GDPR (General Data Protection Regulation)

**Requirements:**
- ✅ Data minimization (only necessary fields)
- ✅ Purpose limitation (fraud detection only)
- ✅ Storage limitation (defined retention periods)
- ✅ Right to erasure (user data deletion on request)
- ✅ Data breach notification (<72 hours)
- ✅ Privacy by design (encryption, PII masking)

**Implementation:**
```python
# GDPR: Right to erasure
def delete_user_data(user_id: str):
    db.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM audit_logs WHERE source_id = ?", (user_id,))
    # Log deletion request for compliance
    audit_log("gdpr_deletion", user_id=user_id)
```

### PCI-DSS (Payment Card Industry)

**Applicable Requirements:**
- ✅ 1.1 - Firewall configuration (network perimeter)
- ✅ 2.1 - Vendor-supplied defaults changed
- ✅ 3.4 - Card data encrypted in transit (TLS 1.3)
- ✅ 4.1 - Strong cryptography (AES-256)
- ✅ 6.5 - Secure development (input validation, no SQLi)
- ✅ 8.2 - Strong authentication
- ✅ 10.1 - Audit trail for all access

**Token Storage:**
- Never store full PAN (Primary Account Number)
- Use last 4 digits only: `****-****-****-1234`
- Reference token from payment processor

### DPDP (India Digital Personal Data Protection)

**Requirements:**
- ✅ Consent for processing
- ✅ Purpose limitation
- ✅ Data accuracy
- ✅ Storage limitation
- ✅ Security safeguards
- ✅ Data breach notification
- ✅ Cross-border transfer restrictions

### SOC 2 Type II

**Control Categories:**
- ✅ Security (access controls, encryption)
- ✅ Availability (uptime monitoring, failover)
- ✅ Confidentiality (data classification, DLP)
- ✅ Processing Integrity (input validation, checksums)

---

## Incident Response

### Security Incident Classification

| Severity | Examples | Response Time | Escalation |
|----------|----------|---------------|------------|
| **P1 - Critical** | Active breach, data exfiltration | Immediate | CISO, Legal |
| **P2 - High** | Brute force attack, DDoS | <15 minutes | Security team |
| **P3 - Medium** | Unusual access patterns | <1 hour | SOC analyst |
| **P4 - Low** | Minor anomalies | <4 hours | Monitoring |

### Incident Response Workflow

1. **Detection** - Security engine flags event
2. **Triage** - SOC analyst reviews in queue
3. **Investigation** - Audit logs, access patterns
4. **Containment** - Block source, isolate affected systems
5. **Remediation** - Fix vulnerability, update rules
6. **Recovery** - Restore normal operations
7. **Post-Incident** - Review, improve detection

### SOC Analyst Actions

**Review Queue:**
```bash
GET /v1/security/events/review-queue
```

**Investigate Event:**
```bash
GET /v1/security/events?source_id=suspicious_api_key
GET /v1/security/audit-trail?source_id=suspicious_api_key
```

**Take Action:**
```bash
# Mark as reviewed
POST /v1/security/events/{event_id}/review
{
  "analyst_id": "analyst_001",
  "action": "escalate",
  "notes": "Potential insider threat, escalating to CISO"
}

# Or dismiss
POST /v1/security/events/{event_id}/review
{
  "analyst_id": "analyst_001",
  "action": "dismiss",
  "notes": "False positive, legitimate batch job"
}
```

### Breach Notification

If personal data breach detected:

1. **Immediate** - Contain breach, preserve evidence
2. **<72 hours** - Notify regulatory authority (GDPR)
3. **<24 hours** - Notify affected customers if high risk
4. **Document** - All actions, timeline, impact assessment

---

## Security Best Practices

### Deployment

**Production Checklist:**
- [ ] TLS 1.3 configured on all endpoints
- [ ] API keys rotated and stored in secrets manager
- [ ] Database encryption enabled
- [ ] Firewall rules restrict access to trusted IPs
- [ ] Rate limiting enabled and tuned
- [ ] SIEM integration configured
- [ ] Backup and disaster recovery tested
- [ ] Security event alerting configured
- [ ] SOC team trained on review workflows

### Monitoring

**Critical Metrics:**
- Security events per hour (baseline: <10)
- Blocked sources (baseline: 0-2)
- Rate limit violations (baseline: <5/hour)
- Failed authentication attempts (baseline: <10/hour)
- API error rate (baseline: <1%)

**Alerts:**
```yaml
# Example alert configuration
alerts:
  - name: "Critical Security Event"
    condition: "threat_level >= 4"
    action: "page_soc_team"

  - name: "High Rate Limit Violations"
    condition: "violations > 10 in 5min"
    action: "notify_soc_team"

  - name: "Unusual Off-Hours Access"
    condition: "off_hours_events > 5 in 1hour"
    action: "create_ticket"
```

### Secure Development

**Code Security:**
- Input validation on all endpoints
- Parameterized SQL queries (no string concatenation)
- Dependency vulnerability scanning (`safety check`)
- Static analysis (`bandit`, `semgrep`)
- Secrets scanning (`truffleHog`, `git-secrets`)

**Testing:**
- Security tests for all endpoints
- Rate limiting tests
- Authentication/authorization tests
- Injection attack tests (SQLi, XSS, command injection)

---

## Contact & Support

**Security Issues:**
- Email: security@example.com
- Bug Bounty: HackerOne (if applicable)
- Encryption: PGP key available

**SOC Operations:**
- 24/7 Security Operations Center
- Escalation: security-escalation@example.com
- Phone: +1-XXX-XXX-XXXX (emergencies only)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2024-01-15 | Added institute security, rate limiting, SOC workflow |
| 1.0.0 | 2024-01-01 | Initial release with customer fraud detection |

---

**Last Updated:** 2024-01-15
**Maintained By:** Security Team
**Review Cycle:** Quarterly
