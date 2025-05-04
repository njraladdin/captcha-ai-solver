from seleniumbase import SB
from concurrent.futures import ProcessPoolExecutor # Use ProcessPoolExecutor
import time
import os

tasks_to_run = [
    {"id": 1, "url": "https://gitlab.com/users/sign_in"},
    {"id": 2, "url": "https://github.com/login"},
    {"id": 3, "url": "https://google.com/ncr"},
    # Add more tasks
]

MAX_CONCURRENT_BROWSERS = 3

def run_cdp_task(task_info):
    task_id = task_info['id']
    url_to_open = task_info['url']
    print(f"[Task {task_id}] Starting process {os.getpid()}...")
    result = f"Task {task_id} FAILED"
    try:
        # Each process gets its own SB instance
        # Headless is highly recommended for concurrency
        with SB(uc=True, headless=False, pls="none") as sb:
            print(f"[Task {task_id} / Process {os.getpid()}] Activating CDP for: {url_to_open}")
            sb.activate_cdp_mode(url_to_open)
            print(f"[Task {task_id} / Process {os.getpid()}] Page title: {sb.cdp.get_title()}")
            # Perform other CDP actions
            sb.cdp.sleep(2) # Example action
            sb.cdp.highlight("body")
            result = f"Task {task_id} completed: {sb.cdp.get_title()}"
        print(f"[Task {task_id} / Process {os.getpid()}] Finished.")
        return result
    except Exception as e:
        print(f"[Task {task_id} / Process {os.getpid()}] *** FAILED ***: {e}")
        # Optionally save screenshots/logs here if needed, though harder across processes
        return f"Task {task_id} failed: {e}"

# --- Main execution ---
if __name__ == "__main__": # Necessary for ProcessPoolExecutor on some OSes
    start_time = time.time()
    results = []
    with ProcessPoolExecutor(max_workers=MAX_CONCURRENT_BROWSERS) as executor:
        print(f"\nSubmitting {len(tasks_to_run)} tasks to {MAX_CONCURRENT_BROWSERS} processes...")
        # Submit tasks
        futures = [executor.submit(run_cdp_task, task) for task in tasks_to_run]
        # Collect results as they complete
        for future in futures:
            results.append(future.result())

    print("\n--- All tasks completed ---")
    print("Results:")
    for res in results:
        print(f"- {res}")

    end_time = time.time()
    print(f"\nTotal execution time: {end_time - start_time:.2f} seconds")