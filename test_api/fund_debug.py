# debug_funds.py
from app.tsetmc import get_funds

data = get_funds()
funds = data.get("funds", [])

print(f"Total funds: {len(funds)}")
print("\nSample fund keys:", list(funds[0].keys()) if funds else "empty")
print("\nAll funds with زر/طلا/گوهر/عیار/کهربا/گلدیس in name:\n")

keywords = ["زر", "طلا", "گوهر", "عیار", "کهربا", "گلدیس"]
for f in funds:
    name = f.get("mfName", "")
    if any(k in name for k in keywords):
        print(f"  name={name}")
        print(f"  insCode={f.get('insCode')}")
        print(f"  all keys: {f}")
        print()