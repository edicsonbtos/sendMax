import os
import re

base_path = r"C:\Users\edics\OneDrive\Escritorio\sendmax-bot\operator-web\src"

def process_file(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replacements for imports
    content = re.sub(r'import\s+\{\s*apiGet\s*,\s*apiPost\s*\}\s+from\s+["\']@/lib/api["\'];?', 'import api from "@/lib/api";', content)
    content = re.sub(r'import\s+\{\s*apiGet\s*\}\s+from\s+["\']@/lib/api["\'];?', 'import api from "@/lib/api";', content)
    content = re.sub(r'import\s+\{\s*apiPost\s*\}\s+from\s+["\']@/lib/api["\'];?', 'import api from "@/lib/api";', content)

    # Replacements for calls - apiGet and apiPost. Note fetch returns res.json() which is a promise of data. 
    # Axios returns { data: ... }. We must fix that too! This is crucial!
    # Let me check if they use `await apiGet(...)`
    # Replace `await apiGet(` with `(await api.get(`. WAIT, if they expect `data`, axios returns `{ data }`. So it's `(await api.get(...)).data`
    # The original apiGet implementation did `return res.json()`.
    
    # Wait, in the prompt, the user said: "Los componentes deben usar directamente api.get() y api.post()."
    # To be safe, let's just do `(await api.get(...)).data` 
    content = re.sub(r'apiGet\(', '(await api.get(', content)
    # The above is hard to regex safely for all cases if they don't use await inline. Let's just do:
    # apiGet(url) -> await api.get(url).then(res => res.data)
    # But wait, what if it's already awaited? `await apiGet(url)` -> `await api.get(url).then(res => res.data)` is invalid syntax (await await).
    
    # Let's write back
    # Actually wait, I will write the replacement manually using python replace to be explicit.
    # We will do: content.replace("apiGet(", "(await api.get("). Wait, no.
    pass

for root, dirs, files in os.walk(base_path):
    for f in files:
        if f.endswith(".tsx") or f.endswith(".ts"):
            file_path = os.path.join(root, f)
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                
            orig_content = content
            content = re.sub(r'import\s+\{\s*apiGet\s*,\s*apiPost\s*\}\s+from\s+["\']@/lib/api["\'];?', 'import api from "@/lib/api";', content)
            content = re.sub(r'import\s+\{\s*apiGet\s*\}\s+from\s+["\']@/lib/api["\'];?', 'import api from "@/lib/api";', content)
            content = re.sub(r'import\s+\{\s*apiPost\s*\}\s+from\s+["\']@/lib/api["\'];?', 'import api from "@/lib/api";', content)

            # Fix `await apiGet(...)` to `(await api.get(...)).data` natively.
            content = re.sub(r'await\s+apiGet\(([^)]+)\)', r'(await api.get(\1)).data', content)
            content = re.sub(r'await\s+apiPost\(([^)]+)\)', r'(await api.post(\1)).data', content)
            
            # Non-awaited
            content = re.sub(r'apiGet\(([^)]+)\)', r'api.get(\1).then(res => res.data)', content)
            content = re.sub(r'apiPost\(([^)]+)\)', r'api.post(\1).then(res => res.data)', content)

            if orig_content != content:
                print("Replacing in", file_path)
                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(content)
