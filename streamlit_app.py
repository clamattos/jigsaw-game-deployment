import os
import uuid
import boto3
import streamlit as st
import json
from pathlib import Path
import re

st.set_page_config(page_title="Jigsaw Room", page_icon="🧩", layout="centered")

REGION = os.getenv("AWS_REGION", os.getenv("REGION", "us-east-1"))
SUPERVISOR_AGENT_ID = os.getenv("SUPERVISOR_AGENT_ID", "")
SUPERVISOR_ALIAS_ID = os.getenv("SUPERVISOR_ALIAS_ID", "")
GUSTAVO_AGENT_ID = "6S9FJMQF7B"
GUSTAVO_ALIAS_ID = os.getenv("GUSTAVO_ALIAS_ID", "")
MAYA_AGENT_ID = "DSNQSVFD3N"
MAYA_ALIAS_ID = os.getenv("MAYA_ALIAS_ID", "")
CAROLINE_AGENT_ID = "KHOXBCC9II"
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
	oficina_text = ""
	# Prefer the specific Caroline file if present
	preferred = base / "dra_caroline" / "oficina_sem_respostas.txt"
	if preferred.exists():
		try:
			oficina_text = preferred.read_text(encoding="utf-8").strip()
		except Exception:
			pass
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

def normalize_challenge_key(title: str) -> str:
	if not title:
		return ""
	# Strip heading hashes and emoji, then keep from 'DESAFIO ...'
	clean = re.sub(r"^#+\\s+", "", title).strip()
	i = clean.upper().find("DESAFIO")
	core = clean[i:] if i != -1 else clean
	core = re.sub(r"\s+", " ", core)
	return core.strip()

# Build challenge catalog from Oficina using heading lines like '### 🎂 DESAFIO 1 — ...'
challenge_texts = {}
if oficina_text:
	lines = oficina_text.splitlines()
	current_display = None
	buf = []
	for ln in lines:
		ls = ln.strip()
		if re.match(r".*DESAFIO\\s+\\d+\\s+—\\s+.*$", ls, re.IGNORECASE):
			if current_display and buf:
				challenge_texts[current_display] = "\n".join(buf).strip()
				buf = []
			current_display = ls
		else:
			buf.append(ln)
	if current_display and buf:
		challenge_texts[current_display] = "\n".join(buf).strip()
challenge_keys = list(challenge_texts.keys())

@st.cache_data
def load_respostas(path: str = "respostas.txt"):
	try:
		text = Path(path).read_text(encoding="utf-8")
		answers = {}
		current_norm = None
		for line in text.splitlines():
			line_stripped = line.strip()
			# Headings like '### 🎂 DESAFIO 1 — ...' (robust match)
			if re.match(r".*DESAFIO\\s+\\d+\\s+—\\s+.*$", line_stripped, re.IGNORECASE):
				current_norm = normalize_challenge_key(line_stripped)
				continue
			if current_norm and line_stripped.startswith("**Resposta:**"):
				answers[current_norm] = line_stripped.split("**Resposta:**",1)[1].strip().strip("* ")
		return answers
	except Exception:
		return {}

respostas = load_respostas()

# New: parse respostas.txt into full entries (title, description, answer)
@st.cache_data
def load_respostas_entries(path: str = "respostas.txt"):
    try:
        text = Path(path).read_text(encoding="utf-8")
        entries = []
        current_title = None
        buf = []
        answer = ""
        heading_re = re.compile(r"^\s*#{2,6}\s+.*DESAFIO\s+\d+\s+[—\-–]\s+.*$", re.IGNORECASE)
        for ln in text.splitlines():
            ls = ln.strip()
            if heading_re.match(ls):
                if current_title is not None:
                    desc = "\n".join([x for x in buf if not x.strip().lower().startswith("**resposta:**")]).strip()
                    entries.append({"title": current_title, "description": desc, "answer": answer})
                    buf = []
                    answer = ""
                current_title = ls
            else:
                buf.append(ln)
                if ls.lower().startswith("**resposta:**"):
                    answer = ls.split("**Resposta:**", 1)[1].strip().strip("* ")
        if current_title is not None:
            desc = "\n".join([x for x in buf if not x.strip().lower().startswith("**resposta:**")]).strip()
            entries.append({"title": current_title, "description": desc, "answer": answer})
        return entries
    except Exception:
        return []

respostas_entries = load_respostas_entries()
respostas_map = {normalize_challenge_key(e["title"]): e for e in respostas_entries}
challenge_keys_ui = [e["title"] for e in respostas_entries]

st.title("🧩 Jigsaw Room")

# Main layout: sidebar with everything, main area with chat only
main_col, sidebar_col = st.columns([3, 1])

