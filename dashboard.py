import streamlit as st
from pymongo.mongo_client import MongoClient
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import zipfile
import io
import os
import json
import google.generativeai as genai

MONGO_URI = "mongodb+srv://sujithdevelop:Gjo240Y2a4XYDyoW@cluster0.yqgl34a.mongodb.net/github_analytics?retryWrites=true&w=majority&tlsInsecure=true"
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["github_analytics"]
collection = db["repo_data"]
PRODUCER_API = "https://github-producer-api.onrender.com"



def fetch(owner, repo):
    try:
        url = f"{PRODUCER_API}/fetch?owner={owner}&repo={repo}"
        res = requests.get(url)

        if res.status_code != 200:
            return res.status_code, {"status": "error", "detail": res.text}

        data = res.json()

        collection.update_one(
            {"repo.name": repo, "repo.owner": owner},
            {"$set": data},
            upsert=True
        )

        return res.status_code, {"status": "success", "message": f"{owner}/{repo} data stored."}

    except Exception as e:
        return 500, {"status": "error", "detail": str(e)}


genai.configure(api_key="AIzaSyCihZ-7-DqWurLTv3B1OnVcCafUEIaqkS8")
model = genai.GenerativeModel(os.getenv("MODEL","gemini-2.5-pro"))

def generate_repo_summary(data: dict) -> str:
    prompt = f"""
    Summarize the health, activity, and maintenance status of the following GitHub repository:

    - Name: {data['repo']['name']}
    - Owner: {data['repo']['owner']}
    - Stars: {data['repo']['stars']}
    - Forks: {data['repo']['forks']}
    - Open Issues: {data['repo']['open_issues']}
    - Commit Count: {len(data.get('commits', []))}
    - Pull Requests: {len(data.get('pull_requests', []))}
    - Contributors: {len(data.get('contributors', []))}

    Respond in 3–4 lines, like a GitHub project review.
    """
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        return f"⚠️ Gemini Error: {str(e)}"

def ask_question_about_repo(data: dict, question: str) -> str:
    context = {
        "repo": data.get("repo", {}),
        "stats": {
            "commits": len(data.get("commits", [])),
            "pull_requests": len(data.get("pull_requests", [])),
            "issues": len(data.get("issues", [])),
            "contributors": len(data.get("contributors", [])),
        },
        "top_contributors": sorted(
            data.get("contributors", []), key=lambda x: x.get("contributions", 0), reverse=True
        )[:5]
    }

    full_prompt = f"""
    You are an expert GitHub project analyst.
    Here’s a snapshot of a repository:

    {json.dumps(context, indent=2)}

    Now answer this question: {question}
    """

    try:
        res = model.generate_content(full_prompt)
        return res.text.strip()
    except Exception as e:
        return f"⚠️ Gemini Error: {str(e)}"

def generate_repo_tags(data: dict) -> list:
    prompt = f"""
    Analyze this GitHub repo and return 3–5 tags describing its nature.

    Examples: #well-maintained, #highly-active, #needs-maintenance, #community-driven

    Repo data:
    Name: {data['repo']['name']}
    Owner: {data['repo']['owner']}
    Stars: {data['repo']['stars']}
    Open Issues: {data['repo']['open_issues']}
    Commits: {len(data['commits'])}
    PRs: {len(data['pull_requests'])}
    Contributors: {len(data['contributors'])}

    Only return a comma-separated list of tags.
    """

    try:
        res = model.generate_content(prompt)
        return [t.strip() for t in res.text.split(",")]
    except Exception as e:
        return "[f\"#gemini_error: {str(e)}\"]"


