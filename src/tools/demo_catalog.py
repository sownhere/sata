"""Bundled demo-mode sample APIs and minimal OpenAPI fixtures."""

from __future__ import annotations

_PETSTORE_SPEC = """
openapi: 3.0.3
info:
  title: PetStore Demo
  version: "1.0"
servers:
  - url: https://petstore3.swagger.io/api/v3
paths:
  /pet/findByStatus:
    get:
      operationId: findPetsByStatus
      summary: Find pets by status
      parameters:
        - name: status
          in: query
          required: true
          schema:
            type: string
      responses:
        "200":
          description: Successful response
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
""".strip()

_REQRES_SPEC = """
openapi: 3.0.3
info:
  title: ReqRes Demo
  version: "1.0"
servers:
  - url: https://reqres.in/api
paths:
  /users:
    get:
      operationId: listUsers
      summary: List paginated users
      parameters:
        - name: page
          in: query
          required: false
          schema:
            type: integer
      responses:
        "200":
          description: Successful response
          content:
            application/json:
              schema:
                type: object
        "401":
          description: Unauthorized
""".strip()

_JSONPLACEHOLDER_SPEC = """
openapi: 3.0.3
info:
  title: JSONPlaceholder Demo
  version: "1.0"
servers:
  - url: https://jsonplaceholder.typicode.com
paths:
  /posts:
    get:
      operationId: listPosts
      summary: List posts
      responses:
        "200":
          description: Successful response
          content:
            application/json:
              schema:
                type: array
                items:
                  type: object
  /posts/{id}:
    get:
      operationId: getPost
      summary: Get a post
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        "200":
          description: Successful response
          content:
            application/json:
              schema:
                type: object
""".strip()

DEMO_SAMPLES = {
    "petstore": {
        "id": "petstore",
        "name": "PetStore",
        "base_url": "https://petstore3.swagger.io/api/v3",
        "source_url": "https://petstore3.swagger.io/api/v3/openapi.json",
        "raw_spec": _PETSTORE_SPEC,
        "notes": "Public Swagger Petstore sample API.",
    },
    "reqres": {
        "id": "reqres",
        "name": "ReqRes",
        "base_url": "https://reqres.in/api",
        "source_url": "https://reqres.in/api-docs/",
        "raw_spec": _REQRES_SPEC,
        "notes": (
            "Public sample API. Execution may require an API key depending on "
            "ReqRes environment policy."
        ),
    },
    "jsonplaceholder": {
        "id": "jsonplaceholder",
        "name": "JSONPlaceholder",
        "base_url": "https://jsonplaceholder.typicode.com",
        "source_url": "https://jsonplaceholder.typicode.com/",
        "raw_spec": _JSONPLACEHOLDER_SPEC,
        "notes": "Free fake REST API for demos and prototyping.",
    },
}


def list_demo_samples() -> list[dict]:
    """Return demo samples in stable display order."""
    return [
        DEMO_SAMPLES["petstore"],
        DEMO_SAMPLES["reqres"],
        DEMO_SAMPLES["jsonplaceholder"],
    ]


def get_demo_sample(sample_id: str) -> dict:
    """Return a single bundled sample by id."""
    key = str(sample_id or "").strip().lower()
    if key not in DEMO_SAMPLES:
        raise KeyError(f"Unknown demo sample: {sample_id}")
    return DEMO_SAMPLES[key]
