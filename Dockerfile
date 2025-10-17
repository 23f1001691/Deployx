FROM python:3.10-slim

# Install system dependencies including git and GitHub CLI
RUN apt-get update && apt-get install -y \
    git \
    curl \
    gnupg \
    ca-certificates \            
    && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI
RUN mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update \
    && apt-get install gh -y \
    && rm -rf /var/lib/apt/lists/*
    
WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7860

ENV PORT=7860

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7860"]