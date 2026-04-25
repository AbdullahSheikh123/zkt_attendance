app_name = "zkt_attendance"
app_title = "ZKT Attendance"
app_publisher = "Your Company"
app_description = "ZKTeco Biometric Attendance Device Integration"
app_email = "admin@yourcompany.com"
app_license = "MIT"
app_version = "1.0.0"

app_icon = "octicon octicon-device-mobile"
app_color = "#2196F3"

# Included in every page
app_include_css = ["/assets/zkt_attendance/css/zkt_attendance.css"]
app_include_js = ["/assets/zkt_attendance/js/zkt_attendance.js"]

doc_events = {}

scheduler_events = {
    "cron": {
        "*/5 * * * *": [
            "zkt_attendance.utils.scheduler.auto_fetch_attendance"
        ],
    }
}

has_permission = {}
fixtures = []
