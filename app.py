# file: app.py
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import boto3, uuid, json, os

REGION = os.getenv("AWS_REGION", os.getenv("REGION", "us-east-1"))
SUPERVISOR_AGENT_ID = os.getenv("SUPERVISOR_AGENT_ID", "SUPERVISOR_AGENT_ID")
SUPERVISOR_ALIAS_ID = os.getenv("SUPERVISOR_ALIAS_ID", "SUPERVISOR_ALIAS_ID")

runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)
app = Flask(__name__, static_folder=None)
CORS(app)

@app.get("/")
def serve_index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(base_dir, "index.html")

@app.post("/chat")
def chat():
    data = request.get_json()
    user_text = data.get("message", "")
    session_id = data.get("session_id") or str(uuid.uuid4())

    # Simple (non-streaming) invoke:
    resp = runtime.invoke_agent(
        agentId=SUPERVISOR_AGENT_ID,
        agentAliasId=SUPERVISOR_ALIAS_ID,
        sessionId=session_id,
        inputText=user_text,
    )
    # The response contains chunks; collect text chunks:
    output = []
    for chunk in resp.get("completion", []):
        if "chunk" in chunk and "bytes" in chunk["chunk"]:
            output.append(chunk["chunk"]["bytes"].decode("utf-8"))
    return jsonify({"session_id": session_id, "reply": "".join(output)})

@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "region": REGION,
        "supervisor_agent_id": SUPERVISOR_AGENT_ID != "SUPERVISOR_AGENT_ID",
        "supervisor_alias_id": SUPERVISOR_ALIAS_ID != "SUPERVISOR_ALIAS_ID",
    })

# Optional streaming (if you want progressive updates):
# See docs for streaming configurations & permissions.
# https://docs.aws.amazon.com/bedrock/latest/userguide/agents-invoke-agent.html

if __name__ == "__main__":
    app.run(port=5000, debug=True)
