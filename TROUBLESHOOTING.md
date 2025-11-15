# Troubleshooting Guide - Security & Fraud Playground

## Common Issues and Solutions

### Issue: start-playground.sh closes immediately (Windows/Git Bash)

**Symptoms:**
- Script opens and closes quickly
- Gets to "Waiting for backend to start..." then exits

**Note:** Frontend runs on port 3000, not 5173

**Cause:** Backend fails to start, usually due to:
1. Missing dependencies
2. Port already in use
3. Python/module import errors

**Solutions:**

#### Solution 1: Use Windows Batch File (Recommended for Windows)
```batch
# Instead of start-playground.sh, use:
start-playground-simple.bat
```

#### Solution 2: Manual Startup (See what's failing)

**Terminal 1 - Start Backend:**
```bash
# Test if backend starts
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# If you see errors, install missing dependencies:
pip install fastapi uvicorn pydantic numpy scikit-learn onnxruntime
```

**Terminal 2 - Start Frontend:**
```bash
cd demo/frontend
npm install  # First time only
npm run dev
```

#### Solution 3: Check Logs
```bash
# After script closes, check:
cat logs/backend.log
cat logs/pip-install.log

# Common errors and fixes:
```

### Common Backend Errors

#### Error: "ModuleNotFoundError: No module named 'fastapi'"
**Fix:**
```bash
pip install fastapi uvicorn pydantic numpy scikit-learn onnxruntime aiohttp
```

#### Error: "Address already in use (port 8000)"
**Fix:**
```bash
# Windows (Command Prompt/PowerShell):
netstat -ano | findstr :8000
taskkill /F /PID <PID>

# Git Bash/Linux:
lsof -ti:8000 | xargs kill -9

# Or try different port:
python -m uvicorn api.main:app --host 0.0.0.0 --port 8001
```

#### Error: "No module named 'api'"
**Fix:** Make sure you're in the project root directory
```bash
cd fraud-middleware-mvp
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

#### Error: "cannot import name 'RulesEngine'"
**Fix:** Missing module files - check project structure
```bash
# Verify files exist:
ls api/models/rules.py
ls api/models/ml_engine.py
ls api/models/policy.py
```

### Common Frontend Errors

#### Error: "npm: command not found"
**Fix:** Install Node.js from https://nodejs.org/

#### Error: "Cannot find module"
**Fix:**
```bash
cd demo/frontend
rm -rf node_modules package-lock.json
npm install
```

#### Error: "Port 3000 already in use"
**Fix:**
```bash
# Kill process on port 3000
# Windows:
netstat -ano | findstr :3000
taskkill /F /PID <PID>

# Git Bash/Linux:
lsof -ti:3000 | xargs kill -9
```

### Rate Limiting Issues

#### Issue: Getting "rate_limit_exceeded" during testing

**Fix Option 1 - Reset via API:**
```bash
curl -X POST "http://localhost:8000/v1/security/sources/127.0.0.1/reset?analyst_id=admin"
```

**Fix Option 2 - Restart server:**
```bash
./stop-playground.sh
./start-playground.sh
```

**Fix Option 3 - Wait 5 minutes** (block expires automatically)

### Python Version Issues

#### Issue: "python3: command not found"
**Fix:** Windows typically uses `python` not `python3`
```bash
# Try:
python --version

# Or create an alias:
alias python3=python
```

#### Issue: Wrong Python version (need 3.8+)
**Fix:**
```bash
# Check version:
python --version

# If < 3.8, download from:
# https://www.python.org/downloads/
```

### Git Bash Specific Issues

#### Issue: Script won't execute
**Fix:**
```bash
# Make executable:
chmod +x start-playground.sh

# Run with bash explicitly:
bash start-playground.sh
```

#### Issue: Colors not showing
**Fix:** This is cosmetic, script still works

#### Issue: lsof command not found
**Fix:** Script should handle this, but if issues persist use the .bat file on Windows

### Database Issues

#### Issue: "database is locked"
**Fix:**
```bash
# Close any DB browser tools
# Delete and recreate:
rm data/security_events.db
# Will be recreated on next start
```

#### Issue: "table already exists"
**Fix:** Normal SQLite behavior, safe to ignore

### Network/Firewall Issues

#### Issue: Cannot access http://localhost:8000
**Check:**
1. Is backend running? `curl http://localhost:8000/health`
2. Firewall blocking? Temporarily disable to test
3. Using VPN? May interfere with localhost

#### Issue: Frontend can't reach backend (CORS errors)
**Fix:** Backend allows all origins for development
```python
# Already configured in api/main.py:
allow_origins=["*"]
```

### Performance Issues

#### Issue: Slow startup (>2 minutes)
**Possible causes:**
1. First time npm install (normal, 1-2 minutes)
2. Slow disk/antivirus scanning
3. Many Python packages to install

