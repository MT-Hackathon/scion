# Troubleshooting: Cursor Database Issues

Common problems and diagnostic information for Cursor's conversation history database.

---

## Database File Locations

| Platform | Path |
|----------|------|
| Windows | `%APPDATA%\Cursor\User\globalStorage\state.vscdb` |
| Linux | `~/.config/Cursor/User/globalStorage/state.vscdb` |
| macOS | `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb` |

**Related Files**:

- `state.vscdb-wal` - Write-Ahead Log (uncommitted transactions)
- `state.vscdb-shm` - Shared memory file for WAL
- `state.vscdb.backup` - Cursor's automatic backup
- `state.vscdb.corrupted.*` - Files Cursor marked as corrupted

**Configuration Files** (in `Cursor/User/`):

- `settings.json` - User preferences and extension settings
- `keybindings.json` - Custom keyboard shortcuts
- `snippets/` - User-defined code snippets

---

## Common Errors

### Error: "disk I/O error" (SQLite error 10)

**Symptoms**:

- MCP server fails to connect
- Scripts timeout or return I/O errors
- Current conversation works but history is inaccessible

**Causes**:

1. Database corruption during write
2. SQLite WAL mode conflicts when Cursor is running
3. Disk space issues

**Diagnosis**:

```bash
# Check if database is accessible
sqlite3 /path/to/state.vscdb "SELECT COUNT(*) FROM ItemTable;"

# Check for WAL files (indicates active use)
# Use 'ls -la' on Linux/macOS or 'dir' on Windows
ls -la /path/to/state.vscdb*

# Check database integrity
sqlite3 /path/to/state.vscdb "PRAGMA integrity_check;"
```

### Error: "database is locked"

**Cause**: Multiple processes accessing the database.

**Fix**: Close all Cursor instances before running scripts.

### Error: Database Not Found

**Cause**: Wrong path or database moved.

**Fix**: Set `CURSOR_DB_PATH` environment variable.

---

## Diagnostic Commands

### Quick Health Check

```bash
sqlite3 /path/to/state.vscdb "SELECT COUNT(*) FROM ItemTable;"
sqlite3 /path/to/state.vscdb "SELECT COUNT(*) FROM cursorDiskKV WHERE key LIKE 'bubbleId:%';"
sqlite3 /path/to/state.vscdb "SELECT key FROM ItemTable WHERE key LIKE 'cursor%' LIMIT 10;"
```

### List Conversation IDs

```bash
sqlite3 /path/to/state.vscdb \
  "SELECT DISTINCT substr(key, 10, 36) FROM cursorDiskKV WHERE key LIKE 'bubbleId:%' LIMIT 20;"
```

### Check Database Size and Fragmentation

```bash
# Linux/macOS
ls -lh /path/to/state.vscdb
# Windows (PowerShell)
(Get-Item /path/to/state.vscdb).length / 1MB

sqlite3 /path/to/state.vscdb "PRAGMA page_count; PRAGMA freelist_count;"
```

---

## Prevention

1. **Regular backups**: Run `backup-cursor-data.py` periodically to backup conversations and settings
2. **Keep Cursor updated**: Many database issues are fixed in updates
3. **Monitor disk space**: Low disk space can cause SQLite corruption
4. **Avoid force-killing Cursor**: This can leave WAL files in inconsistent state

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `backup-cursor-data.py` | Comprehensive backup of chat history, settings, and config files |
| `export-project-knowledge.py` | Export conversations to JSON/CSV/Markdown |
| `check-last-chat.py` | Quick test of database accessibility |

---

## When to Contact Support

- Database corruption persists
- Cursor crashes on startup
- Data loss that cannot be recovered from any backup
