from pathlib import Path

from setuptools import setup, find_packages


APP_NAME = "zkt_attendance"


def ensure_bench_app_registered():
    """Make bench get-app builds work when build runs before apps.txt sync."""
    app_root = Path(__file__).resolve().parent
    bench_root = app_root.parent.parent
    apps_txt = bench_root / "sites" / "apps.txt"

    if not apps_txt.exists():
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
    name=APP_NAME,
    version="1.0.0",
    description="ZKTeco Attendance Device Integration for Frappe/ERPNext",
    author="Your Company",
    author_email="admin@yourcompany.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
