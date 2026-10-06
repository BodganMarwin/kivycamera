import urllib.request
import json

url = "https://api.github.com/repos/BodganMarwin/kivycamera/actions/runs"
req = urllib.request.Request(url, headers={"User-Agent": "Python"})
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        runs = data.get("workflow_runs", [])
        for r in runs[:3]:
            print(f"Run #{r['run_number']}: status={r['status']}, conclusion={r['conclusion']}, html={r['html_url']}")
except Exception as e:
    print("Error:", e)
