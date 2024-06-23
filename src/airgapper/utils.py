
import json
import subprocess

import requests


def check_docker():
    resp = subprocess.run(["docker", "--version"], capture_output=True, text=True)
    if resp.returncode:
        print(resp.stdout)
        print(resp.stderr)
        raise Exception("✖ Need to install/start docker first and run this script again.")

def pretty_print_completedprocess(resp: subprocess.CompletedProcess):
    if resp.returncode == 0:
        print(resp.stdout)
    elif resp.returncode:
        print(resp.stdout)
        print(resp.stderr)

def pretty_print_response(resp: requests.Response):
    print(f"{resp.status_code}: {resp.reason}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except:
        print(resp.text)