# Deployment Guide

This document covers how to deploy the Sata AI Testing Streamlit application. Since the current source code does not explicitly define CI/CD pipelines or containerization yet, these are foundational deployment steps.

## Requirements

The infrastructure hosting Sata must support:
- Python 3.12+ 
- Outbound HTTP access to external LLM endpoints (OpenAI or Gemini) and target APIs defined in specs.
- Web ingress to the Streamlit default port (`8501`).

## Environment Variables

In any target deployment environment, the following configuration is strictly required:
- `LLM_API_KEY`: Your model provider's secure API token.
- `LLM_CHAT_MODEL`: The chat model configuration.
- `LLM_BASE_URL`: The compatible provider endpoint.

> [!WARNING]
> Streamlit Cloud and other PaaS providers expose their own Secrets management UI. Enter the above variables into the deployment parameters instead of committing a `.env` file to your Git repository.

## Deploying to Streamlit Community Cloud (Recommended)

Streamlit offers out-of-the-box hosting directly from GitHub repositories.

1. Create a GitHub repository and push your local Sata codebase to it.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io).
3. Click "New App".
4. Authorize GitHub and select your repository, branch, and `app.py` as the main file path.
5. Expand "Advanced Settings" and paste your production environment variables.
6. Click "Deploy". The platform will automatically install dependencies from `requirements.txt`.

## Deploying via Docker (Self-Hosted)

For customized internal networks without internet egress restrictions to Streamlit Cloud, containerizing the application is ideal. 

You can add a `Dockerfile` to the root of the project:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose standard Streamlit port
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

To build and run:
```bash
docker build -t sata-ai .
docker run -p 8501:8501 \
  -e LLM_API_KEY=your_key \
  -e LLM_CHAT_MODEL=gpt-4o \
  -e LLM_BASE_URL=https://api.openai.com/v1 \
  sata-ai
```
