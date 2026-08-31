"""
OneAgent Local — Standalone offline version.

Works with Ollama only. No cloud API keys required.
Run: streamlit run app.py --server.port 8502
"""

import sys
import os
import json
import logging
from pathlib import Path

# Add parent to path so we can import core and modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="OneAgent Local",
    page_icon="🏠",
    layout="wide",
)

# ── Ollama Client ───────────────────────────────────────────────────

def ollama_available():
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def ollama_models():
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=3)
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def ollama_chat(messages, model="llama3.1:8b"):
    try:
        from openai import OpenAI
        client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
        response = client.chat.completions.create(
            model=model, messages=messages, temperature=0.7, max_tokens=4096,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"


# ── Sidebar ─────────────────────────────────────────────────────────

st.sidebar.title("OneAgent Local")
st.sidebar.caption("Offline Edition")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Chat", "FHIR Tools", "Database", "Files", "Coding", "Settings"],
    index=0,
)

# Ollama status
if ollama_available():
    st.sidebar.success("Ollama Connected")
    models = ollama_models()
    selected_model = st.sidebar.selectbox("Model", models) if models else "llama3.1:8b"
else:
    st.sidebar.error("Ollama Not Running")
    st.sidebar.info("Start Ollama: `ollama serve`")
    selected_model = "llama3.1:8b"


# ── Pages ───────────────────────────────────────────────────────────

if page == "Dashboard":
    st.title("OneAgent Local Dashboard")
    st.info("Offline mode — using Ollama for all AI operations")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Ollama", "Connected" if ollama_available() else "Offline")
    with col2:
        st.metric("Models", len(ollama_models()))
    with col3:
        st.metric("Cost", "$0.00 (local)")

    st.divider()
    st.subheader("Available Modules")
    for mod in ["FHIR Tools", "Database", "Files", "Coding", "LEAP"]:
        st.write(f"- {mod}")

elif page == "Chat":
    st.title("Chat (Local)")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask anything (local)..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner(f"Thinking ({selected_model})..."):
                response = ollama_chat(
                    [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                    model=selected_model,
                )
                st.markdown(response)
                st.caption(f"Model: {selected_model} | Cost: $0.00")
                st.session_state.messages.append({"role": "assistant", "content": response})

elif page == "FHIR Tools":
    st.title("FHIR Tools (Local)")

    tab1, tab2, tab3 = st.tabs(["Search", "Validate", "Ask FHIR Expert"])

    with tab1:
        resource_type = st.text_input("Resource Type", "Patient")
        server = st.selectbox("Server", ["healthos", "public"])
        if st.button("Search"):
            try:
                from modules.fhir.manifest import fhir_search
                result = fhir_search(resource_type, "{}", server)
                st.json(result)
            except Exception as e:
                st.error(f"Error: {e}")

    with tab2:
        val_type = st.text_input("Resource Type", "Patient", key="vtype")
        val_json = st.text_area("Resource JSON", "{}", height=200)
        if st.button("Validate"):
            try:
                from modules.fhir.manifest import fhir_validate
                result = fhir_validate(val_type, val_json)
                st.json(result)
            except Exception as e:
                st.error(f"Error: {e}")

    with tab3:
        fhir_q = st.text_input("Ask a FHIR question")
        if st.button("Ask") and fhir_q:
            with st.spinner("Thinking..."):
                response = ollama_chat([
                    {"role": "system", "content": "You are an HL7 FHIR R4 expert. Answer accurately with spec references."},
                    {"role": "user", "content": fhir_q},
                ], model=selected_model)
                st.markdown(response)

elif page == "Database":
    st.title("Database Operations")

    db_key = st.selectbox("Environment", ["release01_fhir", "release01_muii", "baseline11x_muii", "baseline11x_fhir"])
    operation = st.selectbox("Operation", ["List Tables", "Get Schema", "Run Query", "Check RecordQueue"])

    if operation == "List Tables" and st.button("Execute"):
        try:
            from config.databases import get_db_manager
            db = get_db_manager()
            tables = db.get_tables(db_key)
            st.write(f"Found {len(tables)} tables")
            st.dataframe({"Table": tables})
        except Exception as e:
            st.error(f"Error: {e}")

    elif operation == "Run Query":
        query = st.text_area("SQL Query", "SELECT TOP 10 * FROM FHIR_RecordQueue")
        if st.button("Execute"):
            try:
                from config.databases import get_db_manager
                db = get_db_manager()
                results = db.execute_query(query, db_key=db_key)
                st.dataframe(results)
            except Exception as e:
                st.error(f"Error: {e}")

    elif operation == "Check RecordQueue":
        res_type = st.text_input("Resource Type (optional)")
        if st.button("Check"):
            try:
                from config.databases import get_db_manager
                db = get_db_manager()
                results = db.check_record_queue(resource_type=res_type or None, db_key=db_key)
                st.dataframe(results)
            except Exception as e:
                st.error(f"Error: {e}")

elif page == "Files":
    st.title("File Operations")
    directory = st.text_input("Directory Path", str(Path.home()))
    op = st.selectbox("Operation", ["Analyze", "Organize (dry run)"])

    if st.button("Run") and directory:
        try:
            if op == "Analyze":
                from modules.files.manifest import analyze_files
                result = analyze_files(directory, check_duplicates=True)
                st.metric("Files", result.get("total_files", 0))
                st.metric("Size", f"{result.get('total_size_mb', 0)} MB")
                st.json(result)
            else:
                from modules.files.manifest import organize_files
                result = organize_files(directory, "type", dry_run=True)
                st.json(result)
        except Exception as e:
            st.error(f"Error: {e}")

elif page == "Coding":
    st.title("Coding (Local)")

    desc = st.text_area("Describe what to generate")
    lang = st.selectbox("Language", ["python", "javascript", "sql", "html"])

    if st.button("Generate") and desc:
        with st.spinner(f"Generating ({selected_model})..."):
            prompt = f"Generate {lang} code for:\n{desc}\n\nOutput ONLY the code, no markdown fences."
            code = ollama_chat([{"role": "user", "content": prompt}], model=selected_model)
            if code.startswith("```"):
                lines = code.split("\n")
                code = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            st.code(code, language=lang)

elif page == "Settings":
    st.title("Settings")
    st.info("OneAgent Local uses Ollama only — no API keys needed.")

    st.subheader("Ollama Status")
    if ollama_available():
        st.success("Connected")
        for m in ollama_models():
            st.write(f"- {m}")
    else:
        st.error("Not running. Start with: `ollama serve`")

    st.subheader("Model Selection")
    st.write(f"Active model: {selected_model}")
    st.write("Change model in the sidebar dropdown.")

    st.subheader("Configuration")
    ollama_host = st.text_input("Ollama Host", os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    if st.button("Save"):
        os.environ["OLLAMA_HOST"] = ollama_host
        st.success("Saved (session only)")
