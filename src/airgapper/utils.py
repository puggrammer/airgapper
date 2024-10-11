
import os
import json
import subprocess
import getpass
from time import sleep

import requests


def check_docker():
    resp = subprocess.run(["docker", "--version"], capture_output=True, text=True, check=False)
    if resp.returncode:
        print(resp.stdout)
        print(resp.stderr)
        raise AssertionError("✖ Need to install/start docker first and run this script again.")

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
    except Exception:
        print(resp.text)

def run_command(command, **kwargs):
    """Run command while printing the live output"""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **kwargs
    )
    stdout = []
    while process.stdout:
        line = process.stdout.readline()
        stdout.append(str(line))
        if not line and process.poll() is not None:
            break
        print(line, end='')
    stdout = ''.join(stdout)
    return process

def run_command_with_stdout(command, **kwargs):
    """Run command while printing the live output
    Keep a copy of stdout and returns it 
    """
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        **kwargs
    )
    stdout = []
    while process.stdout:
        line = process.stdout.readline()
        stdout.append(str(line))
        if not line and process.poll() is not None:
            break
        print(line, end='')
    stdout = ''.join(stdout)
    return process, stdout

#############################################
# Test Helpers
#############################################

# def nexus_api_get_file(
#         nexus_url,
#         nexus_repo,
#         nexus_user,
#         nexus_pass,
#         **kwargs):
#     for _ in range(3):
#         resp = requests.get(
#             f"http://{nexus_url}/service/rest/v1/search",
#             params={
#                 "repository": nexus_repo,
#                 **kwargs
#                 },
#             auth=(nexus_user, nexus_pass)
#         )
#         if resp.status_code == 200:
#             break
#         print("Sleeping for 5s for nexus update..")
#         sleep(5)
#     pretty_print_response(resp)
#     assert resp.status_code == 200
#     return resp