// ZKT Attendance - Main JS
// Adds custom buttons and interactions to ZKT Machine doctype

frappe.ui.form.on("ZKT Machine", {
    refresh: function (frm) {
        // Test Connection Button
        frm.add_custom_button(__("Test Connection"), function () {
            if (!frm.doc.ip_address) {
                frappe.msgprint(__("Please enter an IP Address first."));
                return;
            }
            if (frm.is_dirty()) {
                frappe.confirm(
                    __("You have unsaved changes. Save before testing connection?"),
                    () => frm.save().then(() => test_connection(frm)),
                    () => test_connection(frm)
                );
            } else {
                test_connection(frm);
            }
        }, __("ZKT Actions"));

        // Fetch Attendance Button
        frm.add_custom_button(__("Fetch Attendance"), function () {
            show_fetch_dialog(frm);
        }, __("ZKT Actions"));

        // View Device Users Button
        frm.add_custom_button(__("View Device Users"), function () {
            get_device_users(frm);
        }, __("ZKT Actions"));

        // Process Pending Logs Button
        frm.add_custom_button(__("Process Pending Logs"), function () {
            process_pending_logs(frm.doc.name);
        }, __("ZKT Actions"));

        // Status indicator
        if (frm.doc.last_fetch_status) {
            let color = {
                "Success": "green",
                "Failed": "red",
                "Partial": "orange"
            }[frm.doc.last_fetch_status] || "grey";

            frm.dashboard.add_indicator(
                __("Last Fetch: {0}", [frm.doc.last_fetch_status]),
                color
            );
        }

        if (frm.doc.last_fetch_time) {
            frm.dashboard.add_indicator(
                __("Fetched: {0}", [frappe.datetime.str_to_user(frm.doc.last_fetch_time)]),
                "blue"
            );
        }
    }
});


function test_connection(frm) {
    frappe.show_progress(__("Testing Connection..."), 30, 100);

    frappe.call({
        method: "zkt_attendance.api.test_machine_connection",
        args: { machine_name: frm.doc.name },
        freeze: true,
        freeze_message: __("Connecting to {0}...", [frm.doc.ip_address]),
        callback: function (r) {
            frappe.hide_progress();
            if (!r.exc && r.message) {
                let result = r.message;
                if (result.success) {
                    frappe.msgprint({
                        title: __("✅ Connection Successful"),
                        indicator: "green",
                        message: `
                            <table class="table table-bordered">
                                <tr><td><b>Status</b></td><td style="color:green">Connected</td></tr>
                                <tr><td><b>Firmware</b></td><td>${result.firmware || "N/A"}</td></tr>
                                <tr><td><b>Serial Number</b></td><td>${result.serial_number || "N/A"}</td></tr>
                                <tr><td><b>Enrolled Users</b></td><td>${result.user_count || 0}</td></tr>
                            </table>
                        `
                    });
                } else {
                    frappe.msgprint({
                        title: __("❌ Connection Failed"),
                        indicator: "red",
                        message: `<b>Error:</b> ${result.message}`
                    });
                }
            }
        }
    });
}


function show_fetch_dialog(frm) {
    let d = new frappe.ui.Dialog({
        title: __("Fetch Attendance from {0}", [frm.doc.machine_name]),
        fields: [
            {
                fieldtype: "HTML",
                options: `<p class="text-muted">Fetch attendance logs from the ZKTeco device and save them as Employee Checkins.</p>`
            },
            {
                label: __("From Date"),
                fieldname: "from_date",
                fieldtype: "Date",
                default: frappe.datetime.add_days(frappe.datetime.nowdate(), -7)
            },
            {
                label: __("To Date"),
                fieldname: "to_date",
                fieldtype: "Date",
                default: frappe.datetime.nowdate()
            },
            {
                fieldtype: "Column Break"
            },
            {
                label: __("Clear Device Logs After Fetch"),
                fieldname: "clear_device",
                fieldtype: "Check",
                default: 0,
                description: __("⚠️ Warning: This will permanently delete logs from the device!")
            }
        ],
        primary_action_label: __("Fetch Now"),
        primary_action: function (values) {
            d.hide();
            frappe.show_progress(__("Fetching Attendance..."), 50, 100, __("Please wait, connecting to device..."));

            frappe.call({
                method: "zkt_attendance.api.fetch_attendance_logs",
                args: {
                    machine_name: frm.doc.name,
                    from_date: values.from_date || "",
                    to_date: values.to_date || "",
                    clear_device: values.clear_device ? 1 : 0
                },
                freeze: true,
                freeze_message: __("Fetching logs from {0}...", [frm.doc.ip_address]),
                callback: function (r) {
                    frappe.hide_progress();
                    if (!r.exc && r.message) {
                        let res = r.message;
                        let color = res.success ? "green" : "red";
                        let icon = res.success ? "✅" : "❌";
                        frappe.msgprint({
                            title: __("{0} Fetch Complete", [icon]),
                            indicator: color,
                            message: `
                                <table class="table table-bordered">
                                    <tr><td><b>Total Found</b></td><td>${res.total || 0}</td></tr>
                                    <tr><td><b>New Records</b></td><td style="color:green">${res.new_records || 0}</td></tr>
                                    <tr><td><b>Duplicates Skipped</b></td><td>${res.skipped || 0}</td></tr>
                                    <tr><td><b>Errors</b></td><td style="color:${res.errors ? 'red' : 'green'}">${res.errors || 0}</td></tr>
                                    <tr><td><b>Message</b></td><td>${res.message}</td></tr>
                                </table>
                            `
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
                if (!res.success) {
                    frappe.msgprint({ title: __("Error"), message: res.message, indicator: "red" });
                    return;
                }

                let users = res.users || [];
                let rows = users.map(u =>
                    `<tr>
                        <td>${u.uid}</td>
                        <td>${u.user_id}</td>
                        <td>${u.name || "(No Name)"}</td>
                        <td>${u.privilege === 0 ? "User" : u.privilege === 14 ? "Admin" : "Other"}</td>
                    </tr>`
                ).join("");

                frappe.msgprint({
                    title: __("Device Users ({0})", [users.length]),
                    indicator: "blue",
                    message: `
                        <div style="max-height:400px;overflow-y:auto">
                            <table class="table table-bordered table-sm">
                                <thead>
                                    <tr>
                                        <th>UID</th>
                                        <th>User ID</th>
                                        <th>Name</th>
                                        <th>Role</th>
                                    </tr>
                                </thead>
                                <tbody>${rows || '<tr><td colspan="4">No users found</td></tr>'}</tbody>
                            </table>
                        </div>
                    `
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
            if (!r.exc && r.message) {
                let res = r.message;
                frappe.msgprint({
                    title: __("Processing Complete"),
                    indicator: "green",
                    message: res.message
                });
            }
        }
    });
}
