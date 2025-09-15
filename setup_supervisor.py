# file: setup_supervisor.py
import boto3, time

REGION = "us-east-1"
MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
ROLE_ARN = "arn:aws:iam::<ACCOUNT_ID>:role/BedrockAgentServiceRole"

# Paste the returned IDs from setup_agents.py:
GUSTAVO = {"agent_id": "AGENT_ID_GUSTAVO", "alias_id": "ALIAS_ID_GUSTAVO"}
MAYA    = {"agent_id": "AGENT_ID_MAYA", "alias_id": "ALIAS_ID_MAYA"}
IVY     = {"agent_id": "AGENT_ID_IVY", "alias_id": "ALIAS_ID_IVY"}

agent = boto3.client("bedrock-agent", region_name=REGION)


def _get_status(agent_id: str) -> str:
	resp = agent.get_agent(agentId=agent_id)
	return resp.get("agent", {}).get("agentStatus") or resp.get("agent", {}).get("status") or ""


def wait_until_created(agent_id: str, timeout_s: int = 300, poll_s: int = 5):
	start = time.time()
	while True:
		status = _get_status(agent_id)
		if status.upper() != "CREATING":
			return
		if time.time() - start > timeout_s:
			raise TimeoutError(f"Agent {agent_id} still CREATING after {timeout_s}s")
		time.sleep(poll_s)


def wait_until_prepared(agent_id: str, timeout_s: int = 300, poll_s: int = 5):
	start = time.time()
	while True:
		status = _get_status(agent_id)
		if status and status.upper() not in {"PREPARING", "NOT_PREPARED"}:
			return
		if time.time() - start > timeout_s:
			raise TimeoutError(f"Agent {agent_id} not prepared after {timeout_s}s (last status={status})")
		time.sleep(poll_s)


def alias_arn(agent_id, alias_id):
	alias = agent.get_agent_alias(agentId=agent_id, agentAliasId=alias_id)
	return alias["agentAlias"]["agentAliasArn"]

# 1) Create supervisor
resp = agent.create_agent(
	agentName="JigsawSupervisor",
	foundationModel=MODEL_ID,
	agentResourceRoleArn=ROLE_ARN,
	instruction=(
		"You are the game master in a locked-room puzzle. "
		"Coordinate specialized teammates to crack codes quickly and safely. "
		"Break tasks down, delegate to the best collaborator, and synthesize a final answer."
	),
	agentCollaboration="SUPERVISOR",
)
sup_id = resp["agent"]["agentId"]

# 2) Wait for creation
wait_until_created(sup_id)

# 3) Associate collaborators
collabs = [
	("Gustavo", "Use when logic, ciphers, or code-breaking is required.", GUSTAVO),
	("Maya", "Use when riddles hinge on people or social inference.", MAYA),
	("Ivy", "Use for spatial/operational puzzles or combining many clues.", IVY),
]
for name, instruction, meta in collabs:
	agent.associate_agent_collaborator(
		agentId=sup_id,
		agentVersion="DRAFT",
		collaboratorName=name,
		collaborationInstruction=instruction,
		agentDescriptor={"aliasArn": alias_arn(meta["agent_id"], meta["alias_id"])}
		,
		relayConversationHistory="ENABLED",
	)

# 4) Prepare and alias the supervisor
agent.prepare_agent(agentId=sup_id)
wait_until_prepared(sup_id)
alias = agent.create_agent_alias(agentId=sup_id, agentAliasName="prod")
sup_alias = alias["agentAlias"]["agentAliasId"]
print({"supervisor": (sup_id, sup_alias)})
