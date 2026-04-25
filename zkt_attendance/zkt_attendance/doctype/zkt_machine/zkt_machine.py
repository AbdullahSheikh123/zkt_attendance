import frappe
from frappe.model.document import Document


class ZKTMachine(Document):

    def validate(self):
        self.validate_ip_address()
        self.validate_port()

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

    def test_connection(self):
        """Test connection to the ZKT device"""
        from zkt_attendance.utils.zk_connector import ZKConnector
        connector = ZKConnector(self)
        result = connector.test_connection()
        return result

    def fetch_attendance(self, from_date=None, to_date=None, clear_device=False):
        """Fetch attendance logs from device. Note: clear_device is deprecated and ignored."""
        from zkt_attendance.utils.zk_connector import ZKConnector
        connector = ZKConnector(self)
        # Always pass clear_device=False to prevent accidental deletion
        result = connector.fetch_and_save_logs(from_date=from_date, to_date=to_date, clear_device=False)
        return result
