import os
import uuid
import boto3
import streamlit as st
import json
from pathlib import Path

REGION = os.getenv("AWS_REGION", os.getenv("REGION", "us-east-1"))
SUPERVISOR_AGENT_ID = os.getenv("SUPERVISOR_AGENT_ID", "")
SUPERVISOR_ALIAS_ID = os.getenv("SUPERVISOR_ALIAS_ID", "")
GUSTAVO_AGENT_ID = os.getenv("GUSTAVO_AGENT_ID", "")
GUSTAVO_ALIAS_ID = os.getenv("GUSTAVO_ALIAS_ID", "")
MAYA_AGENT_ID = os.getenv("MAYA_AGENT_ID", "")
MAYA_ALIAS_ID = os.getenv("MAYA_ALIAS_ID", "")
CAROLINE_AGENT_ID = os.getenv("CAROLINE_AGENT_ID", "")
CAROLINE_ALIAS_ID = os.getenv("CAROLINE_ALIAS_ID", "")

runtime = boto3.client("bedrock-agent-runtime", region_name=REGION)

# Load challenges
@st.cache_data
def load_challenges():
	try:
		with open("challenges.json", "r") as f:
			return json.load(f)["challenges"]
	except FileNotFoundError:
		return []

def _read_text_file(path: Path) -> str:
	try:
		return path.read_text(encoding="utf-8").strip()
	except Exception:
		return ""

@st.cache_data
def load_oficina_and_personas(base_dir: str = "agents_description"):
	base = Path(base_dir)
	personas = {}
\toficina_text = ""
	if not base.exists():
		return oficina_text, personas

	for persona_dir in base.iterdir():
		if not persona_dir.is_dir():
			continue
		files = {p.name: p for p in persona_dir.glob("*.txt")}
		if not oficina_text and "oficina_sem_respostas.txt" in files:
			oficina_text = _read_text_file(files["oficina_sem_respostas.txt"])
		bg = next((p for n, p in files.items() if n.startswith("background_") or n.startswith("background")), None)
		desc = next((p for n, p in files.items() if n.startswith("descricao_") or n.startswith("descricao")), None)
		tips = next((p for n, p in files.items() if n.startswith("dicas_") or n.startswith("dicas")), None)
		personas[persona_dir.name] = {
			"background": _read_text_file(bg) if bg else "",
			"descricao": _read_text_file(desc) if desc else "",
			"dicas": _read_text_file(tips) if tips else "",
		}

	return oficina_text, personas

challenges = load_challenges()
oficina_text, personas = load_oficina_and_personas()

st.set_page_config(page_title="Jigsaw Room", page_icon="🧩", layout="centered")
st.title("🧩 Jigsaw Room")

with st.sidebar:
	st.subheader("Configuration")
	st.text_input("AWS Region", key="cfg_region", value=REGION)
	st.markdown("**Supervisor Agent**")
	st.text_input("Supervisor Agent ID", key="cfg_agent", value=SUPERVISOR_AGENT_ID)
	st.text_input("Supervisor Alias ID", key="cfg_alias", value=SUPERVISOR_ALIAS_ID)
	st.markdown("**Direct Agents (optional)**")
	st.text_input("Gustavo Agent ID", key="gustavo_agent", value=GUSTAVO_AGENT_ID)
	st.text_input("Gustavo Alias ID", key="gustavo_alias", value=GUSTAVO_ALIAS_ID)
	st.text_input("Maya Agent ID", key="maya_agent", value=MAYA_AGENT_ID)
	st.text_input("Maya Alias ID", key="maya_alias", value=MAYA_ALIAS_ID)
	st.text_input("Dra. Caroline Agent ID", key="caroline_agent", value=CAROLINE_AGENT_ID)
	st.text_input("Dra. Caroline Alias ID", key="caroline_alias", value=CAROLINE_ALIAS_ID)
	st.caption("These can also be set via environment variables.")
	
	st.divider()
	st.subheader("👥 Agents")
	
	# Agent selection
	agents_info = {
		"gustavo": {
			"label": "Gustavo",
			"description": "Senior Software Engineer",
			"specialties": "Logic, ciphers, code-breaking, step-by-step analysis",
			"color": "🔧",
			"persona_key": "gustavo",
		},
		"maya": {
			"label": "Maya",
			"description": "Psychologist", 
			"specialties": "Social cues, people puzzles, behavioral analysis",
			"color": "🧠",
			"persona_key": "maya",
		},
		"dra_caroline": {
			"label": "Dra. Caroline",
			"description": "Química/Docente",
			"specialties": "Laboratorial, método científico, ensino",
			"color": "🧪",
			"persona_key": "dra_caroline",
		}
	}
	
	# Initialize selected agents if not set
	if "selected_agents" not in st.session_state:
		st.session_state.selected_agents = [a["label"] for a in agents_info.values()]
	
	# Agent checkboxes
	for key, info in agents_info.items():
		col1, col2 = st.columns([1, 4])
		with col1:
			selected = st.checkbox(
				"", 
				value=info["label"] in st.session_state.selected_agents,
				key=f"agent_{key}",
				label_visibility="collapsed"
			)
		with col2:
			if selected and info["label"] not in st.session_state.selected_agents:
				st.session_state.selected_agents.append(info["label"])
			elif not selected and info["label"] in st.session_state.selected_agents:
				st.session_state.selected_agents.remove(info["label"])
			st.write(f"{info['color']} **{info['label']}**")
			st.caption(f"{info['description']} - {info['specialties']}")
			persona_data = personas.get(info.get("persona_key", ""), {})
			if persona_data:
				with st.popover("Persona details"):
					if persona_data.get("descricao"):
						st.markdown(f"**Descrição:** {persona_data['descricao']}")
					if persona_data.get("background"):
						st.markdown(f"**Background:** {persona_data['background']}")
					if persona_data.get("dicas"):
						st.markdown(f"**Dicas:** {persona_data['dicas']}")
	
	if not st.session_state.selected_agents:
		st.warning("⚠️ Select at least one agent!")
	
	st.divider()
	st.subheader("🎯 Challenge: Oficina")
	if oficina_text:
		with st.expander("View challenge (oficina_sem_respostas)", expanded=False):
			st.markdown(oficina_text)
			if st.button("Load Oficina as prompt"):
				st.session_state.selected_challenge = {
					"title": "Oficina",
					"category": "oficina",
					"difficulty": "n/a",
					"description": oficina_text,
				}
				st.rerun()
	else:
		st.caption("No oficina file found under agents_description/*/oficina_sem_respostas.txt")

	st.divider()
	st.subheader("📚 Extra Challenges (optional)")
	if challenges:
		categories = ["All"] + list(set(c["category"] for c in challenges))
		difficulties = ["All"] + list(set(c["difficulty"] for c in challenges))
		selected_category = st.selectbox("Category", categories)
		selected_difficulty = st.selectbox("Difficulty", difficulties)
		filtered_challenges = challenges
		if selected_category != "All":
			filtered_challenges = [c for c in filtered_challenges if c["category"] == selected_category]
		if selected_difficulty != "All":
			filtered_challenges = [c for c in filtered_challenges if c["difficulty"] == selected_difficulty]
		challenge_options = {f"{c['title']} ({c['difficulty']})": c for c in filtered_challenges}
		selected_challenge_name = st.selectbox("Select Challenge", ["Custom"] + list(challenge_options.keys()))
		if selected_challenge_name != "Custom" and selected_challenge_name in challenge_options:
			selected_challenge = challenge_options[selected_challenge_name]
			st.write(f"**{selected_challenge['title']}**")
			st.write(f"*{selected_challenge['category']} - {selected_challenge['difficulty']}*")
			st.write(selected_challenge['description'])
			if st.button("Load This Challenge"):
				st.session_state.selected_challenge = selected_challenge
				st.rerun()
	else:
		st.caption("No challenges loaded")

