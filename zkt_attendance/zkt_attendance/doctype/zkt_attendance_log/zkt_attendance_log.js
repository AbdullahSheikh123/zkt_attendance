frappe.ui.form.on("ZKT Attendance Log", {
	refresh: function (frm) {
		if (frm.doc.status === "Pending" || frm.doc.status === "Error") {
			frm.add_custom_button(__("Create Checkin"), function () {
				frappe.call({
					method: "zkt_attendance.zkt_attendance.doctype.zkt_attendance_log.zkt_attendance_log.create_checkin_from_log",
					args: { log_name: frm.doc.name },
					callback: function (r) {
						if (!r.exc) {
							frappe.msgprint({ title: __("Done"), indicator: "green", message: r.message || "Checkin created." });
							frm.reload_doc();
						}
					}
				});
			});
		}
	}
});
