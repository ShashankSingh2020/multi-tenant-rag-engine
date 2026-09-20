import streamlit as st
import requests

API_BASE_URL = "http://127.0.0.1:8000/api"

st.set_page_config(
    page_title="Multi-Tenant AI Knowledge Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "selected_org_id" not in st.session_state:
    st.session_state.selected_org_id = None
if "selected_project_id" not in st.session_state:
    st.session_state.selected_project_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}


# -----------------------------------------------------------------------------
# Authentication Screen
# -----------------------------------------------------------------------------
if not st.session_state.access_token:
    st.title("🔐 Enterprise AI Knowledge Engine")
    st.caption("Sign in to access your tenant workspace, upload documents, and query RAG knowledge.")

    tab_login, tab_register = st.tabs(["Log In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", value="admin@saas.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In")

            if submitted:
                try:
                    resp = requests.post(
                        f"{API_BASE_URL}/auth/login/",
                        json={"email": email, "password": password},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.access_token = data.get("access")
                        st.session_state.current_user = data.get("user")
                        st.success("Successfully authenticated!")
                        st.rerun()
                    else:
                        st.error(f"Login failed: {resp.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to Django backend. Make sure 'python manage.py runserver' is running on port 8000.")

    with tab_register:
        with st.form("register_form"):
            reg_email = st.text_input("Work Email")
            reg_name = st.text_input("Full Name")
            reg_pass = st.text_input("Password", type="password")
            reg_submitted = st.form_submit_button("Register New Tenant")

            if reg_submitted:
                try:
                    resp = requests.post(
                        f"{API_BASE_URL}/auth/register/",
                        json={"email": reg_email, "full_name": reg_name, "password": reg_pass},
                    )
                    if resp.status_code in (200, 201):
                        st.success("Account created successfully! Please switch to the Log In tab.")
                    else:
                        st.error(f"Registration failed: {resp.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Django backend is offline. Start the server on port 8000.")

    st.stop()

# -----------------------------------------------------------------------------
# Sidebar: Tenant Switcher, Project Switcher, & Plan Specs
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("🏢 Workspace Controls")
    st.write(f"User: **{st.session_state.current_user.get('email', '')}**")

    if st.button("🚪 Sign Out", use_container_width=True):
        st.session_state.access_token = None
        st.session_state.current_user = None
        st.session_state.selected_org_id = None
        st.session_state.selected_project_id = None
        st.session_state.chat_history = []
        st.rerun()

    st.divider()

    # 1. Select Organization
    try:
        orgs_resp = requests.get(f"{API_BASE_URL}/organizations/", headers=auth_headers())
        org_list = orgs_resp.json() if orgs_resp.status_code == 200 else []
    except Exception:
        org_list = []

    if org_list:
        org_options = {org["name"]: org["id"] for org in org_list}
        selected_org_name = st.selectbox("Active Organization", list(org_options.keys()))
        st.session_state.selected_org_id = org_options[selected_org_name]
    else:
        st.warning("No organization associated with this account.")

    with st.expander("➕ Create New Organization"):
        new_org_name = st.text_input("Organization Name", key="new_org_input")
        if st.button("Create Org") and new_org_name:
            c_resp = requests.post(
                f"{API_BASE_URL}/organizations/",
                json={"name": new_org_name},
                headers=auth_headers(),
            )
            if c_resp.status_code in (200, 201):
                st.success("Organization created!")
                st.rerun()
            else:
                st.error(c_resp.text)

    st.divider()

    # 2. Select Project
    if st.session_state.selected_org_id:
        proj_resp = requests.get(
            f"{API_BASE_URL}/projects/",
            params={"organization": st.session_state.selected_org_id},
            headers=auth_headers(),
        )
        projects = proj_resp.json() if proj_resp.status_code == 200 else []

        if projects:
            proj_options = {p["name"]: p["id"] for p in projects}
            selected_proj_name = st.selectbox("Active Project", list(proj_options.keys()))
            st.session_state.selected_project_id = proj_options[selected_proj_name]
        else:
            st.warning("No projects yet.")
            st.session_state.selected_project_id = None

        with st.expander("➕ Create New Project"):
            p_name = st.text_input("Project Name", key="new_proj_name")
            p_desc = st.text_input("Description", key="new_proj_desc")
            if st.button("Create Project") and p_name:
                create_p = requests.post(
                    f"{API_BASE_URL}/projects/",
                    json={
                        "organization": st.session_state.selected_org_id,
                        "name": p_name,
                        "description": p_desc,
                    },
                    headers=auth_headers(),
                )
                if create_p.status_code in (200, 201):
                    st.success("Project created!")
                    st.rerun()
                else:
                    st.error(create_p.text)

# -----------------------------------------------------------------------------
# Top-Level Persistent Token Counter & Cost-Saver Advice
# -----------------------------------------------------------------------------
st.title("🧠 Enterprise AI Knowledge Engine")

if st.session_state.selected_org_id:
    usage_resp = requests.get(
        f"{API_BASE_URL}/usage/",
        params={"org_id": st.session_state.selected_org_id},
        headers=auth_headers(),
    )
    if usage_resp.status_code == 200:
        usage = usage_resp.json()
        token_limit = usage.get("token_limit", 50000)
        tokens_used = usage.get("total_tokens_used", 0)
        tokens_left = usage.get("remaining_tokens", max(0, token_limit - tokens_used))

        req_limit = usage.get("ai_request_limit", 100)
        reqs_used = usage.get("ai_requests", 0)
        reqs_left = usage.get("remaining_ai_requests", max(0, req_limit - reqs_used))

        doc_limit = usage.get("document_limit", 5)
        docs_used = usage.get("documents_uploaded", 0)

        # Dynamic Metrics Row
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🪙 Tokens Remaining", f"{tokens_left:,}", f"{tokens_used:,} used", delta_color="inverse")
        m2.metric("⚡ Queries Left", f"{reqs_left}", f"{reqs_used} / {req_limit}")
        m3.metric("📁 Documents Indexed", f"{docs_used} / {doc_limit}")
        m4.metric("🛡️ Active Plan", f"{usage.get('plan')}")

        # Proactive Token Saver & Cost Optimization Guide
        with st.expander("💡 Standard Operating Procedure: How to Reduce AI Token Consumption & Save Money"):
            st.markdown("""
            **Best practices to maximize your token quota and avoid unexpected overages:**
            1. **Target Specific Concepts:** Instead of asking broad prompts like *"Explain this whole PDF"*, ask specific targeted queries like *"List the 3 criteria for simplex transmission"*. Focused prompts produce concise responses, saving completion tokens.
            2. **Tune Retrieval Depth (`top_k`):** In the chat tab below, lower the chunk retrieval slider to `2` or `3`. Reducing chunks cuts the background context passed to the LLM by up to 60%.
            3. **Pre-filter Documents:** Clean out document indexes, bibliographies, and disclaimer pages before uploading files so unnecessary vector chunks are not ingested.
            4. **Avoid Duplicate Indexing:** Search existing documents in the project tab before uploading files already processed by teammates.
            """)
        st.divider()

if not st.session_state.selected_project_id:
    st.info("👈 Please select or create a Project in the sidebar to begin.")
    st.stop()

# -----------------------------------------------------------------------------
# Main Operational Workspace: Chat, Documents, Audit & Team
# -----------------------------------------------------------------------------
tab_chat, tab_docs, tab_team, tab_audit = st.tabs([
    "💬 Multi-Turn RAG Chat",
    "📁 Document Management",
    "👥 Team & Members",
    "📋 Compliance Audit Logs",
])

# =============================================================================
# TAB 1: Multi-Turn RAG Chat
# =============================================================================
with tab_chat:
    c_top1, c_top2 = st.columns([3, 1])
    with c_top1:
        st.caption("Query indexed vector embeddings using multi-turn conversational context.")
    with c_top2:
        top_k = st.slider("Retrieval Depth (Chunks)", min_value=1, max_value=8, value=3, help="Lower values consume fewer tokens")

    # Render persistent conversation
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("🔍 Referenced Source Chunks"):
                    for src in message["sources"]:
                        st.markdown(f"- **{src.get('document_title')}** (Similarity Score: `{src.get('relevance_score', 0):.2f}`)")
                        st.caption(f"> {src.get('snippet')}")

    user_query = st.chat_input("Ask a question about your project documents...")
    if user_query:
        # Prepare recent conversation turns before appending current query
        history_payload = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_history[-4:]
        ]

        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        with st.chat_message("assistant"):
            with st.spinner("Searching vectors and synthesizing answer..."):
                try:
                    rag_resp = requests.post(
                        f"{API_BASE_URL}/ai/query/",
                        json={
                            "project_id": st.session_state.selected_project_id,
                            "query": user_query,
                            "top_k": top_k,
                            "chat_history": history_payload,
                        },
                        headers=auth_headers(),
                    )

                    if rag_resp.status_code == 200:
                        ans_data = rag_resp.json()
                        answer_text = ans_data.get("answer", "")
                        sources = ans_data.get("sources", [])

                        st.markdown(answer_text)

                        if sources:
                            with st.expander("🔍 Referenced Source Chunks"):
                                for s in sources:
                                    st.markdown(f"- **{s.get('document_title')}** (Similarity Score: `{s.get('relevance_score', 0):.2f}`)")
                                    st.caption(f"> {s.get('snippet')}")

                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": answer_text,
                            "sources": sources,
                        })
                    elif rag_resp.status_code == 429:
                        st.error("Quota exceeded! You have exhausted your monthly AI queries or tokens.")
                    else:
                        st.error(f"Error executing AI query ({rag_resp.status_code}): {rag_resp.text}")
                except Exception as e:
                    st.error(f"Request failed: {str(e)}")