if "session_id" not in st.session_state:
	st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
	st.session_state.messages = []  # list of (role, content)

# Show selected challenge info
if "selected_challenge" in st.session_state:
	challenge = st.session_state.selected_challenge
	with st.expander(f"🎯 Current Challenge: {challenge['title']}", expanded=True):
		st.write(f"**Category:** {challenge['category']} | **Difficulty:** {challenge['difficulty']}")
		st.write(f"**Description:** {challenge['description']}")
		if st.button("Clear Challenge"):
			del st.session_state.selected_challenge
			st.rerun()

for role, content in st.session_state.messages:
	with st.chat_message(role):
		st.markdown(content)

# Auto-fill prompt if challenge is selected
default_prompt = ""
if "selected_challenge" in st.session_state:
	default_prompt = st.session_state.selected_challenge['description']

col_role, col_placeholder = st.columns([1, 3])
with col_role:
	target = st.selectbox("Target", ["Supervisor", "Gustavo", "Maya", "Dra. Caroline"], index=0)
prompt = st.chat_input("Describe the puzzle…", value=default_prompt)
if prompt:
	st.session_state.messages.append(("user", prompt))
	with st.chat_message("user"):
		st.markdown(prompt)

	# Build dynamic instruction based on selected agents (context for supervisor)
	selected_agents = st.session_state.get("selected_agents", [])
	agent_context = ""
	if target == "Supervisor" and selected_agents:
		agent_context = f"\n\nAvailable team members: {', '.join(selected_agents)}. Collaborate with them as needed."

	enhanced_prompt = prompt + agent_context

	# Invoke Bedrock Agent (non-streaming)
	try:
		if target == "Supervisor":
			agent_id = st.session_state.get("cfg_agent") or SUPERVISOR_AGENT_ID
			alias_id = st.session_state.get("cfg_alias") or SUPERVISOR_ALIAS_ID
		elif target == "Gustavo":
			agent_id = st.session_state.get("gustavo_agent") or GUSTAVO_AGENT_ID
			alias_id = st.session_state.get("gustavo_alias") or GUSTAVO_ALIAS_ID
		elif target == "Maya":
			agent_id = st.session_state.get("maya_agent") or MAYA_AGENT_ID
			alias_id = st.session_state.get("maya_alias") or MAYA_ALIAS_ID
		else:
			agent_id = st.session_state.get("caroline_agent") or CAROLINE_AGENT_ID
			alias_id = st.session_state.get("caroline_alias") or CAROLINE_ALIAS_ID

		if not agent_id or not alias_id:
			raise RuntimeError(f"Missing Agent ID/Alias for target: {target}")

		resp = runtime.invoke_agent(
			agentId=agent_id,
			agentAliasId=alias_id,
			sessionId=st.session_state.session_id,
			inputText=enhanced_prompt,
		)
		chunks = []
		for chunk in resp.get("completion", []):
			if "chunk" in chunk and "bytes" in chunk["chunk"]:
				chunks.append(chunk["chunk"]["bytes"].decode("utf-8"))
		reply = "".join(chunks) if chunks else "(no reply)"
	except Exception as e:
		reply = f"Error: {e}"

	st.session_state.messages.append(("assistant", reply))
	with st.chat_message("assistant"):
		st.markdown(reply)

st.markdown("---")
st.caption("Tip: Select which agents to include in the sidebar. Configure your supervisor agent and alias there too. Your session is preserved until refresh.")
