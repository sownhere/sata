# Sata

**AI agent for automated API testing and test-result analysis.**

Sata ingests API documentation or user-provided input, plans and runs API tests, compares responses to expectations, surfaces common API defects, and presents results in a clear dashboard—so teams spend less time on repetitive manual checks and get faster feedback when something breaks.

---

## Agent

| | |
| --- | --- |
| **Name (VN)** | AI Agent tự động kiểm thử API & phân tích kết quả test |
| **Role** | End-to-end assistant: from spec → test cases → execution → report |

---

## Features

### Specification & test design

- Parses API docs or free-form user input to infer **endpoints**, **HTTP methods**, **parameters**, **request bodies**, and **critical test conditions**.
- **Generates test suites** automatically, including:
  - Happy paths (valid requests)
  - Missing or incomplete data
  - Invalid formats and wrong data types
  - Authentication / authorization failures
  - Boundary and edge cases

### Execution & assertion

- **Sends HTTP requests** for each case and evaluates responses against:
  - **Status codes**
  - **Response shape** (schema / structure)
  - **Payload content** and **expected business rules**

### Analysis & defect detection

- Highlights typical API problems, for example:
  - Validation that is too loose or inconsistent
  - Responses that do not match the documented structure
  - Poor or inconsistent exception handling
  - Error messages that vary unpredictably across similar failures

### Reporting

- Aggregates run results into an **interactive UI** (e.g. **Streamlit** or **Gradio**) so you can see **pass/fail** per case, **logs**, and **likely root causes** at a glance.

### Outcomes

- Cuts down **manual regression** effort
- Improves **test coverage** for APIs
- Helps **developers and testers debug** failures faster

---

## Mô tả tính năng (tiếng Việt)

- Tự động phân tích tài liệu API hoặc thông tin đầu vào của người dùng để xác định endpoint, method, tham số, request body và các điều kiện kiểm thử quan trọng.
- Tự động sinh bộ test case cho API, bao gồm cả trường hợp hợp lệ, thiếu dữ liệu, sai định dạng, sai kiểu dữ liệu, lỗi xác thực và các trường hợp biên.
- Tự động gửi request kiểm thử và đối chiếu kết quả trả về theo status code, cấu trúc dữ liệu, nội dung response và logic nghiệp vụ mong đợi.
- Tự động phát hiện các lỗi phổ biến của API như validate chưa chặt, response sai cấu trúc, xử lý exception chưa đúng hoặc thông báo lỗi chưa nhất quán.
- Tổng hợp kết quả thành báo cáo trực quan trên giao diện Streamlit/Gradio, giúp người dùng dễ theo dõi các test case pass/fail, log lỗi và nguyên nhân tiềm năng.
- Hỗ trợ rút ngắn thời gian kiểm thử thủ công, nâng cao độ bao phủ test và hỗ trợ developer/tester debug nhanh hơn.

---

## Repository

Git workflow, branches, commits, and PR rules for this project are documented in [`GIT_CONVENTION.md`](./GIT_CONVENTION.md).

---

## Status

This repository is under active definition; implementation details and setup instructions will be added as the stack and layout stabilize.
