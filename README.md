# ZKT Attendance - Biometric Device Integration

A Frappe/ERPNext application that integrates ZKTeco biometric attendance devices with ERPNext, automatically fetching and processing attendance logs from the devices.

---

## 📋 Features

✅ **Automatic Background Sync** - Fetch attendance logs on a configurable schedule without blocking the UI
✅ **Flexible Sync Intervals** - Configure sync frequency per machine (5 minutes to 24+ hours)
✅ **Efficient Log Fetching** - Fetch only recent logs (configurable: last 7 days, 30 days, or all)
✅ **Automatic Employee Matching** - Maps device user IDs to ERPNext employees
✅ **Error Tracking** - Full audit trail of processing status and errors
✅ **Manual Fetch Control** - On-demand fetch with custom date ranges
✅ **Duplicate Prevention** - Automatic detection prevents duplicate Employee Checkins
✅ **Safe Data Handling** - Device logs are never deleted; safe to retry

---

## 🚀 Installation

### Prerequisites
- Frappe/ERPNext installed and running
- Python 3.6+
- `pyzk` library for device communication

### Steps

1. **Install the app:**
```bash
bench get-app zkt_attendance https://github.com/your-org/zkt_attendance
bench --site your-site-name install-app zkt_attendance
```

2. **Install Python dependency:**
```bash
pip install pyzk
```

3. **Run migrations:**
```bash
bench --site your-site-name migrate
bench --site your-site-name clear-cache
```

4. **Reload browser** (hard refresh: Ctrl+Shift+R)

---

## ⚙️ Configuration

### Step 1: Create ZKT Machine

Navigate to **ZKT Machine** list and create a new record:

#### Connection Settings
- **Machine Name** - Unique identifier (e.g., "Gate-01", "Main-Entrance")
- **IP Address** - Device IP (e.g., 192.168.1.100)
- **Port** - Device port (default: 4370)
- **Communication Password** - Device password (if required)
- **Timeout** - Connection timeout in seconds (default: 10)

#### Auto-Sync Settings ⭐
- **Sync Interval (minutes)** - How often to fetch logs (default: 30)
  - Minimum: 5 minutes recommended
  - Set to 60+ for less frequent machines
- **Fetch Last N Days** - Only fetch recent logs (default: 7 days)
  - Set to `0` to fetch ALL logs from device
  - Set to `7` to fetch only last 7 days (efficient)
  - Set to `1` for daily syncs

#### Other
- **Active** - Enable/disable auto-sync for this machine

### Step 2: Prepare Employee Records

For automatic employee matching, ensure your Employee records have:

**Option A (Recommended):**
- Go to **Employee** doctype
- Add field: `Attendance Device ID` (if not present)
- Fill with device user ID (e.g., "101", "102")

**Option B (Fallback):**
- Use existing `Employee ID` field (must match device user ID)

**Note:** Device user IDs are assigned on the biometric device itself.

### Step 3: Test Connection

1. Open a **ZKT Machine** record
2. Click **"Test Connection"** button
3. Should show: Firmware, Serial Number, Enrolled Users count ✅

---

## 🔄 How It Works

### Automatic Sync (Background Job)

1. **Scheduler** runs every 5 minutes (backend)
2. For each **Active** machine:
   - Checks if `sync_interval` time has elapsed since last fetch
   - If yes: Fetches logs from device (last N days based on config)
   - If no: Skips (waits for next interval)
3. For each log fetched:
   - Creates **ZKT Attendance Log** record
   - Matches `device_user_id` to Employee record
   - **Automatically creates Employee Checkin** (if employee matched)
   - Prevents duplicates automatically

### Manual Fetch

1. Open **ZKT Machine** record
2. Click **"Fetch Attendance"** button
3. Dialog shows:
   - From Date (default: last 7 days)
   - To Date (default: today)
4. Click **"Start Background Job"**
   - Job queues immediately
   - You can continue working
   - No UI freeze ⚡

### Data Flow

```
ZKTeco Device
    ↓
fetch_and_save_logs() [zk_connector.py]
    ↓
Create ZKT Attendance Log + resolve_employee()
    ↓
If employee matched: Create Employee Checkin
    ↓
Mark log as "Processed" ✅
```

---

## 📊 Monitoring & Troubleshooting

### View Sync Status

1. Open **ZKT Machine** record
2. **Dashboard** shows:
   - Last Fetch Status: Success/Failed/Partial
   - Last Fetch Time
   - Total Records Fetched

### Check Processing Status

Navigate to **ZKT Attendance Log** list:

| Status | Meaning | Action |
|--------|---------|--------|
| **Pending** | Not yet processed | Wait for next sync or manual trigger |
| **Processed** | ✅ Employee Checkin created | Success |
| **Skipped** | Employee not found | Update Employee with device ID |
| **Error** | Failed to create checkin | Check error_message field |

### Common Issues

#### ❌ "No matching employee found"

**Cause:** Employee record doesn't have `attendance_device_id` matching device user ID

