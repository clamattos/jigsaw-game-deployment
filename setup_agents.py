# file: setup_agents.py
import boto3, time

REGION = "us-east-1"  # change if needed
MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # example; pick any model you’re enabled for
ROLE_ARN = "arn:aws:iam::290780715325:role/BedrockAgentServiceRole"  # your IAM role

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
	"""Polls the agent until it's prepared and ready for aliasing."""
	start = time.time()
	while True:
		status = _get_status(agent_id)
		if status and status.upper() not in {"PREPARING", "NOT_PREPARED"}:
			return
		if time.time() - start > timeout_s:
			raise TimeoutError(f"Agent {agent_id} not prepared after {timeout_s}s (last status={status})")
		time.sleep(poll_s)


def create_agent_with_alias(name, instruction):
	# Create agent
	resp = agent.create_agent(
		agentName=name,
		foundationModel=MODEL_ID,
		instruction=instruction,
		agentResourceRoleArn=ROLE_ARN,
		idleSessionTTLInSeconds=600,
	)
	agent_id = resp["agent"]["agentId"]

	# Wait until created (not in CREATING)
	wait_until_created(agent_id)
	# Prepare a DRAFT version (required after changes)
	agent.prepare_agent(agentId=agent_id)
	# Wait until preparation completes
	wait_until_prepared(agent_id)
	# Create an alias pointing at the latest prepared version
	alias = agent.create_agent_alias(
		agentId=agent_id,
		agentAliasName="test",
	)
	alias_id = alias["agentAlias"]["agentAliasId"]
	return agent_id, alias_id


gustavo_inst = (
	"You are Gustavo, a senior software engineer. "
	"Expert in logic, ciphers, code-breaking. "
	"Be concise, think step-by-step, propose exact next actions."
)
maya_inst = (
	"You are Maya, a psychologist who excels at reading social cues and riddles involving people. "
	"Explain reasoning plainly; verify assumptions."
)
ivy_inst = (
	"You are Ivy, an operations hacker who is great with physical puzzles, spatial reasoning, "
	"and combining clues across sources."
)

if __name__ == "__main__":
	g_id, g_alias = create_agent_with_alias("Gustavo", gustavo_inst)
	m_id, m_alias = create_agent_with_alias("Maya", maya_inst)
	i_id, i_alias = create_agent_with_alias("Ivy", ivy_inst)
	print({"gustavo": (g_id, g_alias), "maya": (m_id, m_alias), "ivy": (i_id, i_alias)})
