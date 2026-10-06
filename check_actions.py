import urllib.request
import json
import time

def check_latest_run():
    url = "https://api.github.com/repos/BodganMarwin/kivycamera/actions/runs?per_page=1"
    req = urllib.request.Request(url, headers={"User-Agent": "Python"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            runs = data.get("workflow_runs", [])
            if runs:
                latest = runs[0]
                run_id = latest["id"]
                status = latest["status"]
                conclusion = latest.get("conclusion")
                html_url = latest["html_url"]
                print(f"Run ID: {run_id} | Status: {status} | Conclusion: {conclusion}")
                print(f"URL: {html_url}")
                
                # Check jobs
                jobs_url = latest["jobs_url"]
                req_jobs = urllib.request.Request(jobs_url, headers={"User-Agent": "Python"})
                with urllib.request.urlopen(req_jobs) as jresp:
                    jdata = json.loads(jresp.read().decode())
                    for job in jdata.get("jobs", []):
                        print(f"  Job: {job['name']} ({job['status']}, {job.get('conclusion')})")
                        for step in job.get("steps", []):
                            print(f"    Step {step['number']}: {step['name']} -> {step['status']} ({step.get('conclusion')})")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    check_latest_run()
