from pathlib import Path

from setuptools import setup, find_packages


APP_NAME = "zkt_attendance"


def ensure_bench_app_registered():
    """Make bench get-app builds work when build runs before apps.txt sync."""
    candidates = []
    for start in (Path(__file__).resolve().parent, Path.cwd().resolve()):
        candidates.extend(start.parents)
        candidates.append(start)

    apps_txt = None
    for candidate in candidates:
        possible_apps_txt = candidate / "sites" / "apps.txt"
        possible_apps_dir = candidate / "apps"
        if possible_apps_txt.exists() and possible_apps_dir.exists():
            apps_txt = possible_apps_txt
            break

    if not apps_txt:
        return

    apps_text = apps_txt.read_text(encoding="utf-8")
    apps = apps_text.splitlines()
    if APP_NAME in apps:
        return

    separator = "" if not apps_text or apps_text.endswith("\n") else "\n"
    with apps_txt.open("a", encoding="utf-8") as f:
        f.write(f"{separator}{APP_NAME}\n")


with open("requirements.txt") as f:
    install_requires = [line.strip() for line in f if line.strip()]

ensure_bench_app_registered()

setup(
    name="zkt_attendance",
    version="1.0.0",
    description="ZKTeco Attendance Device Integration for Frappe/ERPNext",
    author="Your Company",
    author_email="admin@yourcompany.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
