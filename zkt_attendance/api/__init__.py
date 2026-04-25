"""
Whitelisted API methods for ZKT Attendance app.
Called from JS via frappe.call().
"""
import frappe
from frappe import _


@frappe.whitelist()
def test_machine_connection(machine_name):
    """Test connection to a ZKT Machine"""
    machine = frappe.get_doc("ZKT Machine", machine_name)
    result = machine.test_connection()
    return result


@frappe.whitelist()
def fetch_attendance_logs(machine_name, from_date=None, to_date=None, clear_device=False):
    """
    Fetch attendance logs from a ZKT Machine as a background job.
    
    Args:
        machine_name: Name of the ZKT Machine document
        from_date: Start date filter (optional)
        to_date: End date filter (optional)  
        clear_device: Whether to clear device logs after fetching (deprecated, always False)
    """
    # Queue the fetch as a background job
    frappe.enqueue(
        method=_fetch_attendance_logs_background,
        machine_name=machine_name,
        from_date=from_date,
        to_date=to_date,
        job_name=f"Fetch Logs - {machine_name}",
        queue="default"
    )
    
    return {
        "success": True,
        "message": f"Background job started for {machine_name}. You can continue working."
    }


def _fetch_attendance_logs_background(machine_name, from_date=None, to_date=None):
    """
    Background job: Fetch attendance logs from a ZKT Machine.
    
    Args:
        machine_name: Name of the ZKT Machine document
        from_date: Start date filter (optional)
        to_date: End date filter (optional)  
    """
    try:
        machine = frappe.get_doc("ZKT Machine", machine_name)
        result = machine.fetch_attendance(
            from_date=from_date,
            to_date=to_date,
            clear_device=False
        )
        
        # Log the result
        frappe.log_error(
            title=f"Attendance Fetch Result - {machine_name}",
            message=f"New: {result.get('new_records', 0)}, Skipped: {result.get('skipped', 0)}, Errors: {result.get('errors', 0)}"
        )
        
        # Optionally create a notification or log entry
        if result.get('success'):
            frappe.msgprint(
                msg=f"✅ Fetch completed for {machine_name}. New records: {result.get('new_records', 0)}",
                title="Attendance Fetch Success",
                indicator="green"
            )
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            f"Background Fetch Error - {machine_name}"
        )


@frappe.whitelist()
def fetch_all_machines(from_date=None, to_date=None):
    """Fetch attendance from all active machines"""
    machines = frappe.get_all(
        "ZKT Machine",
        filters={"is_active": 1},
        fields=["name"]
    )

    if not machines:
        return {"success": False, "message": "No active machines found"}

    results = {}
    for m in machines:
        machine_doc = frappe.get_doc("ZKT Machine", m.name)
        results[m.name] = machine_doc.fetch_attendance(
            from_date=from_date,
            to_date=to_date
        )

    return {"success": True, "results": results}


@frappe.whitelist()
def get_device_users(machine_name):
    """Get all users enrolled on a ZKT Machine"""
    machine = frappe.get_doc("ZKT Machine", machine_name)
    from zkt_attendance.utils.zk_connector import ZKConnector
    connector = ZKConnector(machine)
    return connector.get_device_users()


@frappe.whitelist()
def process_pending_logs(machine_name=None):
    """Process all pending ZKT Attendance Log records to create Employee Checkins"""
    filters = {"status": "Pending"}
    if machine_name:
        filters["machine"] = machine_name

    pending_logs = frappe.get_all(
        "ZKT Attendance Log",
        filters=filters,
        fields=["name"]
    )

    processed = 0
    errors = 0

    for log_ref in pending_logs:
        log = frappe.get_doc("ZKT Attendance Log", log_ref.name)
        success = log.create_checkin()
        if success:
            processed += 1
        else:
            errors += 1

    return {
        "success": True,
        "processed": processed,
        "errors": errors,
        "message": f"Processed {processed} records. Errors: {errors}"
    }


@frappe.whitelist()
def get_attendance_summary(machine_name=None, from_date=None, to_date=None):
    """Get attendance summary statistics"""
    filters = {}
    if machine_name:
        filters["machine"] = machine_name
    if from_date:
        filters["timestamp"] = [">=", from_date]
    if to_date:
        filters["timestamp"] = ["<=", to_date + " 23:59:59"]

    total = frappe.db.count("ZKT Attendance Log", filters)

    status_counts = {}
    for status in ["Pending", "Processed", "Skipped", "Error"]:
        f = dict(filters)
        f["status"] = status
        status_counts[status.lower()] = frappe.db.count("ZKT Attendance Log", f)

    return {
        "total": total,
        "status_counts": status_counts
    }
