"""
OneAgent UI — Single Streamlit application.

Run with: streamlit run ui/app.py --server.port 8501

Sidebar auto-populated from module manifests.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="OneAgent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ─────────────────────────────────────────────────────────

st.sidebar.title("OneAgent")
st.sidebar.caption("Unified Personal Super-App")

page = st.sidebar.radio(
    "Navigate",
    ["Dashboard", "Chat", "FHIR Tools", "LEAP Analytics", "Research",
     "Work Ops", "Files", "Coding", "Content", "Skills", "Scheduler", "Settings"],
    index=0,
)

st.sidebar.divider()

# Quick status
try:
    from core.llm.router import get_router
    router = get_router()
    providers = router.list_available()
    available = sum(1 for p in providers if p["available"])
    st.sidebar.metric("LLM Providers", f"{available}/{len(providers)}")

    summary = router.get_daily_spend()
    st.sidebar.metric("Today's Spend", f"${summary['total_usd']:.4f}")
except Exception:
    st.sidebar.metric("LLM Providers", "N/A")
    st.sidebar.metric("Today's Spend", "$0")


# ── Pages ───────────────────────────────────────────────────────────

if page == "Dashboard":
    st.title("OneAgent Dashboard")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Modules", len(st.session_state.get("modules", [])) or "...")
    with col2:
        st.metric("Skills", len(st.session_state.get("skills", [])) or "...")
    with col3:
        st.metric("MCP Servers", "...")
    with col4:
        st.metric("Scheduled Jobs", "...")

    st.divider()

    # Module status
    st.subheader("Module Status")
    try:
        from modules import load_all_modules
        mods = load_all_modules()
        st.session_state["modules"] = mods
        for mod in mods:
            with st.expander(f"{mod['name']} — {mod.get('description', '')}", expanded=False):
                st.json(mod)
    except Exception as e:
        st.error(f"Error loading modules: {e}")

elif page == "Chat":
    st.title("Chat with OneAgent")

    task_class = st.selectbox("Task class", ["reason", "classify", "code", "healthcare", "summarize", "long_context"])

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask anything..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    import asyncio
                    from core.llm.router import get_router

                    async def _chat():
                        router = get_router()
                        return await router.complete(
                            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                            task_class=task_class,
                        )

                    response = asyncio.run(_chat())
                    st.markdown(response.content)
                    st.caption(f"{response.provider}/{response.model} | ${response.cost_usd:.4f}")
                    st.session_state.messages.append({"role": "assistant", "content": response.content})
                except Exception as e:
                    st.error(f"Error: {e}")

elif page == "FHIR Tools":
    st.title("FHIR Tools")

    tab1, tab2, tab3, tab4 = st.tabs(["Search", "Validate", "Inconsistencies", "Scopes"])

    with tab1:
        st.subheader("FHIR Resource Search")
        resource_type = st.text_input("Resource Type", "Patient")
        search_params = st.text_area("Search Params (JSON)", "{}", height=100)
        server = st.selectbox("Server", ["healthos", "public"])

        if st.button("Search"):
            try:
                from modules.fhir.manifest import fhir_search
                result = fhir_search(resource_type, search_params, server)
                if result.get("status") == 200:
                    st.json(result["data"])
                else:
                    st.error(f"Error: {result}")
            except Exception as e:
                st.error(f"Error: {e}")

    with tab2:
        st.subheader("FHIR Resource Validation")
        val_resource = st.text_input("Resource Type", "Patient", key="val_res")
        val_json = st.text_area("Resource JSON", '{}', height=200)
        if st.button("Validate"):
            try:
                from modules.fhir.manifest import fhir_validate
                result = fhir_validate(val_resource, val_json)
                st.json(result)
            except Exception as e:
                st.error(f"Error: {e}")

    with tab3:
        st.subheader("Inconsistency Detection")
        inc_resource = st.selectbox("Resource Type", ["Patient", "Encounter", "Observation"])
        inc_db = st.selectbox("Database", ["release01_fhir", "baseline11x_fhir"])
        if st.button("Find Inconsistencies"):
            try:
                from modules.fhir.manifest import find_inconsistencies
                result = find_inconsistencies(inc_resource, inc_db)
                st.json(result)
            except Exception as e:
                st.error(f"Error: {e}")

    with tab4:
        st.subheader("SMART on FHIR Scope Generation")
        if st.button("Generate Scopes"):
            try:
                from modules.fhir.manifest import generate_smart_scopes
                result = generate_smart_scopes()
                st.metric("V1 Scopes", result["v1_count"])
                st.metric("V2 Scopes", result["v2_count"])
                with st.expander("V1 Scopes"):
                    st.code("\n".join(result["v1"]))
                with st.expander("V2 Scopes"):
                    st.code("\n".join(result["v2"]))
            except Exception as e:
                st.error(f"Error: {e}")

elif page == "LEAP Analytics":
    st.title("LEAP Analytics")
    pipeline = st.selectbox("Pipeline", ["LEAP-10G", "LEAP-11X", "FHIR-10G", "FHIR-11X", "UDS+"])
    report_type = st.selectbox("Report Type", ["summary", "coverage", "status"])

    if st.button("Generate Report"):
        try:
            from modules.leap.manifest import leap_analytics
            db_map = {"LEAP-10G": "release01_fhir", "LEAP-11X": "baseline11x_fhir",
                      "FHIR-10G": "release01_fhir", "FHIR-11X": "baseline11x_fhir", "UDS+": "baseline11x_muii"}
            result = leap_analytics(report_type, db_map.get(pipeline, "release01_fhir"), pipeline)
            st.json(result)
        except Exception as e:
            st.error(f"Error: {e}")

elif page == "Research":
    st.title("Research")
    topic = st.text_input("Research Topic")
    depth = st.selectbox("Depth", ["quick", "standard", "deep"])

    if st.button("Research") and topic:
        with st.spinner("Researching..."):
            try:
                import asyncio
                from modules.research.manifest import deep_research
                result = asyncio.run(deep_research(topic, depth))
                st.markdown(result["research"])
                st.caption(f"Cost: ${result['cost']:.4f}")
            except Exception as e:
                st.error(f"Error: {e}")

elif page == "Work Ops":
    st.title("Work Operations")
    st.info("Outlook, Teams, SharePoint, DataSync tools")
    op = st.selectbox("Operation", ["Extract Emails", "Extract Teams Messages", "SharePoint Download", "DataSync Status"])

    if st.button("Run") and op == "DataSync Status":
        from modules.work_ops.manifest import datasync_status
        st.json(datasync_status())

elif page == "Files":
    st.title("File Operations")
    directory = st.text_input("Directory Path", str(Path.home()))
    op = st.selectbox("Operation", ["Analyze", "Organize", "Storage Guard"])

    if st.button("Run") and directory:
        try:
            if op == "Analyze":
                from modules.files.manifest import analyze_files
                result = analyze_files(directory, check_duplicates=True)
                st.metric("Total Files", result.get("total_files", 0))
                st.metric("Total Size", f"{result.get('total_size_mb', 0)} MB")
                if "duplicates" in result:
                    st.warning(f"Found {len(result['duplicates'])} duplicate sets")
                st.json(result)
            elif op == "Organize":
                strategy = st.radio("Strategy", ["type", "date", "size"])
                from modules.files.manifest import organize_files
                result = organize_files(directory, strategy, dry_run=True)
                st.json(result)
            elif op == "Storage Guard":
                from modules.files.manifest import guard_storage
                result = guard_storage(directory)
                st.json(result)
        except Exception as e:
            st.error(f"Error: {e}")

elif page == "Coding":
    st.title("Coding Tools")
    desc = st.text_area("Describe what to generate")
    lang = st.selectbox("Language", ["python", "javascript", "sql", "html"])

    if st.button("Generate Code") and desc:
        with st.spinner("Generating..."):
            try:
                import asyncio
                from modules.coding.manifest import generate_code
                result = asyncio.run(generate_code(desc, lang))
                st.code(result["code"], language=lang)
                st.caption(f"Model: {result['model']} | Cost: ${result['cost']:.4f}")
            except Exception as e:
                st.error(f"Error: {e}")

elif page == "Content":
    st.title("Content Generation")
    content_type = st.selectbox("Type", ["Blog Post", "Social Media", "SEO Analysis", "Documentation"])
    topic = st.text_input("Topic")

    if st.button("Generate") and topic:
        with st.spinner("Generating..."):
            try:
                import asyncio
                if content_type == "Blog Post":
                    from modules.content.manifest import generate_blog_post
                    result = asyncio.run(generate_blog_post(topic))
                elif content_type == "Social Media":
                    from modules.content.manifest import generate_social_posts
                    result = asyncio.run(generate_social_posts(topic))
                elif content_type == "SEO Analysis":
                    from modules.content.manifest import seo_analyze
                    result = asyncio.run(seo_analyze(topic))
                else:
                    from modules.content.manifest import generate_docs
                    result = asyncio.run(generate_docs(topic))

                key = next(k for k in result if k not in ("cost", "model", "topic", "platforms", "type"))
                st.markdown(result[key])
                if "cost" in result:
                    st.caption(f"Cost: ${result['cost']:.4f}")
            except Exception as e:
                st.error(f"Error: {e}")

elif page == "Skills":
    st.title("Skill Packs")
    try:
        from core.skills.registry import get_skill_registry
        registry = get_skill_registry()
        for cat in registry.list_categories():
            st.subheader(cat.title())
            for skill in registry.list_skills(category=cat):
                with st.expander(f"{skill.name} — {skill.description}"):
                    st.markdown(skill.prompt)
    except Exception as e:
        st.error(f"Error: {e}")

elif page == "Scheduler":
    st.title("Scheduled Jobs")
    try:
        from core.scheduler.scheduler import get_scheduler
        scheduler = get_scheduler()
        jobs = scheduler.list_jobs()
        if not jobs:
            st.info("No scheduled jobs configured")
        for job in jobs:
            st.write(f"**{job.name}** ({job.trigger.value}) — {job.schedule}")
            st.caption(f"Last run: {job.last_run} | Runs: {job.run_count}")
    except Exception as e:
        st.error(f"Error: {e}")

elif page == "Settings":
    st.title("Settings")

    tab1, tab2, tab3 = st.tabs(["LLM Providers", "Budget", "Self-Authored Modules"])

    with tab1:
        st.subheader("LLM Provider Status")
        try:
            from core.llm.router import get_router
            router = get_router()
            for p in router.list_available():
                status = "OK" if p["available"] else "UNAVAILABLE"
                st.write(f"**{p['provider']}** ({p['model']}) — ${p['cost_per_1k_input']:.4f}/1k input — {status}")
        except Exception as e:
            st.error(f"Error: {e}")

    with tab2:
        st.subheader("Budget Configuration")
        daily = st.number_input("Daily limit ($)", value=5.0, min_value=0.0, step=0.5)
        if st.button("Save Budget"):
            from core.llm.budget import get_budget_tracker
            tracker = get_budget_tracker()
            tracker.config.daily_limit_usd = daily
            st.success(f"Daily limit set to ${daily:.2f}")

    with tab3:
        st.subheader("Self-Authored Modules")
        try:
            from core.meta.registry import get_module_registry
            registry = get_module_registry()
            pending = registry.get_pending_review()
            if pending:
                st.warning(f"{len(pending)} modules pending review")
                for mod in pending:
                    with st.expander(f"{mod.name} — {mod.description}"):
                        st.write(f"Tests passed: {mod.tests_passed}")
                        st.code(mod.provenance.get("prompt", ""))
                        col1, col2 = st.columns(2)
                        if col1.button(f"Approve {mod.name}"):
                            registry.update_status(mod.name, "approved")
                            st.success(f"Approved {mod.name}")
                            st.rerun()
                        if col2.button(f"Reject {mod.name}"):
                            registry.update_status(mod.name, "rejected")
                            st.error(f"Rejected {mod.name}")
                            st.rerun()
            else:
                st.info("No modules pending review")
        except Exception as e:
            st.error(f"Error: {e}")
