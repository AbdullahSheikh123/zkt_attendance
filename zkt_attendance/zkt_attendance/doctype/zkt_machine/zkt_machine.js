frappe.ui.form.on("ZKT Machine", {
	refresh: function (frm) {
		frm.add_custom_button(__("Test Connection"), function () {
			if (!frm.doc.ip_address) {
				frappe.msgprint(__("Please enter an IP Address first."));
				return;
			}
			if (frm.is_dirty()) {
				frappe.confirm(
					__("You have unsaved changes. Save before testing?"),
					() => frm.save().then(() => test_connection(frm)),
					() => test_connection(frm)
				);
			} else {
				test_connection(frm);
			}
		}, __("ZKT Actions"));

		frm.add_custom_button(__("Fetch Attendance"), function () {
			show_fetch_dialog(frm);
		}, __("ZKT Actions"));

		frm.add_custom_button(__("View Device Users"), function () {
			get_device_users(frm);
		}, __("ZKT Actions"));

		frm.add_custom_button(__("Process Pending Logs"), function () {
			process_pending_logs(frm.doc.name);
		}, __("ZKT Actions"));

		if (frm.doc.last_fetch_status) {
			let color = { "Success": "green", "Failed": "red", "Partial": "orange" }[frm.doc.last_fetch_status] || "grey";
			frm.dashboard.add_indicator(__("Last Fetch: {0}", [frm.doc.last_fetch_status]), color);
		}
		if (frm.doc.last_fetch_time) {
			frm.dashboard.add_indicator(__("Fetched: {0}", [frappe.datetime.str_to_user(frm.doc.last_fetch_time)]), "blue");
		}
	}
});

function test_connection(frm) {
	frappe.call({
		method: "zkt_attendance.api.test_machine_connection",
		args: { machine_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Connecting to {0}...", [frm.doc.ip_address]),
		callback: function (r) {
			if (!r.exc && r.message) {
				let res = r.message;
				frappe.msgprint({
					title: res.success ? __("✅ Connection Successful") : __("❌ Connection Failed"),
					indicator: res.success ? "green" : "red",
					message: res.success
						? `<table class="table table-bordered">
							<tr><td><b>Firmware</b></td><td>${res.firmware || "N/A"}</td></tr>
							<tr><td><b>Serial No.</b></td><td>${res.serial_number || "N/A"}</td></tr>
							<tr><td><b>Enrolled Users</b></td><td>${res.user_count || 0}</td></tr>
						   </table>`
						: `<b>Error:</b> ${res.message}`
				});
			}
		}
	});
}

function show_fetch_dialog(frm) {
	let d = new frappe.ui.Dialog({
		title: __("Fetch Attendance — {0}", [frm.doc.machine_name]),
		fields: [
			{ label: __("From Date"), fieldname: "from_date", fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.nowdate(), -7) },
			{ label: __("To Date"),   fieldname: "to_date",   fieldtype: "Date", default: frappe.datetime.nowdate() }
		],
		primary_action_label: __("Start Background Job"),
		primary_action: function (values) {
			d.hide();
			frappe.call({
				method: "zkt_attendance.api.fetch_attendance_logs",
				args: {
					machine_name: frm.doc.name,
					from_date: values.from_date || "",
					to_date: values.to_date || ""
				},
				freeze: false,
				async: true,
				callback: function (r) {
					if (!r.exc && r.message) {
						let res = r.message;
						frappe.msgprint({
							title: __("✅ Background Job Started"),
							indicator: "blue",
							message: __("Attendance fetch job has been queued. You can continue working. Check the notifications for completion status.")
						});
						frm.reload_doc();
					}
				}
			});
		}
	});
	d.show();
}

function get_device_users(frm) {
	frappe.call({
		method: "zkt_attendance.api.get_device_users",
		args: { machine_name: frm.doc.name },
		freeze: true,
		freeze_message: __("Loading device users..."),
		callback: function (r) {
			if (!r.exc && r.message) {
				let res = r.message;
				if (!res.success) { frappe.msgprint({ title: __("Error"), message: res.message, indicator: "red" }); return; }
				let rows = (res.users || []).map(u =>
					`<tr><td>${u.uid}</td><td>${u.user_id}</td><td>${u.name || "(No Name)"}</td>
					<td>${u.privilege === 0 ? "User" : u.privilege === 14 ? "Admin" : "Other"}</td></tr>`
				).join("");
				frappe.msgprint({
					title: __("Device Users ({0})", [res.users.length]),
					indicator: "blue",
					message: `<div style="max-height:400px;overflow-y:auto">
						<table class="table table-bordered table-sm">
							<thead><tr><th>UID</th><th>User ID</th><th>Name</th><th>Role</th></tr></thead>
							<tbody>${rows || "<tr><td colspan='4'>No users found</td></tr>"}</tbody>
						</table></div>`
				});
			}
		}
	});
}

function process_pending_logs(machine_name) {
	frappe.call({
		method: "zkt_attendance.api.process_pending_logs",
		args: { machine_name: machine_name },
		freeze: true,
		freeze_message: __("Processing pending logs..."),
		callback: function (r) {
			if (!r.exc && r.message) frappe.msgprint({ title: __("Done"), indicator: "green", message: r.message.message });
		}
	});
}
