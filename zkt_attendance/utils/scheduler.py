"""
Scheduled tasks for ZKT Attendance auto-fetch
"""
import frappe
from datetime import datetime, timedelta


def auto_fetch_attendance():
    """
    Scheduled task: auto-fetch attendance from all active machines.
    Respects each machine's configured sync_interval and fetch_last_days.
    """
    machines = frappe.get_all(
        "ZKT Machine",
        filters={"is_active": 1},
        fields=["name", "machine_name", "ip_address", "port", "communication_password", "timeout", "sync_interval", "last_fetch_time", "fetch_last_days"]
    )

    if not machines:
        return

    current_time = datetime.now()

    for machine in machines:
        try:
            sync_interval = machine.sync_interval or 30  # Default to 30 minutes if not set
            fetch_last_days = machine.fetch_last_days or 7  # Default to 7 days if not set
            last_fetch = machine.last_fetch_time
            
            # Check if enough time has passed since last fetch
            if last_fetch:
                last_fetch_time = frappe.get_datetime(last_fetch)
                time_since_fetch = (current_time - last_fetch_time).total_seconds() / 60  # Convert to minutes
                
                if time_since_fetch < sync_interval:
                    # Skip this machine, not enough time has passed
                    continue
            
            # Calculate from_date based on fetch_last_days
            from_date = None
            if fetch_last_days > 0:
                from_date = (current_time - timedelta(days=fetch_last_days)).strftime('%Y-%m-%d')
            
            # Fetch attendance for this machine
            machine_doc = frappe.get_doc("ZKT Machine", machine.name)
            machine_doc.fetch_attendance(from_date=from_date)
            
        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                f"Auto Fetch Error - {machine.name}"
            )
