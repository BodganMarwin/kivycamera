import urllib.request
import json

job_id = "112045516213"
url = f"https://api.github.com/repos/BodganMarwin/kivycamera/actions/jobs/{job_id}"
req = urllib.request.Request(url, headers={"User-Agent": "Python"})

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print("Job:", data.get("name"), "Conclusion:", data.get("conclusion"))
        for step in data.get("steps", []):
            print(f"Step {step['number']}: {step['name']} -> {step['conclusion']}")
except Exception as e:
    print("Error:", e)
