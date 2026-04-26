import frappe
from frappe.model.document import Document


@frappe.whitelist()
def create_checkin_from_log(log_name):
	log = frappe.get_doc("ZKT Attendance Log", log_name)
	success = log.create_checkin()
	return "Checkin created successfully." if success else f"Skipped: {log.error_message}"


class ZKTAttendanceLog(Document):

    def before_insert(self):
        self.resolve_employee()

    def resolve_employee(self):
        """Try to match device_user_id to an Employee"""
        if self.device_user_id and not self.employee:
            # Check Employee doctype for attendance_device_id field (ERPNext standard)
            employee = frappe.db.get_value(
                "Employee",
                {"attendance_device_id": self.device_user_id, "status": "Active"},
                "name"
            )
            if employee:
                self.employee = employee
            else:
                # Fallback: try matching employee_id directly
                employee = frappe.db.get_value(
                    "Employee",
                    {"employee_id": self.device_user_id, "status": "Active"},
                    "name"
                )
                if employee:
                    self.employee = employee
                else:
                    # Only log if no match found
                    frappe.log_error(
                        f"No employee found for device_user_id: {self.device_user_id}. Searched in attendance_device_id and employee_id.",
                        "ZKT Employee Match - Failed"
                    )

    def create_checkin(self):
        """Create Employee Checkin record from this log"""
        if not self.employee:
            self.db_set("status", "Skipped")
            self.db_set("error_message", "No matching employee found for Device User ID: " + str(self.device_user_id))
            return False

        # Map punch type to checkin log_type
        log_type_map = {
            "Check In": "IN",
            "Check Out": "OUT",
            "Overtime In": "IN",
            "Overtime Out": "OUT",
        }
        log_type = log_type_map.get(self.punch_type, "IN")

        # Check for duplicate checkin
        existing = frappe.db.exists("Employee Checkin", {
            "employee": self.employee,
            "time": self.timestamp,
            "log_type": log_type
        })

        if existing:
            self.db_set("status", "Skipped")
            self.db_set("error_message", f"Duplicate record already exists: {existing}")
            return False

        try:
            checkin = frappe.get_doc({
                "doctype": "Employee Checkin",
                "employee": self.employee,
                "time": self.timestamp,
                "log_type": log_type,
                "device_id": self.machine,
                "skip_auto_attendance": 0
            })
            checkin.insert(ignore_permissions=True)
            frappe.db.commit()
            self.db_set("status", "Processed")
            return True
        except Exception as e:
            self.db_set("status", "Error")
            self.db_set("error_message", str(e))
            frappe.log_error(frappe.get_traceback(), "ZKT Attendance Log - Create Checkin Error")
            return False