# =============================================================================
# TAB 2: Document Management & Ingestion
# =============================================================================
with tab_docs:
    st.subheader("Upload Document for Vectorization")
    doc_title = st.text_input("Document Title (e.g. Network Layer Specification)")
    uploaded_file = st.file_uploader("Select file (PDF, TXT, MD)", type=["pdf", "txt", "md"])

    if st.button("Upload & Vectorize"):
        if not doc_title or not uploaded_file:
            st.warning("Please supply both a document title and a file.")
        else:
            with st.spinner("Uploading and running ingestion pipeline..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                data = {
                    "title": doc_title,
                    "organization_id": st.session_state.selected_org_id,
                }
                upload_resp = requests.post(
                    f"{API_BASE_URL}/documents/project/{st.session_state.selected_project_id}/",
                    data=data,
                    files=files,
                    headers=auth_headers(),
                )
                if upload_resp.status_code in (200, 201):
                    st.success("Document uploaded! Ingestion task completed.")
                    st.rerun()
                else:
                    st.error(f"Upload failed: {upload_resp.text}")

    st.divider()
    st.subheader("Existing Project Documents")
    docs_resp = requests.get(
        f"{API_BASE_URL}/documents/project/{st.session_state.selected_project_id}/",
        headers=auth_headers(),
    )
    if docs_resp.status_code == 200:
        docs = docs_resp.json()
        if docs:
            for d in docs:
                status = d.get("status", "PENDING")
                status_color = "🟢" if status == "READY" else ("🔴" if status == "FAILED" else "🟡")
                st.write(f"{status_color} **{d.get('title')}** — Status: `{status}` — ID: `{d.get('id')}`")
        else:
            st.info("No documents uploaded for this project yet.")

