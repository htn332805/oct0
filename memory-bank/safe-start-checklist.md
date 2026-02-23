# ✅ Pexpect Development Safe Start Checklist

**Before starting ANY pexpect development session, complete this checklist:**

---

## 🔍 **Pre-Session Verification** (5 minutes)

- [ ] **Read the incident lesson**: `memory-bank/write-safety-lesson-2026-02-21.md`
- [ ] **Review write safety rule**: Top of `pexpect.prompt.md` (⚠️ CRITICAL section)
- [ ] **Understand the procedure**: WRITE SAFETY VERIFICATION PROCEDURE in pexpect.prompt.md

---

## 📋 **Before Any File Write** (MANDATORY)

- [ ] **Identify target directory** where file will be created (e.g., `/root/github_repo/oct0/logs/`)
- [ ] **Verify .write_exception exists**:
  ```bash
  ls -la /path/to/target/.write_exception      # Check target directory
  ls -la /path/to/parent/.write_exception      # Check parent directory
  ```
- [ ] **If NEITHER exists**:
  - [ ] STOP immediately (do not proceed)
  - [ ] Ask user: "Should I create `.write_exception` in `/path/to/target/`?"
  - [ ] Wait for user confirmation
- [ ] **If ONE exists**:
  - [ ] PROCEED with file write
  - [ ] Document which directory had the `.write_exception`

---

## 🚀 **Starting Pexpect Session**

1. [ ] Read the incident lesson: `memory-bank/write-safety-lesson-2026-02-21.md`
2. [ ] Review write safety rule in pexpect.prompt.md
3. [ ] Check pexpect-memory for previous session knowledge:
   ```bash
   ls -la /root/github_repo/oct0/bin/instances/pexpect_dev/pexpect-memory/
   ```
4. [ ] Verify write permissions for target directory (see section below)

---

## 📊 **Logging Locations** (Safe Zones with .write_exception)

✅ **SAFE TO WRITE** (have .write_exception):
- `/root/github_repo/oct0/memory-bank/` - Can create/edit lesson files
- `/root/github_repo/oct0/plans/` - Can create plans
- `/root/github_repo/oct0/bin/instances/pexpect_dev/pexpect-memory/` - Pexpect knowledge accumulation
- `/root/github_repo/oct0/logs/` - **IF `.write_exception` exists** (verify first)

❌ **DANGER ZONE** (NO .write_exception unless created):
- Any directory not listed above
- **Always verify first**

---

## 🛠️ **Quick Verification Command**

```bash
# Run this before starting any file writes:
echo "=== Checking Write Permissions ===" && \
find /root/github_repo/oct0 -maxdepth 2 -name ".write_exception" -type f && \
echo "" && \
echo "✅ Ready to proceed if your target is in the list above" && \
echo "❌ STOP if your target is NOT in the list"
```

---

## 📚 **Reference Files**

- **Main Instruction**: `pexpect.prompt.md` (WRITE SAFETY ENFORCEMENT section at top)
- **Incident Details**: `memory-bank/write-safety-lesson-2026-02-21.md`
- **This Checklist**: `memory-bank/safe-start-checklist.md`

---

## ⚡ **Quick Reminders**

- **Write safety rule**: Absolute, non-negotiable, applies always
- **No exceptions**: Even if something "should" be writable, verify `.write_exception`
- **When in doubt**: Use DESIGN MODE (provide code, don't write files)
- **Always ask**: If unsure, ask the user for permission
- **Document everything**: Note which directories had `.write_exception`

---

**Last Updated**: 2026-02-21  
**Incident Reference**: Write safety violation in pexpect.prompt.md setup  
**Prevention Status**: ✅ FIXED and DOCUMENTED
