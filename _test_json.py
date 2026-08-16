import json, sys
sys.path.insert(0, '.')
from core.llm_client import LLMClient

with open('outputs/_debug/llm_raw_20260815_003515.txt', 'r', encoding='utf-8') as f:
    raw = f.read()

result = LLMClient._extract_json(raw)
print(type(result))
if isinstance(result, dict):
    print(f"frame: {result.get('frame')}")
    print(f"duration: {result.get('duration')}")
    print(f"description: {result.get('description')}")
    print(f"keys: {list(result.keys())}")
    print("OK!")
else:
    print(f"unexpected type: {type(result)}")
