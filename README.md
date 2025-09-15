# Jigsaw Room - Multi-Agent Game

Minimal Flask + AWS Bedrock Agents sample with a supervisor orchestrating 3 collaborators.

## Local run (Flask)

1. Export env vars:

```bash
export AWS_REGION=us-east-1
export SUPERVISOR_AGENT_ID=ag-xxxxxxxxxxxxxxxxx
export SUPERVISOR_ALIAS_ID=xxxxxxxx
```

2. Install deps and run:

```bash
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`.

## Local run (Streamlit)

```bash
export AWS_REGION=us-east-1
export SUPERVISOR_AGENT_ID=ag-xxxxxxxxxxxxxxxxx
export SUPERVISOR_ALIAS_ID=xxxxxxxx
streamlit run streamlit_app.py
```

## Deploy: Streamlit Cloud

- Push this repo to GitHub.
- In Streamlit Cloud, create an app pointing to `streamlit_app.py`.
- Set Secrets (App settings → Secrets) with:

```
AWS_REGION="us-east-1"
SUPERVISOR_AGENT_ID="ag-..."
SUPERVISOR_ALIAS_ID="..."
AWS_ACCESS_KEY_ID="..."        # if needed
AWS_SECRET_ACCESS_KEY="..."     # if needed
AWS_SESSION_TOKEN="..."         # if using temporary creds
```

- Or attach an AWS role via OIDC in your AWS account that grants `bedrock:InvokeAgent` for your supervisor alias.

## Deploy: AWS App Runner (Flask)

1. Build and push container (ECR):

```bash
echo $ACCOUNT_ID $AWS_REGION
aws ecr create-repository --repository-name jigsaw-room || true
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
docker build -t jigsaw-room:latest .
docker tag jigsaw-room:latest $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/jigsaw-room:latest
docker push $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/jigsaw-room:latest
```

2. Create an App Runner service. Configure:
   - Port: `8080`
   - Env vars: `AWS_REGION`, `SUPERVISOR_AGENT_ID`, `SUPERVISOR_ALIAS_ID`

## Notes
- `index.html` is a minimal chat UI for the Flask backend. `streamlit_app.py` is a separate UI talking directly to Bedrock Agents.
- Ensure IAM permissions for Bedrock Agents `InvokeAgent` on the supervisor alias.
- If running on Streamlit Cloud, prefer OIDC to avoid static AWS keys.