#### Issue: High CPU usage
**Normal during:**
- npm install (first time)
- ML model loading
- Burst testing (1000 requests)

### Testing & Demo Issues

#### Issue: "Failed to fetch" in playground UI
**Causes:**
1. Backend not running
2. Wrong API URL in config

**Fix:**
```bash
# Check backend:
curl http://localhost:8000/health

# Update frontend config if needed:
# demo/frontend/src/config.js
export const API_BASE_URL = 'http://localhost:8000'
```

#### Issue: Empty dashboard/no data
**This is normal** on first start. Generate data by:
1. Go to "Fraud Tester" and run scenarios
2. Go to "Rate Limiting" and send requests
3. Events will appear in Security Monitor

## Platform-Specific Instructions

### Windows Users

**Recommended:** Use `start-playground-simple.bat`

Advantages:
- ✓ Native Windows batch file
- ✓ Better error handling
- ✓ Auto-opens browser
- ✓ Clearer error messages

```batch
# Double-click or run:
start-playground-simple.bat
```

### Mac/Linux Users

Use the bash script:
```bash
chmod +x start-playground.sh
./start-playground.sh
```

### WSL (Windows Subsystem for Linux) Users

Should work like Linux, but:
- Use Linux paths
- May need to access via `localhost` or WSL IP
- Browser may need explicit IP address

## Getting Help

### Debug Mode - See What's Happening

```bash
# Terminal 1 - Backend with logs visible:
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Frontend with logs visible:
cd demo/frontend
npm run dev

# Watch what happens when you use the UI
```

### Logs Location

After running start script:
- `logs/backend.log` - Backend errors and requests
- `logs/frontend.log` - Frontend build/dev server logs
- `logs/pip-install.log` - Python package installation
- `logs/npm-install.log` - Node package installation

### Check System Health

```bash
# Backend health:
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "components": {
    "api": "up",
    "rules_engine": "up",
    "ml_engine": "up",
    "policy_engine": "up",
    "security_engine": "up",
    "rate_limiter": "up",
    "event_store": "up"
  }
}
```

### Verify Dependencies

```bash
# Python dependencies:
pip list | grep -E "fastapi|uvicorn|pydantic|numpy|scikit|onnx"

# Node/npm:
node --version  # Should be 14+
npm --version   # Should be 6+

# Frontend dependencies:
cd demo/frontend
npm list --depth=0
```

## Still Having Issues?

### Clean Slate - Nuclear Option

```bash
# 1. Stop everything
./stop-playground.sh  # or stop-playground.bat

# 2. Clean Python cache
find . -type d -name __pycache__ -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# 3. Clean frontend
cd demo/frontend
rm -rf node_modules package-lock.json
npm install
cd ../..

# 4. Clean data
rm -rf data/
rm -rf logs/

# 5. Reinstall Python deps
pip install --force-reinstall fastapi uvicorn pydantic numpy scikit-learn onnxruntime

# 6. Try starting again
./start-playground.sh
```

### Minimal Test - Does anything work?

```bash
# Test 1: Python imports
python -c "import fastapi, uvicorn; print('OK')"

# Test 2: Start backend manually
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Test 3: Query backend
curl http://localhost:8000/health

# Test 4: Start frontend manually
cd demo/frontend && npm run dev

# If all work manually, script issue
# If some fail, dependency issue
```

## Known Issues (Fixed)

### Security Test Playground - All tests showing api_abuse (FIXED in v2.0.1)

**Symptoms:**
- All security tests (Brute Force, Data Exfiltration, Insider Threat) showed `api_abuse` instead of their specific threat types

**Cause:**
- API Abuse test exhausted rate limit, blocking subsequent tests
- Tests never reached specific threat detection logic

**Fix Applied:**
- Modified security monitoring middleware to bypass rate limiting for security test requests
- Tests now run independently with correct threat detection
- Normal API rate limiting unchanged

**Verification:**
- Navigate to Security Test Playground in UI
- Each test should now show its correct threat type (brute_force, data_exfiltration, unusual_access)

### SOC Workspace - Clear All Button Issues (FIXED in v2.0)

**Symptoms:**
- "Clear All" button showed wrong count (100 instead of actual)
- Events still visible after clearing

**Cause:**
- API had default limit of 100 events
- Frontend not refreshing properly after clear

**Fix Applied:**
- Increased API limits to handle large queues (10,000+ events)
- Fixed frontend state management for immediate refresh
- Added proper console logging for debugging

## Contact

If none of these solutions work:
1. Note which step fails
2. Copy error message from logs/
3. Note your OS and Python version
4. Report the issue with these details

---

**Most Common Fix:** Use `start-playground-simple.bat` on Windows instead of the bash script!
