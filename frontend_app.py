import os
import streamlit as st
import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000/api").rstrip("/")

st.set_page_config(page_title="Enterprise AI Engine", page_icon="🧠", layout="wide")

if "token" not in st.session_state:
    st.session_state.token = None
if "selected_org_id" not in st.session_state:
    st.session_state.selected_org_id = None
if "selected_project_id" not in st.session_state:
    st.session_state.selected_project_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def get_headers():
    return {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json",
    }


def auth_view():
    st.title("🧠 Enterprise AI Engine")
    mode = st.radio("Choose Mode", ["Login", "Register"], horizontal=True)

    col1, _ = st.columns([1, 1])
    with col1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")

        if mode == "Register":
            password_confirm = st.text_input("Confirm Password", type="password")
            if st.button("Register Account", use_container_width=True):
                if password != password_confirm:
                    st.error("Passwords do not match.")
                else:
                    res = requests.post(
                        f"{API_BASE_URL}/auth/register/",
                        json={
                            "email": email,
                            "password": password,
                            "password_confirm": password_confirm,
                        },
                    )
                    if res.status_code == 201:
                        st.success("Registration successful! Please login.")
                    else:
                        st.error(f"Registration failed: {res.text}")
        else:
            if st.button("Log In", use_container_width=True):
                # Try standard /auth/login/ then fallback to /auth/token/
                res = requests.post(f"{API_BASE_URL}/auth/login/", json={"email": email, "password": password})
                if res.status_code != 200:
                    res = requests.post(f"{API_BASE_URL}/auth/token/", json={"email": email, "password": password})

                if res.status_code == 200:
                    data = res.json()
                    st.session_state.token = data.get("access") or data.get("token")
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")


def dashboard_view():
    with st.sidebar:
        st.title("🏢 Workspace")
        if st.button("Sign Out"):
            st.session_state.token = None
            st.session_state.chat_history = []
            st.rerun()

        # Organization Selection
        org_res = requests.get(f"{API_BASE_URL}/organizations/", headers=get_headers())
        if org_res.status_code == 200:
            orgs = org_res.json().get("results", org_res.json())
            org_map = {o["name"]: o["id"] for o in orgs}
            if org_map:
                chosen_org_name = st.selectbox("Organization", list(org_map.keys()))
                st.session_state.selected_org_id = org_map[chosen_org_name]
            else:
                st.info("Create an organization to start.")
                new_org = st.text_input("Organization Name")
                if st.button("Create Org"):
                    requests.post(f"{API_BASE_URL}/organizations/", headers=get_headers(), json={"name": new_org})
                    st.rerun()

        # Scoped Project Selection
        if st.session_state.selected_org_id:
            st.markdown("---")
            proj_res = requests.get(
                f"{API_BASE_URL}/projects/?organization={st.session_state.selected_org_id}",
                headers=get_headers(),
            )
            if proj_res.status_code == 200:
                projects = proj_res.json().get("results", proj_res.json())
                proj_map = {p["name"]: p["id"] for p in projects}
                if proj_map:
                    chosen_proj_name = st.selectbox("Project", list(proj_map.keys()))
                    st.session_state.selected_project_id = proj_map[chosen_proj_name]
                else:
                    st.info("No projects in this organization.")
                    new_p = st.text_input("New Project Name")
                    if st.button("Create Project"):
                        p_res = requests.post(
                            f"{API_BASE_URL}/projects/",
                            headers=get_headers(),
                            json={"name": new_p, "organization": st.session_state.selected_org_id},
                        )
                        if p_res.status_code == 201:
                            st.rerun()
                        else:
                            st.error(p_res.text)

        # Quota Telemetry
        if st.session_state.selected_org_id:
            st.markdown("---")
            st.subheader("📊 Live Quota")
            usage_res = requests.get(
                f"{API_BASE_URL}/usage/summary/?organization={st.session_state.selected_org_id}",
                headers=get_headers(),
            )
            if usage_res.status_code == 200:
                u = usage_res.json()
                st.caption(f"**Plan**: {u.get('plan_name')}")
                st.caption(f"**AI Requests**: {u.get('ai_requests_used', 0)} / {u.get('max_ai_requests', 0)}")
                st.caption(f"**Tokens**: {u.get('tokens_used', 0):,} / {u.get('max_tokens', 0):,}")
                st.caption(f"**Documents**: {u.get('documents_count', 0)} / {u.get('max_documents', 0)}")

    tab_chat, tab_docs, tab_team, tab_audit = st.tabs(["💬 Chat", "📄 Documents", "👥 Team", "🛡️ Audit"])

    with tab_chat:
        if not st.session_state.selected_project_id:
            st.warning("Select or create a project first.")
        else:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if msg.get("sources"):
                        with st.expander("Sources"):
                            for s in msg["sources"]:
                                st.write(f"- {s}")

            user_query = st.chat_input("Ask a question about the project documents...")
            if user_query:
                st.session_state.chat_history.append({"role": "user", "content": user_query})
                with st.chat_message("user"):
                    st.markdown(user_query)

                with st.chat_message("assistant"):
                    with st.spinner("Retrieving and synthesizing..."):
                        r_res = requests.post(
                            f"{API_BASE_URL}/ai/query/",
                            headers=get_headers(),
                            json={
                                "project_id": st.session_state.selected_project_id,
                                "query": user_query,
                                "chat_history": st.session_state.chat_history[:-1],
                            },
                        )
                        if r_res.status_code == 200:
                            data = r_res.json()
                            ans = data.get("response", "")
                            sources = data.get("sources", [])
                            st.markdown(ans)
                            if sources:
                                with st.expander("Sources"):
                                    for s in sources:
                                        st.write(f"- {s}")
                            st.session_state.chat_history.append({"role": "assistant", "content": ans, "sources": sources})
                        else:
                            st.error(r_res.text)

    with tab_docs:
        if st.session_state.selected_project_id:
            f = st.file_uploader("Upload Document", type=["txt", "pdf", "docx"])
            if f and st.button("Upload & Ingest"):
                res = requests.post(
                    f"{API_BASE_URL}/documents/project/{st.session_state.selected_project_id}/",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    data={"title": f.name},
                    files={"file": (f.name, f.getvalue())},
                )
                if res.status_code == 201:
                    st.success("Uploaded! Ingestion queued.")
                else:
                    st.error(res.text)

    with tab_team:
        if st.session_state.selected_org_id:
            c1, _ = st.columns(2)
            with c1:
                inv_email = st.text_input("Invite Email")
                inv_role = st.selectbox("Role", ["MEMBER", "ADMIN"])
                if st.button("Generate Invite"):
                    res = requests.post(
                        f"{API_BASE_URL}/organizations/{st.session_state.selected_org_id}/invites/",
                        headers=get_headers(),
                        json={"email": inv_email, "role": inv_role},
                    )
                    if res.status_code == 201:
                        st.success(f"Token: `{res.json().get('token')}`")
                    else:
                        st.error(res.text)

    with tab_audit:
        if st.session_state.selected_org_id:
            # Backend accepts both ?org_id= and ?organization=
            a_res = requests.get(
                f"{API_BASE_URL}/audit/?org_id={st.session_state.selected_org_id}",
                headers=get_headers(),
            )
            if a_res.status_code == 200:
                logs = a_res.json().get("results", a_res.json())
                for log in logs:
                    st.text(f"[{log.get('created_at')}] {log.get('action')} - {log.get('actor') or log.get('ip_address')}")
            else:
                st.caption("No audit access or logs found.")


if not st.session_state.token:
    auth_view()
else:
    dashboard_view()
