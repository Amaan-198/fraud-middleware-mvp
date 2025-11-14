# Security & Fraud Playground UI

Interactive web interface for testing and exploring the Allianz Fraud Middleware MVP's fraud detection and security features.

## Overview

This is a unified playground UI that provides:

- **Dashboard** - Real-time overview of system health, security metrics, and recent events
- **Fraud Tester** - Interactive fraud decision testing with sample scenarios
- **Security Monitor** - View and filter security events and threats
- **SOC Workspace** - Analyst tools for reviewing events and managing blocked sources
- **Rate Limiting** - Test and observe rate limiting behavior across different tiers
- **Security Test** - Automated security scenario testing (API abuse, brute force, data exfiltration, insider threats)
- **Audit Trail** - Complete audit log of all security and fraud operations

## Prerequisites

- Node.js 18+ and npm
- Backend API running on `http://localhost:8000` (or configure via environment variable)

## Quick Start

### 1. Install Dependencies

```bash
cd demo/frontend
npm install
```

### 2. Start the Development Server

```bash
npm run dev
```

The playground will be available at `http://localhost:3000`

### 3. Ensure Backend is Running

The UI expects the backend API to be running. Start it with:

```bash
# From project root
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Configuration

### API URL

By default, the frontend connects to `http://localhost:8000`. To change this:

**Option 1: Environment Variable**

Create a `.env` file in `demo/frontend/`:

```env
VITE_API_URL=http://your-backend-url:8000
```

**Option 2: Edit config.js**

Modify `src/config.js`:

```javascript
export const API_BASE_URL = 'http://your-backend-url:8000';
```

### Development Server Port

To change the frontend port, edit `vite.config.js`:

```javascript
export default defineConfig({
  server: {
    port: 3001,  // Change to desired port
    // ...
  }
})
```

## Features Guide

### 1. Dashboard

**Purpose**: System overview and health monitoring

**Features**:
- Real-time system health checks for decision pipeline and security subsystem
- Key metrics: total events, pending reviews, blocked sources, active monitoring
- Threat level and type distribution charts
- Recent high-priority security events table
- Auto-refresh every 10 seconds

**Use Cases**:
- Quick system health check
- Monitor security event trends
- Identify high-priority incidents

---

### 2. Fraud Tester

**Purpose**: Test fraud detection decisions interactively

**Features**:
- Pre-configured sample scenarios (normal, high amount, foreign location, suspicious pattern)
- Custom transaction builder
- Real-time decision results with:
  - Decision code (ALLOW, MONITOR, STEP-UP, REVIEW, BLOCK)
  - Fraud score and ML score
  - Processing latency
  - Rule flags and reasons
  - Top contributing ML features

**Use Cases**:
- Test fraud detection logic
- Validate scenario handling
- Performance testing (check latency)
- Demo to stakeholders

**Sample Scenarios**:
- **Normal Transaction**: Low amount, known location → ALLOW
- **High Amount**: Large transaction → MONITOR/REVIEW
- **Foreign Location**: Transaction from unusual country → STEP-UP
- **Suspicious Pattern**: New device, odd hours → REVIEW/BLOCK

---

### 3. Security Monitor

**Purpose**: View and analyze security events

**Features**:
- Real-time security event feed
- Advanced filtering:
  - Minimum threat level (INFO, LOW, MEDIUM, HIGH, CRITICAL)
  - Threat type (api_abuse, brute_force, data_exfiltration, etc.)
  - Source ID
  - Result limit
- Auto-refresh toggle
- Event statistics summary

**Use Cases**:
- Monitor ongoing security threats
- Investigate specific sources
- Filter by threat severity
- Compliance reporting

**Event Types**:
- `api_abuse` - High-volume API requests
- `brute_force` - Multiple failed authentication attempts
- `data_exfiltration` - Unusual data access patterns
- `anomalous_behavior` - Behavioral anomalies
- `rate_limit_violation` - Rate limit breaches

---

### 4. SOC Workspace

**Purpose**: Security Operations Center analyst tools

