#!/usr/bin/env python3
"""
Cleanup older GitHub deployments, keeping only the latest active one.
"""
import subprocess
import urllib.request
import json
import sys

def main():
    # Retrieve git credentials
    p = subprocess.Popen(['git', 'credential', 'fill'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    out, _ = p.communicate('protocol=https\nhost=github.com\n\n')
    token = None
    for line in out.splitlines():
        if line.startswith('password='):
            token = line.split('=', 1)[1]
            break

    if not token:
        print("Error: Could not retrieve GitHub token.")
        sys.exit(1)

    headers = {
        'Authorization': f'token {token}',
        'User-Agent': 'EDA-Deployer',
        'Accept': 'application/vnd.github+json'
    }

    # Fetch all deployments
    req = urllib.request.Request('https://api.github.com/repos/pranavsarathi/eda/deployments', headers=headers)
    with urllib.request.urlopen(req) as resp:
        deps = json.loads(resp.read().decode())

    print(f"Total deployments found: {len(deps)}")
    if len(deps) <= 1:
        print("Only 1 deployment exists. Nothing to clean up.")
        return

    # Sort descending by created_at
    deps.sort(key=lambda x: x['created_at'], reverse=True)
    latest = deps[0]
    to_delete = deps[1:]

    print(f"Keeping ONLY deployment: ID {latest['id']} (commit: {latest.get('sha', '')[:7]}, created: {latest['created_at']})")
    print(f"Removing {len(to_delete)} older deployments...")

    for d in to_delete:
        dep_id = d['id']
        sha = d.get('sha', '')[:7]
        print(f"Purging deployment {dep_id} (commit {sha})...")
        
        # 1. Mark inactive
        try:
            status_url = f"https://api.github.com/repos/pranavsarathi/eda/deployments/{dep_id}/statuses"
            payload = json.dumps({'state': 'inactive'}).encode('utf-8')
            s_req = urllib.request.Request(status_url, data=payload, headers=headers, method='POST')
            with urllib.request.urlopen(s_req) as s_resp:
                print(f"  [+] Marked inactive: HTTP {s_resp.status}")
        except urllib.error.HTTPError as e:
            print(f"  [-] Status note: HTTP {e.code}")

        # 2. Delete deployment
        try:
            del_url = f"https://api.github.com/repos/pranavsarathi/eda/deployments/{dep_id}"
            d_req = urllib.request.Request(del_url, headers=headers, method='DELETE')
            with urllib.request.urlopen(d_req) as d_resp:
                print(f"  [+] Deleted deployment: HTTP {d_resp.status}")
        except urllib.error.HTTPError as e:
            print(f"  [-] Delete error: HTTP {e.code} - {e.read().decode()}")

    print("Cleanup completed successfully.")

if __name__ == "__main__":
    main()
