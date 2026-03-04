# Guide: Debugging Workflow

Step-by-step UI debugging procedure.

---

## Pattern

### Debugging Methodology

1. **Baseline snapshot** - Capture initial state before changes
2. **Navigate/Snapshot** - Navigate to target page, capture state
3. **Console/Network** - Check for errors and failed requests
4. **Interact** - Interact with UI element
5. **Read code** - Component → store → API call
6. **Fix** - Make necessary code changes
7. **Restart** - Restart dev servers if config/CSS/contracts changed
8. **Verify** - Verify fix by interacting again
9. **Screenshot + diff** - Take screenshot and read it
10. **Re-test** - Test complete user flow

### Tools Priority

Snapshot → Console → Network → Screenshot → Evaluate

### Screenshot Verification (MANDATORY)

After taking a screenshot, immediately read the saved image. Do not declare success without reading the capture.

### When to Restart Dev Servers

- Modified settings JSON
- Modified CSS files
- Modified backend API contracts
- Modified environment variables

### Common Issue Categories

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| UI fetch fails | Backend error | Backend logs, CORS, endpoint exists |
| UI doesn't update | File not saved | Hard refresh, restart dev server |
| Console type errors | Contract mismatch | TypeScript types vs backend response |
| Styling doesn't apply | Token not synced | Restart frontend, check settings JSON |

---

## Project Implementation

### Dev Server Commands

**Frontend (Terminal 1):**
```bash
cd ~/projects/Universal-API/src/frontend
export VITE_API_URL=http://localhost:8000
npm run dev -- --host 0.0.0.0 --port 4173
```

**Backend (Terminal 2):**
```bash
conda activate Universal-API
cd ~/projects/Universal-API
uvicorn src.backend.web_api:app --host 0.0.0.0 --port 8000
```

**Clear occupied port:**
```bash
lsof -ti:4173 | xargs kill -9
```

### Backend Verification

Before blaming the UI, verify backend is working:

```bash
# Check backend is running
ps aux | grep uvicorn

# Test health endpoint
curl http://localhost:8000/health

# Test target endpoint
curl http://localhost:8000/api/pipelines

# Check OpenAPI docs
# Open http://localhost:8000/docs in browser
```

### Browser Tool Usage

**Baseline snapshot:**
```
browser_snapshot()
```

**Navigate and snapshot:**
```
browser_navigate(url)
browser_snapshot()
```

**Check console/network:**
```
browser_console_messages()
browser_network_requests()
```

**Interact:**
```
browser_click(element, ref)
browser_type(element, ref, text)
```

**Screenshot verification:**
```
browser_take_screenshot(filename="after-fix.png")
read_file("after-fix.png")
```

### Common Fixes

**Issue: UI fetch fails**
1. Check backend logs for errors
2. Verify endpoint exists (`/docs`)
3. Check CORS configuration
4. Verify `VITE_API_URL` is set correctly

**Issue: UI doesn't update after code change**
1. Check if file is actually saved
2. Restart dev server if config changed
3. Hard refresh browser (Ctrl+Shift+R)
4. Clear browser cache

**Issue: Styling doesn't apply**
1. Verify CSS variables are synced (`cssVariableSync.ts`)
2. Check `default_app_settings.json` has correct values
3. Restart frontend dev server after settings changes
4. Verify Tailwind class names are correct
