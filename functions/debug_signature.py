
import inspect
from tools import add_task, get_manifesto

print("Checking function signatures...")

sig_add = inspect.signature(add_task)
print(f"add_task signature: {sig_add}")

sig_get = inspect.signature(get_manifesto)
print(f"get_manifesto signature: {sig_get}")

# Check if the parameters are what we expect
if "description" not in sig_add.parameters:
    print("FAILURE: 'description' parameter missing from add_task signature!")
else:
    print("SUCCESS: 'description' parameter found.")
