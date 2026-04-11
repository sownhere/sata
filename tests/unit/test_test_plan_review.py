"""Tests for deterministic Test Plan Review formatting helpers."""

from src.ui.test_plan_review import (
    build_test_plan_review_sections,
    extract_destructive_test_groups,
    filter_enabled_test_cases,
    format_test_category_label,
)


def test_format_test_category_label_humanizes_known_category():
    assert format_test_category_label("happy_path") == "Happy Path"
    assert format_test_category_label("auth_failure") == "Auth Failure"


def test_filter_enabled_test_cases_excludes_disabled_categories_only():
    generated_test_cases = [
        {
            "id": "tc-1",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "List users",
            "description": "Returns 200",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        },
        {
            "id": "tc-2",
            "endpoint_path": "/users/{id}",
            "endpoint_method": "DELETE",
            "category": "boundary",
            "priority": "P2",
            "title": "Delete user boundary case",
            "description": "Deletes one user",
            "request_overrides": {},
            "expected": {"status_code": 204},
            "is_destructive": True,
            "field_refs": ["id"],
        },
    ]

    enabled = filter_enabled_test_cases(generated_test_cases, ["boundary"])

    assert enabled == [generated_test_cases[0]]


def test_extract_destructive_test_groups_returns_empty_for_none_input():
    assert extract_destructive_test_groups(None) == []


def test_extract_destructive_test_groups_returns_empty_when_no_destructive_cases():
    test_cases = [
        {
            "id": "tc-1",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "List users",
            "description": "Returns 200",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        }
    ]
    assert extract_destructive_test_groups(test_cases) == []


def test_extract_destructive_test_groups_returns_groups_for_destructive_cases():
    test_cases = [
        {
            "id": "tc-safe",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "List users",
            "description": "Returns 200",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        },
        {
            "id": "tc-del-1",
            "endpoint_path": "/users/{id}",
            "endpoint_method": "DELETE",
            "category": "boundary",
            "priority": "P2",
            "title": "Delete user",
            "description": "Deletes one user",
            "request_overrides": {},
            "expected": {"status_code": 204},
            "is_destructive": True,
            "field_refs": ["id"],
        },
        {
            "id": "tc-del-2",
            "endpoint_path": "/users/{id}",
            "endpoint_method": "DELETE",
            "category": "boundary",
            "priority": "P3",
            "title": "Delete user not found",
            "description": "Returns 404",
            "request_overrides": {},
            "expected": {"status_code": 404},
            "is_destructive": True,
            "field_refs": ["id"],
        },
        {
            "id": "tc-put-1",
            "endpoint_path": "/users/{id}",
            "endpoint_method": "PUT",
            "category": "happy_path",
            "priority": "P1",
            "title": "Update user",
            "description": "Updates one user",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": True,
            "field_refs": ["id"],
        },
    ]

    groups = extract_destructive_test_groups(test_cases)

    assert len(groups) == 2
    # Sorted by method then path: DELETE before PUT
    delete_group = next(g for g in groups if g["endpoint_method"] == "DELETE")
    put_group = next(g for g in groups if g["endpoint_method"] == "PUT")
    assert delete_group["endpoint_path"] == "/users/{id}"
    assert delete_group["count"] == 2
    assert put_group["endpoint_path"] == "/users/{id}"
    assert put_group["count"] == 1


def test_extract_destructive_test_groups_collapses_same_endpoint_across_categories():
    test_cases = [
        {
            "id": "tc-del-a",
            "endpoint_path": "/items/{id}",
            "endpoint_method": "DELETE",
            "category": "happy_path",
            "priority": "P1",
            "title": "Delete item success",
            "description": "",
            "request_overrides": {},
            "expected": {"status_code": 204},
            "is_destructive": True,
            "field_refs": [],
        },
        {
            "id": "tc-del-b",
            "endpoint_path": "/items/{id}",
            "endpoint_method": "DELETE",
            "category": "auth_failure",
            "priority": "P2",
            "title": "Delete item unauthorized",
            "description": "",
            "request_overrides": {},
            "expected": {"status_code": 401},
            "is_destructive": True,
            "field_refs": [],
        },
    ]

    groups = extract_destructive_test_groups(test_cases)

    assert groups == [
        {"endpoint_method": "DELETE", "endpoint_path": "/items/{id}", "count": 2}
    ]


def test_build_test_plan_review_sections_groups_counts_and_marks_excluded():
    generated_test_cases = [
        {
            "id": "tc-happy-1",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P1",
            "title": "List users",
            "description": "Returns 200",
            "request_overrides": {},
            "expected": {"status_code": 200},
            "is_destructive": False,
            "field_refs": [],
        },
        {
            "id": "tc-happy-2",
            "endpoint_path": "/users",
            "endpoint_method": "GET",
            "category": "happy_path",
            "priority": "P2",
            "title": "List users with invalid filter",
            "description": "Returns 400",
            "request_overrides": {},
            "expected": {"status_code": 400},
            "is_destructive": False,
            "field_refs": ["limit"],
        },
        {
            "id": "tc-delete-1",
            "endpoint_path": "/users/{id}",
            "endpoint_method": "DELETE",
            "category": "boundary",
            "priority": "P3",
            "title": "Delete user",
            "description": "Deletes one user",
            "request_overrides": {},
            "expected": {"status_code": 204},
            "is_destructive": True,
            "field_refs": ["id"],
        },
    ]

    sections = build_test_plan_review_sections(
        generated_test_cases,
        disabled_categories=["boundary"],
    )

    assert [section["category"] for section in sections] == ["happy_path", "boundary"]

    happy_section = sections[0]
    assert happy_section["label"] == "Happy Path"
    assert happy_section["is_enabled"] is True
    assert happy_section["priority_counts"] == {"P1": 1, "P2": 1, "P3": 0}
    assert [case["status"] for case in happy_section["test_cases"]] == [
        "Enabled",
        "Enabled",
    ]

    boundary_section = sections[1]
    assert boundary_section["label"] == "Boundary"
    assert boundary_section["is_enabled"] is False
    assert boundary_section["priority_counts"] == {"P1": 0, "P2": 0, "P3": 1}
    assert boundary_section["test_cases"][0]["status"] == "Excluded"
    assert "DELETE" in boundary_section["test_cases"][0]["destructive_warning"]
    assert "/users/{id}" in boundary_section["test_cases"][0]["destructive_warning"]