st.set_page_config(
    page_title="GitHub Analytics Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced aestheticsc
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .main {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 50%, #2d1b69 100%);
        color: #ffffff;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 50%, #2d1b69 100%);
    }
    
    /* Animated gradient title */
    .gradient-title {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4, #ffeaa7);
        background-size: 300% 300%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: gradientShift 3s ease infinite;
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    /* Glass morphism cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 40px rgba(0, 0, 0, 0.4);
    }
    
    /* Neon glow buttons */
    .neon-button {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        border: none;
        border-radius: 50px;
        padding: 0.75rem 2rem;
        color: white;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.4);
    }
    
    .neon-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(255, 107, 107, 0.6);
    }
    
    /* Custom metrics styling */
    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
        margin: 0.5rem;
    }
    
    .metric-card:hover {
        transform: scale(1.05);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #4ecdc4;
        margin-bottom: 0.5rem;
    }
    
    .metric-label {
        font-size: 1rem;
        color: #b8bcc8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Enhanced expander styling */
    .streamlit-expanderHeader {
        background: linear-gradient(90deg, #ff6b6b, #4ecdc4);
        border-radius: 10px;
        color: white !important;
        font-weight: 600;
    }
    
    /* Repo card styling */
    .repo-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.2);
        padding: 2rem;
        margin: 1rem;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .repo-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, #ff6b6b, #4ecdc4, #45b7d1);
    }
    
    .repo-card:hover {
        transform: translateY(-10px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
    }
    
    .repo-title {
        font-size: 1.5rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 1rem;
    }
    
    /* Chat styling */
    .chat-container {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 1.5rem;
        margin: 1rem 0;
    }
    
    .user-message {
        background: linear-gradient(135deg, #ff6b6b, #ff8e8e);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 5px 20px;
        margin: 0.5rem 0;
        max-width: 80%;
        margin-left: auto;
    }
    
    .bot-message {
        background: linear-gradient(135deg, #4ecdc4, #6ee7df);
        color: #1a1a1a;
        padding: 1rem 1.5rem;
        border-radius: 20px 20px 20px 5px;
        margin: 0.5rem 0;
        max-width: 80%;
    }
    
    /* Health score styling */
    .health-score {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        color: white;
        font-size: 2rem;
        font-weight: 700;
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1f2e 0%, #2d1b69 100%);
    }
    
    /* Remove Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(45deg, #ff6b6b, #4ecdc4);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(45deg, #ff5252, #26a69a);
    }
    
    /* Plotly chart styling */
    .js-plotly-plot {
        background: rgba(255, 255, 255, 0.05) !important;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Success/Error message styling */
    .stSuccess {
        background: linear-gradient(135deg, #4ecdc4, #44a08d);
        color: white;
        border-radius: 15px;
        border: none;
    }
    
    .stError {
        background: linear-gradient(135deg, #ff6b6b, #ee5a52);
        color: white;
        border-radius: 15px;
        border: none;
    }
    
    .stWarning {
        background: linear-gradient(135deg, #ffeaa7, #fdcb6e);
        color: #2d3436;
        border-radius: 15px;
        border: none;
    }
</style>
""", unsafe_allow_html=True)

# Animated title
st.markdown('<h1 class="gradient-title"> GitHub Analytics Dashboard</h1>', unsafe_allow_html=True)

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Connect to MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["github_analytics"]
collection = db["repo_data"]

# Fetch list of repos
repos = list(collection.find({}, {"_id": 0, "repo.name": 1, "repo.owner": 1}))

# New Repo Form with enhanced styling
with st.expander("✨ Fetch New Repository", expanded=False):
    
    with st.form("fetch_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_owner = st.text_input("🏢 GitHub Owner", placeholder="Enter repository owner...")
        with col2:
            new_repo = st.text_input("📁 Repository Name", placeholder="Enter repository name...")
        
        submit = st.form_submit_button("🚀 Fetch Repository")

        if submit and new_owner and new_repo:
            try:
                if submit and new_owner and new_repo:
                    with st.spinner("🔄 Fetching repository data..."):
                        status_code, response_data = fetch(new_owner, new_repo)

                        if status_code == 200:
                            st.success(f"✅ {response_data.get('message', 'Repository fetched successfully!')}")
                            st.rerun()
                        else:
                            st.error(f"❌ {response_data.get('detail', 'Failed to fetch repository.')}")

            except Exception as e:
                st.error(f"🚨 Request error: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

if not repos:
    st.markdown("""
    <div class="glass-card" style="text-align: center;">
        <h3>🔍 No Repositories Found</h3>
        <p>Use the fetch form above to add your first repository!</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

repo_names = [f"{r['repo']['owner']}/{r['repo']['name']}" for r in repos]

# Enhanced Repo Cards Overview
st.markdown('<h2 style="color: #4ecdc4; text-align: center; margin: 2rem 0;">📚 Repository Collection</h2>', unsafe_allow_html=True)

cols = st.columns(3)
for i, repo in enumerate(repos):
    with cols[i % 3]:
        name = repo['repo']['name']
        owner = repo['repo']['owner']
        
        full_data = collection.find_one({"repo.name": name, "repo.owner": owner}, {"_id": 0, "repo": 1, "contributors": 1, "commits": 1, "pull_requests": 1})
        if full_data:
            repo_info = full_data["repo"]
            stars = repo_info.get("stars", 0)
            open_issues = repo_info.get("open_issues", 0)
            commits_count = len(full_data.get("commits", []))
            prs_count = len(full_data.get("pull_requests", []))
            denominator = stars + commits_count + prs_count
            health_score = ((stars + commits_count + prs_count - open_issues) / denominator) * 100 if denominator else 0

            # Custom repo card
            st.markdown(f"""
            <div class="repo-card">
                <div class="repo-title">💼 {owner}/{name}</div>
                <div style="display: flex; justify-content: space-between; margin: 1rem 0;">
                    <div class="metric-card">
                        <div class="metric-value">⭐ {stars}</div>
                        <div class="metric-label">Stars</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">🍴 {repo_info.get("forks", 0)}</div>
                        <div class="metric-label">Forks</div>
                    </div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">🧠 {round(health_score, 1)}%</div>
                    <div class="metric-label">Health Score</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔬 Analyze Repository", key=f"view_{i}", help=f"Deep dive into {owner}/{name}"):
                st.session_state["repo_override"] = f"{owner}/{name}"
                st.rerun()

# Repo Detail View
if "repo_override" in st.session_state:
    selected_repo = st.session_state["repo_override"]
else:
    st.markdown('<h3 style="color: #ff6b6b;">🎯 Select Repository for Analysis</h3>', unsafe_allow_html=True)
    selected_repo = st.selectbox("Choose a repository to analyze", repo_names, label_visibility="collapsed")

owner, name = selected_repo.split("/")
data = collection.find_one({"repo.name": name, "repo.owner": owner}, {"_id": 0})

if data:
    # Enhanced header
    st.markdown(f"""
    <div class="glass-card">
        <h1 style="color: #ffffff; text-align: center; margin-bottom: 2rem;">
            🎯 {owner}/{name}
        </h1>
    </div>
    """, unsafe_allow_html=True)
    
    repo_info = data["repo"]

    # Enhanced Action Buttons
    st.markdown('<h3 style="color: #4ecdc4;">⚡ Quick Actions</h3>', unsafe_allow_html=True)
    cols = st.columns([1, 1, 1, 1])
    
    if cols[0].button("🏷️ Generate Tags", help="AI-powered repository tags"):
        with st.spinner("🤖 Generating intelligent tags..."):
            tags = generate_repo_tags(data)
        st.success("🎉 Tags: " + ", ".join(tags))

    if cols[1].button("🗑️ Delete Repository", help="Remove repository from database"):
        collection.delete_one({"repo.name": name, "repo.owner": owner})
        db["repo_history"].delete_many({"repo": name, "owner": owner})
        st.success("🗑️ Repository deleted successfully!")
        st.session_state.pop("repo_override", None)
        st.rerun()

    if cols[2].button("📤 Export Data", help="Download all repository data"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for key in ["commits", "pull_requests", "issues", "contributors"]:
                df = pd.DataFrame(data.get(key, []))
                if not df.empty:
                    csv_bytes = df.to_csv(index=False).encode('utf-8')
                    zip_file.writestr(f"{name}_{key}.csv", csv_bytes)
        zip_buffer.seek(0)
        st.download_button("📥 Download ZIP", zip_buffer, file_name=f"{name}_github_data.zip", mime="application/zip")

    if cols[3].button("🔙 Back to Dashboard", help="Return to main dashboard"):
        st.session_state.pop("repo_override", None)
        st.rerun()

    # Enhanced Repo Metrics
    
    mcols = st.columns(4)
    metrics = [
        ("⭐", "Stars", repo_info.get("stars", 0)),
        ("🍴", "Forks", repo_info.get("forks", 0)),
        ("👁️", "Watchers", repo_info.get("watchers", 0)),
        ("🐞", "Issues", repo_info.get("open_issues", 0))
    ]
    
    for i, (icon, label, value) in enumerate(metrics):
        with mcols[i]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{icon} {value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Enhanced Contributors Section
    contributors = pd.DataFrame(data.get("contributors", []))
    if not contributors.empty:
        st.markdown('<h3 style="color: #4ecdc4;">👥 Top Contributors</h3>', unsafe_allow_html=True)
        
        st.dataframe(
            contributors.sort_values("contributions", ascending=False),
            use_container_width=True,
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced Commits Timeline
    commits = pd.DataFrame(data.get("commits", []))
    if not commits.empty:
        commits["date"] = pd.to_datetime(commits["date"]).dt.tz_localize(None)
        commits["author"] = commits["author"].fillna("Unknown")

        st.markdown('<h3 style="color: #4ecdc4;">📈 Commit Activity Timeline</h3>', unsafe_allow_html=True)
        
        
        date_range = st.date_input(
            "📅 Filter by date range", 
            [commits["date"].min(), commits["date"].max()],
            help="Select date range to analyze commit patterns"
        )
        
        if len(date_range) == 2:
            commits = commits[
                (commits["date"] >= pd.to_datetime(date_range[0])) & 
                (commits["date"] <= pd.to_datetime(date_range[1]))
            ]

        # Enhanced plotly chart
        fig = px.histogram(
            commits, 
            x="date", 
            color="author",
            title="🚀 Commit Activity Over Time",
            template="plotly_dark"
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font_color='white'
        )
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced Pull Requests
    prs = pd.DataFrame(data.get("pull_requests", []))
    if not prs.empty:
        st.markdown('<h3 style="color: #4ecdc4;">🔄 Pull Requests</h3>', unsafe_allow_html=True)
        
        
        selected_state = st.selectbox(
            "🎯 Filter by status", 
            ["all", "open", "closed"], 
            index=0,
            help="Filter pull requests by their current state"
        )
        
        if selected_state != "all":
            prs = prs[prs["state"] == selected_state]
        
        st.dataframe(
            prs[["title", "state", "user", "created_at", "closed_at"]],
            use_container_width=True,
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced Issues
    issues = pd.DataFrame(data.get("issues", []))
    if not issues.empty:
        st.markdown('<h3 style="color: #4ecdc4;">🐛 Issues Tracker</h3>', unsafe_allow_html=True)
        
        
        col1, col2 = st.columns(2)
        with col1:
            issue_states = st.multiselect(
                "📊 Filter by state", 
                issues["state"].unique(), 
                default=issues["state"].unique(),
                help="Select issue states to display"
            )
        with col2:
            issue_users = st.multiselect(
                "👤 Filter by user", 
                issues["user"].unique(),
                help="Select specific users to filter by"
            )
        
        if issue_states:
            issues = issues[issues["state"].isin(issue_states)]
        if issue_users:
            issues = issues[issues["user"].isin(issue_users)]
        
        st.dataframe(
            issues[["title", "state", "user", "created_at", "closed_at"]],
            use_container_width=True,
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced AI Summary
    with st.expander("🧠 AI-Powered Repository Insights", expanded=False):
        
        if st.button("✨ Generate Deep Analysis", help="Get AI-powered insights about this repository"):
            with st.spinner("🤖 Analyzing repository patterns..."):
                summary = generate_repo_summary(data)
            st.success("🎯 Analysis Complete!")
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, rgba(78, 205, 196, 0.1), rgba(69, 183, 209, 0.1)); 
                        border-radius: 15px; padding: 2rem; margin: 1rem 0; 
                        border-left: 4px solid #4ecdc4;">
                <h4 style="color: #4ecdc4; margin-bottom: 1rem;">📊 Repository Intelligence Report</h4>
                <p style="color: #ffffff; line-height: 1.6;">{summary}</p>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced LLM Chat
    with st.expander("💬 Interactive Repository Assistant", expanded=False):
        
        # Display chat history with enhanced styling
        for entry in st.session_state.chat_history:
            st.markdown(f"""
            <div class="user-message">
                <strong>🧑‍💻 You:</strong> {entry['question']}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="bot-message">
                <strong>🤖 Assistant:</strong> {entry['answer']}
            </div>
            """, unsafe_allow_html=True)

        # Chat input
        user_question = st.text_input(
            "💭 Ask me anything about this repository...", 
            key="chat_input",
            placeholder="e.g., What are the main contributors' patterns?",
            help="Ask questions about repository statistics, patterns, or insights"
        )
        
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("🚀 Ask Assistant", key="ask_button"):
                if user_question.strip():
                    with st.spinner("🧠 Thinking..."):
                        answer = ask_question_about_repo(data, user_question)
                    st.session_state.chat_history.append({"question": user_question, "answer": answer})
                    st.rerun()
                else:
                    st.warning("💡 Please enter a question to get started!")
        
        with col2:
            if st.button("🧹 Clear Chat", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    # Enhanced Health Score
    prs_count = len(prs)
    commits_count = len(commits)
    denominator = repo_info.get("stars", 0) + commits_count + prs_count
    if denominator:
        health_score = ((repo_info.get("stars", 0) + commits_count + prs_count - repo_info.get("open_issues", 0)) / denominator) * 100
        
        st.markdown(f"""
        <div class="health-score">
            <h3>🏥 Repository Health Score</h3>
            <div style="font-size: 3rem; margin: 1rem 0;">{round(health_score, 1)}%</div>
            <p style="opacity: 0.8;">Health = (Stars + Commits + PRs - Open Issues) / (Stars + Commits + PRs)</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Health score visualization
        fig = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = health_score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Health Score"},
            delta = {'reference': 75},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "#4ecdc4"},
                'steps': [
                    {'range': [0, 50], 'color': "rgba(255, 107, 107, 0.3)"},
                    {'range': [50, 80], 'color': "rgba(255, 234, 167, 0.3)"},
                    {'range': [80, 100], 'color': "rgba(78, 205, 196, 0.3)"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font={'color': "white", 'family': "Inter"},
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
else:
    st.markdown("""
    <div class="glass-card" style="text-align: center;">
        <h3 style="color: #ff6b6b;">❌ Repository Not Found</h3>
        <p>The selected repository data could not be found in the database.</p>
    </div>
    """, unsafe_allow_html=True)