with sidebar_col:
	st.subheader("Configuration")
	st.text_input("AWS Region", key="cfg_region", value=REGION)
	st.markdown("**Agents**")
	st.text_input("Gustavo Agent ID", key="gustavo_agent", value=GUSTAVO_AGENT_ID)
	st.text_input("Gustavo Alias ID", key="gustavo_alias", value=GUSTAVO_ALIAS_ID)
	st.text_input("Maya Agent ID", key="maya_agent", value=MAYA_AGENT_ID)
	st.text_input("Maya Alias ID", key="maya_alias", value=MAYA_ALIAS_ID)
	st.text_input("Dra. Caroline Agent ID", key="caroline_agent", value=CAROLINE_AGENT_ID)
	st.text_input("Dra. Caroline Alias ID", key="caroline_alias", value=CAROLINE_ALIAS_ID)
	st.caption("These can also be set via environment variables.")
	
	st.divider()
	st.subheader("👥 Personagens")
	
	# Agent selection (toggle-like checkboxes)
	agents_info = {
		"gustavo": {
			"label": "Gustavo",
			"description": "Agente jurídico (Direito)",
			"specialties": "Análise legal, interpretação de normas, raciocínio lógico",
			"color": "🔧",
			"persona_key": "gustavo",
		},
		"maya": {
			"label": "Maya",
			"description": "Engenheira de Software Sênior", 
			"specialties": "Lógica, cifras, quebra de códigos, passo-a-passo",
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
				f"Agent {info['label']}", 
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
	st.subheader("🎯 Desafios")
	selected_challenge_key = st.selectbox("Desafio", ["(texto livre)"] + challenge_keys_ui)
	if selected_challenge_key != "(texto livre)":
		entry = respostas_map.get(normalize_challenge_key(selected_challenge_key))
		st.session_state.selected_challenge = {
			"title": selected_challenge_key,
			"category": "oficina",
			"difficulty": "n/a",
			"description": (entry or {}).get("description", ""),
			"answer": (entry or {}).get("answer", ""),
		}
	
	# Show challenge description in sidebar
	if "selected_challenge" in st.session_state:
		challenge = st.session_state.selected_challenge
		st.markdown("---")
		st.subheader("📄 Desafio Selecionado")
		st.markdown(f"**{challenge['title']}**")
		st.markdown(challenge.get("description", ""))
	
	# Manual answer attempt in sidebar
	st.markdown("---")
	st.subheader("🎯 Tentar Resposta")
	attempt = st.text_input("Digite sua resposta final:", key="attempt_text_sidebar", placeholder="Ex: 19790312 ou 1-3-5")
	if st.button("Verificar Resposta", type="primary", key="check_answer_sidebar"):
		if "selected_challenge" in st.session_state:
			entry = respostas_map.get(normalize_challenge_key(st.session_state.selected_challenge.get("title", "")))
			correct = (entry or {}).get("answer") if entry else None
			if not correct:
				st.warning("⚠️ Nenhum gabarito encontrado para o desafio selecionado.")
			else:
				def norm(s: str) -> str:
					return re.sub(r"\s+", "", s or "").strip().lower()
				if norm(attempt) == norm(correct):
					st.success("✅ **Resposta correta!** Parabéns!")
					st.balloons()
				else:
					st.error(f"❌ **Resposta incorreta.** A resposta correta é: `{correct}`")
		else:
			st.warning("⚠️ Selecione um desafio primeiro.")

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

# Show an info if we parsed zero challenges from respostas.txt
if not challenge_keys_ui:
    st.info("Nenhum desafio encontrado em respostas.txt. Verifique os títulos ('### DESAFIO N — ...').")

# Main chat area
with main_col:
    # Display chat messages
    for role, content in st.session_state.messages:
        with st.chat_message(role):
            st.markdown(content)

    # Character selection and chat input
    col_role, _ = st.columns([1, 3])
    with col_role:
        target = st.selectbox("Personagem", ["Gustavo", "Maya", "Dra. Caroline"], index=0)

    prompt = st.chat_input("Escreva sua pergunta / resposta…")
    if prompt:
        st.session_state.messages.append(("user", prompt))
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build final prompt: selected challenge text plus user's message
        base_text = ""
        if "selected_challenge" in st.session_state:
            base_text = st.session_state.selected_challenge.get("description", "")
        enhanced_prompt = (base_text + "\n\nPergunta do jogador: " + prompt).strip()

        # Invoke Bedrock Agent (non-streaming)
        try:
            if target == "Gustavo":
                agent_id = st.session_state.get("gustavo_agent") or GUSTAVO_AGENT_ID
                alias_id = st.session_state.get("gustavo_alias") or GUSTAVO_ALIAS_ID
            elif target == "Maya":
                agent_id = st.session_state.get("maya_agent") or MAYA_AGENT_ID
                alias_id = st.session_state.get("maya_alias") or MAYA_ALIAS_ID
            else:
                agent_id = st.session_state.get("caroline_agent") or CAROLINE_AGENT_ID
                alias_id = st.session_state.get("caroline_alias") or CAROLINE_ALIAS_ID

            if not agent_id:
                raise RuntimeError(f"Missing Agent ID for target: {target}")

            # Use agent ID directly if no alias provided
            if not alias_id:
                alias_id = "TSTALIASID"  # Default alias for agents without custom aliases

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

        # Validate against respostas.txt if a known challenge is selected
        veredito = None
        if "selected_challenge" in st.session_state:
            challenge_title = st.session_state.selected_challenge.get("title", "")
            gabarito = respostas.get(normalize_challenge_key(challenge_title))
            if gabarito:
                # normalize both strings (remove spaces/newlines/markdown)
                def norm(s: str) -> str:
                    return re.sub(r"\s+", "", s or "").strip().lower()
                if norm(reply).find(norm(gabarito)) != -1 or norm(reply) == norm(gabarito):
                    veredito = "✅ Resposta correta!"
                else:
                    veredito = f"❌ Resposta incorreta."

        final_block = reply if veredito is None else (reply + "\n\n" + veredito)
        st.session_state.messages.append(("assistant", final_block))
        with st.chat_message("assistant"):
            st.markdown(final_block)