**Solution:**
1. Go to **Employee** list
2. Edit each employee
3. Set **Attendance Device ID** = device user ID from machine (e.g., "101")
4. Save
5. Retry fetch

#### ❌ "Duplicate record already exists"

**Normal behavior.** Employee Checkin already exists for that timestamp.

**Check:** Open **Employee Checkin** list and search for the employee/date

#### ❌ Connection Failed

**Possible causes:**
- Wrong IP address
- Device not on network
- Port not accessible
- Communication password incorrect

**Solution:**
1. Verify IP: `ping 192.168.1.100` (or your device IP)
2. Check device settings for port and password
3. Test on device network directly
4. Check firewall rules

#### ⚠️ Slow Sync Speed

**Cause:** Fetching too many days back

**Solution:**
1. Reduce **Fetch Last N Days** (e.g., from 30 to 7)
2. Increase **Sync Interval** (e.g., from 30 to 60 minutes)
3. Disable device's built-in logging (if too large)

---

## 🔧 API Methods

All methods are whitelisted and callable from frontend/REST API:

### `fetch_attendance_logs(machine_name, from_date, to_date)`
Manual fetch with date range (runs as background job)

```python
frappe.call({
    method: "zkt_attendance.api.fetch_attendance_logs",
    args: {
        machine_name: "Gate-01",
        from_date: "2026-04-01",
        to_date: "2026-04-25"
    }
});
```

### `test_machine_connection(machine_name)`
Test device connectivity

```python
frappe.call({
    method: "zkt_attendance.api.test_machine_connection",
    args: { machine_name: "Gate-01" }
});
```

### `get_device_users(machine_name)`
List all enrolled users on device

```python
frappe.call({
    method: "zkt_attendance.api.get_device_users",
    args: { machine_name: "Gate-01" }
});
```

### `process_pending_logs(machine_name)`
Manually process pending logs (trigger Employee Checkin creation)

```python
frappe.call({
    method: "zkt_attendance.api.process_pending_logs",
    args: { machine_name: "Gate-01" }
});
```

---

## 📁 File Structure

```
zkt_attendance/
├── README.md
├── requirements.txt
├── setup.py
├── hooks.py                          # App configuration, scheduler settings
├── api/
│   └── __init__.py                   # Whitelisted API methods
├── utils/
│   ├── scheduler.py                  # Auto-sync scheduled task
│   └── zk_connector.py               # Device communication (pyzk wrapper)
└── zkt_attendance/
    ├── doctype/
    │   ├── zkt_machine/
    │   │   ├── zkt_machine.py        # Machine document class
    │   │   ├── zkt_machine.js        # Form UI and buttons
    │   │   └── zkt_machine.json      # Field definitions
    │   └── zkt_attendance_log/
    │       ├── zkt_attendance_log.py # Log document, Employee matching
    │       ├── zkt_attendance_log.js # Form UI
    │       └── zkt_attendance_log.json
    └── public/
        ├── css/
        └── js/
```

---

## 🔐 Security Notes

✅ **Safe Data Handling**
- Device logs are **never deleted** (clear_device option removed)
- Logs are stored in database before processing
- Can retry failed logs safely

✅ **Permissions**
- System Manager and HR Manager: Full access
- HR User: Read-only access

✅ **Device Password**
- Stored encrypted in database
- Not exposed in logs

---

## 📝 Scheduler Configuration

The app uses a 5-minute cron schedule. Modify in `hooks.py`:

```python
scheduler_events = {
    "cron": {
        "*/5 * * * *": [  # Every 5 minutes
            "zkt_attendance.utils.scheduler.auto_fetch_attendance"
        ],
    }
}
```

Each machine respects its own `sync_interval` - adjust per machine in the ZKT Machine form.

---

## 🐛 Debugging

### Enable Debug Logging

In Frappe console:
```python
frappe.log_error("Message here", "Custom Debug Label")
```

### Check Logs

**Error Logs:** Tools → System Console (search for "ZKT")

**Database Logs:** Monitor background jobs under the site's job queue

### Manual Test Sync

```bash
bench --site your-site-name execute "
from zkt_attendance.utils.scheduler import auto_fetch_attendance
auto_fetch_attendance()
print('Sync complete')
"
```

---

## 📦 Dependencies

- **frappe** - Web framework
- **pyzk** - ZKTeco device communication

Install via:
```bash
pip install pyzk
```

---

## 🤝 Support

For issues or questions:
1. Check **Troubleshooting** section above
2. Review **ZKT Attendance Log** status records
3. Check browser console (F12 → Console tab) for JavaScript errors
4. Check server logs: `bench logs`

---

## 📄 License

MIT License - See LICENSE file

---

## Changelog

### Version 1.0.0
- ✅ Automatic background sync with configurable intervals
- ✅ Efficient log fetching (fetch_last_days config)
- ✅ Automatic Employee matching
- ✅ Manual fetch with custom date ranges
- ✅ Duplicate prevention
- ✅ Full error tracking and logging
- ✅ Removed device log deletion for data safety