**Features**:

**Review Queue**:
- Events flagged for human review
- Event details with source risk profile
- One-click analyst actions:
  - Dismiss (false positive)
  - Investigate further
  - Escalate to senior analyst

**Blocked Sources**:
- List of currently blocked sources
- Reason, timestamp, threat level
- Auto-blocked vs manual block indicator
- One-click unblock with audit trail

**Use Cases**:
- Process security incidents
- Investigate high-risk sources
- Manage false positives
- Unblock legitimate users
- Maintain audit compliance

**Workflow**:
1. Analyst reviews event from queue
2. Views source risk profile (risk score, recent events, threat breakdown)
3. Takes action (dismiss, investigate, escalate)
4. Action is logged to audit trail
5. Event removed from queue

---

### 5. Rate Limiting Playground

**Purpose**: Test and visualize rate limiting behavior

**Features**:
- Test different rate limit tiers:
  - **Free**: 20/min, burst 10
  - **Basic**: 100/min, burst 30
  - **Premium**: 500/min, burst 100
  - **Internal**: 1000/min, burst 200
  - **Unlimited**: No limits
- Send burst requests (1-100)
- Real-time status monitoring:
  - Available tokens
  - Violation count
  - Block status
- Visual results:
  - Allowed/blocked timeline
  - Detailed request log
  - Summary statistics

**Use Cases**:
- Test rate limiting configurations
- Understand tier differences
- Demo abuse protection
- Validate token bucket algorithm
- Test temporary blocking after violations

**How It Works**:
1. Select a source ID and tier
2. Choose burst size
3. Send requests
4. Observe:
   - Which requests are allowed/blocked
   - Token depletion
   - Violation accumulation
   - Temporary blocks after 3 violations

---

### 6. Security Test Playground

**Purpose**: Automated security scenario testing

**Features**:
- Pre-configured security threat scenarios:
  - **API Abuse** (🚨): Send 120 rapid requests to trigger rate limiting
  - **Brute Force** (🔓): Simulate 15 failed authentication attempts
  - **Data Exfiltration** (📤): Large data access (150 records x 10 requests)
  - **Insider Threat** (🕵️): Off-hours privileged endpoint access
- Real-time progress tracking with visual progress bars
- Detailed test results showing:
  - Events generated
  - Threat type and level
  - Source blocking status
  - Individual security event details
- Configurable test source ID
- Results history display

**Use Cases**:
- Validate security detection logic
- Demo security features to stakeholders
- Test threat detection thresholds
- Verify auto-blocking behavior
- Training and education
- Integration testing

**How It Works**:
1. Select or customize test source ID
2. Click scenario button (API Abuse, Brute Force, etc.)
3. Watch real-time progress
4. Review results:
   - Number of events generated
   - Threat classification
   - Whether source was blocked
   - Detailed event breakdown
5. Run multiple scenarios to compare behavior

**Expected Results**:
- **API Abuse**: 20+ events at HIGH/CRITICAL level, possible blocking
- **Brute Force**: Multiple events, potential blocking after threshold
- **Data Exfiltration**: Events if baseline established (requires multiple runs)
- **Insider Threat**: Events for off-hours + privileged access patterns

---

### 7. Audit Trail

**Purpose**: Compliance and forensic audit logging

**Features**:
- Complete audit log of all system operations
- Summary statistics dashboard:
  - Total logs
  - Successful operations
  - Failed operations
  - Unique sources
- Detailed audit table with:
  - Timestamp (date + time)
  - Source ID
  - Action type (color-coded badges)
  - Resource affected
  - Success/failure status
  - Expandable metadata
- Recent activity timeline (last 10 logs)
- Auto-refresh toggle (10-second intervals)
- Manual refresh option

**Use Cases**:
- Compliance reporting (SOC 2, GDPR, etc.)
- Forensic investigation
- Security incident analysis
- Operations monitoring
- User activity tracking
- Troubleshooting and debugging

