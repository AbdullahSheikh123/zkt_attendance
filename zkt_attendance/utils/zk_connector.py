"""
ZKTeco Device Connector
Handles all communication with ZKTeco biometric attendance devices
using the pyzk library.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime, get_datetime


PUNCH_TYPE_MAP = {
    0: "Check In",
    1: "Check Out",
    4: "Overtime In",
    5: "Overtime Out",
}


class ZKConnector:
    def __init__(self, machine_doc):
        """
        Args:
            machine_doc: ZKT Machine document or dict with connection details
        """
        self.machine = machine_doc
        self.machine_name = getattr(machine_doc, "name", None) or machine_doc.get("name")
        self.machine_label = getattr(machine_doc, "machine_name", None) or machine_doc.get("machine_name")
        self.ip = getattr(machine_doc, "ip_address", machine_doc.get("ip_address"))
        self.port = int(getattr(machine_doc, "port", machine_doc.get("port", 4370)))
        self.password = self._get_password(machine_doc)
        self.timeout = int(getattr(machine_doc, "timeout", machine_doc.get("timeout", 10)))
        self.zk = None

    def _get_password(self, machine_doc):
        """Return the decrypted communication password when available."""
        if hasattr(machine_doc, "get_password"):
            return machine_doc.get_password("communication_password") or 0
        return getattr(machine_doc, "communication_password", machine_doc.get("communication_password")) or 0

    def _get_zk_instance(self):
        """Create ZK library instance"""
        try:
            from zk import ZK
        except ImportError:
            frappe.throw(
                "pyzk library is not installed. Run: <code>pip install pyzk</code>",
                title="Missing Dependency"
            )
        password = int(self.password) if str(self.password).isdigit() else 0
        return ZK(
            self.ip,
            port=self.port,
            timeout=self.timeout,
            password=password,
            force_udp=False,
            ommit_ping=False
        )

    def test_connection(self):
        """Test connection to ZKT device. Returns dict with success/error."""
        conn = None
        try:
            zk = self._get_zk_instance()
            conn = zk.connect()
            if not conn:
                return {"success": False, "message": "Could not establish connection"}

            # Get device info
            firmware = conn.get_firmware_version() or "Unknown"
            serial = conn.get_serialnumber() or "Unknown"
            users = conn.get_users()
            user_count = len(users) if users else 0

            conn.disconnect()
            return {
                "success": True,
                "message": f"Connected successfully!",
                "firmware": firmware,
                "serial_number": serial,
                "user_count": user_count
            }
        except Exception as e:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass
            return {"success": False, "message": str(e)}

    def fetch_and_save_logs(self, from_date=None, to_date=None):
        """
        Fetch attendance logs from device and save to ZKT Attendance Log.
        Device logs are never deleted - this is safer and allows retrying failed imports.
        
        Args:
            from_date: Filter logs from this date (optional)
            to_date: Filter logs to this date (optional)
            
        Returns:
            dict with results summary
        """
        conn = None
        result = {
            "success": False,
            "total": 0,
            "new_records": 0,
            "skipped": 0,
            "skipped_existing": 0,
            "skipped_inactive": 0,
            "errors": 0,
            "message": ""
        }

        try:
            zk = self._get_zk_instance()
            conn = zk.connect()

            if not conn:
                result["message"] = "Could not establish connection to device"
                self._update_machine_status("Failed", 0)
                return result

            conn.disable_device()
            attendance_records = conn.get_attendance()
            conn.enable_device()

            if not attendance_records:
                conn.disconnect()
                result["success"] = True
                result["message"] = "No attendance records found on device"
                self._update_machine_status("Success", 0)
                return result

            active_employee_map = self._get_active_employee_map()
            latest_saved_timestamp = self._get_latest_saved_timestamp()
            from_datetime = get_datetime(from_date) if from_date else None
            to_datetime = get_datetime(to_date) if to_date else None

            if latest_saved_timestamp and not from_date:
                latest_saved_timestamp = get_datetime(latest_saved_timestamp)
                from_datetime = latest_saved_timestamp

            # Filter by date range, active employees, and already-imported rows.
            filtered_records = []
            inactive_count = 0
            existing_count = 0
            for record in attendance_records:
                uid = str(record.user_id)
                rec_time = record.timestamp

                if from_datetime and rec_time <= from_datetime:
                    existing_count += 1
                    continue
                if to_datetime and rec_time.date() > to_datetime.date():
                    continue
                if uid not in active_employee_map:
                    inactive_count += 1
                    continue

                existing = frappe.db.exists("ZKT Attendance Log", {
                    "machine": self.machine_name,
                    "device_user_id": uid,
                    "timestamp": rec_time
                })
                if existing:
                    existing_count += 1
                    continue

                filtered_records.append(record)

            result["total"] = len(filtered_records)
            result["skipped_existing"] = existing_count
            result["skipped_inactive"] = inactive_count

            # Save records to database
            new_count = 0
            skip_count = 0
            error_count = 0

            for record in filtered_records:
                try:
                    uid = str(record.user_id)
                    timestamp = record.timestamp
                    punch_code = record.punch
                    status_code = record.status

                    punch_type = PUNCH_TYPE_MAP.get(punch_code, "Check In")

                    # Create new log record
                    log = frappe.get_doc({
                        "doctype": "ZKT Attendance Log",
                        "machine": self.machine_name,
                        "employee": active_employee_map[uid],
                        "device_user_id": uid,
                        "timestamp": timestamp,
                        "punch_type": punch_type,
                        "raw_uid": getattr(record, "uid", 0),
                        "raw_punch": punch_code,
                        "raw_status": status_code,
                        "status": "Pending"
                    })
                    log.insert(ignore_permissions=True)

                    # Immediately try to create checkin
                    log.create_checkin()
                    
                    # Check the result status
                    if log.status == "Processed":
                        new_count += 1
                    elif log.status == "Skipped":
                        skip_count += 1
                    elif log.status == "Error":
                        error_count += 1

                except Exception as e:
                    error_count += 1
                    frappe.log_error(
                        message=f"Error saving attendance record: {str(e)}\nRecord: uid={record.user_id}, time={record.timestamp}",
                        title="ZKT Attendance Fetch Error"
                    )

            frappe.db.commit()

            # Note: clear_device functionality has been removed for data safety
            # Device logs are preserved and can be manually cleared if needed

            conn.disconnect()

            result["success"] = True
            result["new_records"] = new_count
            result["skipped"] = skip_count
            result["errors"] = error_count
            result["message"] = (
                f"Fetch complete. New: {new_count}, Existing skipped: {existing_count}, "
                f"Inactive/unmapped skipped: {inactive_count}, Other skipped: {skip_count}, Errors: {error_count}"
            )

            status = "Success" if error_count == 0 else "Partial"
            self._update_machine_status(status, new_count)

        except Exception as e:
            if conn:
                try:
                    conn.enable_device()
                    conn.disconnect()
                except Exception:
                    pass
            result["message"] = str(e)
            self._update_machine_status("Failed", 0)
            frappe.log_error(frappe.get_traceback(), f"ZKT Fetch Error - {self.machine_name}")

        return result

    def _update_machine_status(self, status, count):
        """Update machine document with fetch status"""
        try:
            frappe.db.set_value("ZKT Machine", self.machine_name, {
                "last_fetch_time": now_datetime(),
                "last_fetch_status": status,
                "total_records_fetched": (
                    frappe.db.get_value("ZKT Machine", self.machine_name, "total_records_fetched") or 0
                ) + count
            })
            frappe.db.commit()
        except Exception:
            pass

    def _get_latest_saved_timestamp(self):
        """Return newest stored ZKT log timestamp for this machine."""
        return frappe.db.get_value(
            "ZKT Attendance Log",
            {"machine": self.machine_name},
            "timestamp",
            order_by="timestamp desc"
        )

    def _get_active_employee_map(self):
        """Map active Employee device IDs to Employee names."""
        employee_meta = frappe.get_meta("Employee")
        fields = ["name"]
        has_attendance_device_id = employee_meta.has_field("attendance_device_id")
        if has_attendance_device_id:
            fields.append("attendance_device_id")

        employees = frappe.get_all(
            "Employee",
            filters={"status": "Active"},
            fields=fields
        )

        employee_map = {}
        for employee in employees:
            if has_attendance_device_id and employee.attendance_device_id:
                employee_map[str(employee.attendance_device_id)] = employee.name

        return employee_map

    def get_device_users(self):
        """Get all users enrolled on the device"""
        conn = None
        try:
            zk = self._get_zk_instance()
            conn = zk.connect()
            users = conn.get_users()
            conn.disconnect()
            return {
                "success": True,
                "users": [
                    {
                        "uid": u.uid,
                        "user_id": u.user_id,
                        "name": u.name,
                        "privilege": u.privilege
                    }
                    for u in (users or [])
                ]
            }
        except Exception as e:
            if conn:
                try:
                    conn.disconnect()
                except Exception:
                    pass
            return {"success": False, "message": str(e), "users": []}
