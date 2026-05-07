import frappe
from frappe.model.document import Document


class ZKTMachine(Document):

    def validate(self):
        self.validate_ip_address()
        self.validate_port()
        self.validate_log_retention()

    def validate_ip_address(self):
        import re
        ip_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(ip_pattern, self.ip_address):
            frappe.throw(f"Invalid IP Address: {self.ip_address}")
        parts = self.ip_address.split(".")
        for part in parts:
            if int(part) > 255:
                frappe.throw(f"Invalid IP Address: {self.ip_address}")

    def validate_port(self):
        if not (1 <= self.port <= 65535):
            frappe.throw("Port must be between 1 and 65535")

    def validate_log_retention(self):
        if self.zkt_log_retention_days and self.zkt_log_retention_days < 0:
            frappe.throw("Keep ZKT Logs For Days must be 0 or greater")
        if (
            self.zkt_log_retention_days
            and self.fetch_last_days
            and self.zkt_log_retention_days <= self.fetch_last_days
        ):
            frappe.throw("Keep ZKT Logs For Days must be greater than Fetch Last N Days")

    def test_connection(self):
        """Test connection to the ZKT device"""
        from zkt_attendance.utils.zk_connector import ZKConnector
        connector = ZKConnector(self)
        result = connector.test_connection()
        return result

    def fetch_attendance(self, from_date=None, to_date=None):
        """Fetch attendance logs from device."""
        from zkt_attendance.utils.zk_connector import ZKConnector
        connector = ZKConnector(self)
        result = connector.fetch_and_save_logs(from_date=from_date, to_date=to_date)
        return result