**Action Types Tracked**:
- `review_event` (👁️) - Analyst reviewed security event
- `unblock_source` (✅) - Source unblocked by analyst
- `set_rate_limit` (⏱️) - Rate limit tier changed
- `block_source` (🚫) - Source manually blocked
- `decision_request` (🔍) - Fraud decision requested
- `data_access` (📊) - Data accessed

**How It Works**:
1. View automatically loads latest audit logs
2. Review summary statistics at top
3. Scroll through detailed log table
4. Click "View metadata" to expand details
5. Check recent activity timeline for latest actions
6. Enable auto-refresh for real-time monitoring

**Data Retention**:
- Audit logs stored in SQLite database
- Persists across server restarts
- Production deployments should implement log rotation

---

## Project Structure

```
demo/frontend/
├── public/                  # Static assets
├── src/
│   ├── components/          # React components
│   │   ├── Dashboard.jsx
│   │   ├── FraudTester.jsx
│   │   ├── SecurityMonitor.jsx
│   │   ├── SocWorkspace.jsx
│   │   ├── RateLimitingPlayground.jsx
│   │   ├── SecurityTestPlayground.jsx
│   │   └── AuditTrail.jsx
│   ├── App.jsx              # Main app with tab navigation
│   ├── main.jsx             # React entry point
│   ├── config.js            # API configuration
│   └── index.css            # Global styles
├── index.html               # HTML template
├── package.json             # Dependencies
├── vite.config.js           # Vite configuration
├── tailwind.config.js       # Tailwind CSS config
└── README.md                # This file
```

## Development

### Build for Production

```bash
npm run build
```

Output will be in `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

### Adding New Features

1. **New Component**: Create in `src/components/`
2. **New API Endpoint**: Add to `src/config.js`
3. **New Tab**: Add to tabs array in `App.jsx`

## Troubleshooting

### Backend Connection Issues

**Problem**: "Failed to fetch" errors

**Solutions**:
- Verify backend is running: `curl http://localhost:8000/v1/decision/health`
- Check CORS settings in backend `api/main.py`
- Verify API_BASE_URL in `src/config.js`

### Port Already in Use

**Problem**: "Port 3000 is already in use"

**Solution**: Change port in `vite.config.js` or kill existing process:
```bash
lsof -ti:3000 | xargs kill -9
```

### Module Not Found

**Problem**: Import errors after fresh install

**Solution**:
```bash
rm -rf node_modules package-lock.json
npm install
```

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/decision` | POST | Fraud decision |
| `/v1/decision/health` | GET | Pipeline health |
| `/v1/security/events` | GET | Security events |
| `/v1/security/events/review-queue` | GET | Events needing review |
| `/v1/security/events/{id}/review` | POST | Review event |
| `/v1/security/sources/{id}/risk` | GET | Source risk profile |
| `/v1/security/sources/blocked` | GET | Blocked sources |
| `/v1/security/sources/{id}/unblock` | POST | Unblock source |
| `/v1/security/dashboard` | GET | Dashboard stats |
| `/v1/security/health` | GET | Security subsystem health |
| `/v1/security/rate-limits/{id}` | GET | Rate limit status |
| `/v1/security/rate-limits/{id}/tier` | POST | Set rate limit tier |

## Performance

- **Bundle Size**: ~150KB gzipped (production build)
- **Load Time**: <1s on modern browsers
- **Auto-refresh**: Dashboard (10s), Security Monitor (5s when enabled)
- **API Latency**: Typically <100ms for local backend

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Security Considerations

This is a **development/demo playground** and should not be exposed to the internet without:

1. **Authentication**: Add user login
2. **Authorization**: Role-based access control
3. **HTTPS**: Enable TLS
4. **Rate Limiting**: Protect frontend from abuse
5. **Input Validation**: Additional client-side validation

## Contributing

When adding new features:

1. Follow existing component structure
2. Use Tailwind CSS for styling
3. Handle loading and error states
4. Add helpful user feedback
5. Update this README

## License

Part of the Allianz Fraud Middleware MVP project.
