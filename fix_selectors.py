#!/usr/bin/env python3
"""
Fix all create_selector calls to use output_fn parameter.
"""

import re

# Read the file
with open('src/torematrix/core/state/selectors/common.py', 'r') as f:
    content = f.read()

# Pattern to match create_selector calls that need fixing
# This matches: create_selector(deps..., lambda_function, name=...)
pattern = r'create_selector\(\s*([^,]+(?:,\s*[^,]+)*),\s*(lambda[^,]+),\s*(name=[^)]+)\)'

def fix_create_selector(match):
    deps = match.group(1).strip()
    lambda_func = match.group(2).strip()  
    name_param = match.group(3).strip()
    
    return f'create_selector(\n    {deps},\n    output_fn={lambda_func},\n    {name_param}\n)'

# Apply the fix
fixed_content = re.sub(pattern, fix_create_selector, content, flags=re.MULTILINE | re.DOTALL)

# Write back
with open('src/torematrix/core/state/selectors/common.py', 'w') as f:
    f.write(fixed_content)

print("Fixed create_selector calls in common.py")