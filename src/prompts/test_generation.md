You are generating API test cases for a single confirmed endpoint.

Return valid JSON only.

Hard requirements:
- Output either:
  - `{ "test_cases": [ ... ] }`, or
  - `[ ... ]` (array of cases).
- Do not include markdown fences.
- Use only these categories:
  - `happy_path`
  - `missing_data`
  - `invalid_format`
  - `wrong_type`
  - `auth_failure`
  - `boundary`
  - `duplicate`
  - `method_not_allowed`
- Use only these priorities: `P1`, `P2`, `P3`.
- Keep endpoint references exact and explicit:
  - `endpoint_path`
  - `endpoint_method`
- Include concise, developer-readable `title` and `description`.
- Prefer deterministic, practical cases over creative speculation.
- Never include secrets, tokens, or credentials in output.

Recommended per-case shape:
```json
{
  "id": "tc-get-users-happy-path-1",
  "endpoint_path": "/users",
  "endpoint_method": "GET",
  "category": "happy_path",
  "priority": "P1",
  "title": "GET /users returns success payload",
  "description": "Valid request returns expected status and schema.",
  "request_overrides": {},
  "expected": { "status_code": 200 },
  "is_destructive": false,
  "field_refs": []
}
```
