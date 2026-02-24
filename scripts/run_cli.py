import argparse
import getpass
import subprocess
import sys
import os

parser = argparse.ArgumentParser(description="Run AutoAdvisor (terminal launcher)")
parser.add_argument("--config", "-c", help="Path to config .xlsx file", required=True)
parser.add_argument("--user", "-u", help="Email local-part (jdoe) or full email", required=False)
parser.add_argument("--password", "-p", help="Password (avoid on CLI); if omitted you'll be prompted", required=False)
parser.add_argument("--advisor", "-a", help="Advisor name (optional)", required=False)
parser.add_argument("--timestamp", help="Optional timestamp folder to use", required=False)
args = parser.parse_args()

user = args.user or input("Email local-part (jdoe) or full email: ").strip()
if "@" not in user:
    user = user + "@students.vsu.edu"

password = args.password
if not password:
    password = getpass.getpass("Password: ")

config_path = os.path.abspath(args.config)
project_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "project.py"))

cmd = [sys.executable, project_py, "--config", config_path, "--user", user, "--pass", password]
if args.advisor:
    cmd += ["--advisor", args.advisor]
if args.timestamp:
    cmd += ["--timestamp", args.timestamp]

print("Launching AutoAdvisor... (check terminal output)")
proc = subprocess.Popen(cmd)
proc.communicate()