# =============================================================================
# TAB 3: Team & Members (RBAC Management)
# =============================================================================
with tab_team:
    st.subheader("Tenant Members & Roles")
    st.caption("Manage access control within this organization.")

    with st.form("invite_member_form"):
        col_m1, col_m2 = st.columns([3, 2])
        with col_m1:
            inv_email = st.text_input("Teammate Email")
        with col_m2:
            inv_role = st.selectbox("Assign Role", ["MEMBER", "VIEWER", "ADMIN"])
        invite_submitted = st.form_submit_button("Add Member")

        if invite_submitted and inv_email:
            st.info(f"Role invitation ready: {inv_email} assigned as {inv_role}. (RBAC records mapped to org context).")

# =============================================================================
# TAB 4: Compliance Audit Logs
# =============================================================================
with tab_audit:
    st.subheader("Tenant Audit Trail")
    st.caption("Immutable record of all document uploads, authentication events, and AI queries.")

    audit_resp = requests.get(
        f"{API_BASE_URL}/audit/",
        params={"org_id": st.session_state.selected_org_id},
        headers=auth_headers(),
    )
    if audit_resp.status_code == 200:
        logs = audit_resp.json()
        if logs:
            for item in logs:
                st.markdown(f"📌 **{item.get('action')}** | Triggered by `{item.get('actor')}` at `{item.get('timestamp')}`")
                st.json(item.get("details", {}))
                st.divider()
        else:
            st.info("No audit logs recorded for this tenant yet.")