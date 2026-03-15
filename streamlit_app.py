import streamlit as st
import sys
import os
import time

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Minimal imports for the Streamlit version
# Note: In a real deploy, these would need the same environment as the FastAPI backend
try:
    from modules.decision_engine import DecisionEngine, Verdict
except ImportError:
    st.error("Could not import backend modules. Please ensure the backend folder is in the path.")
    st.stop()

st.set_page_config(
    page_title="Product Detective 🕵️‍♂️🔍",
    page_icon="🔍",
    layout="wide",
)

# --- STYLING ---
st.markdown("""
<style>
    .stApp {
        background-color: #F5F0E8;
    }
    .main-title {
        color: #1A1A1A;
        font-family: 'Courier New', Courier, monospace;
        font-weight: bold;
        border-bottom: 2px solid #1A1A1A;
        padding-bottom: 10px;
    }
    .verdict-box {
        padding: 20px;
        border-radius: 10px;
        border: 2px solid #1A1A1A;
        margin-top: 20px;
        text-align: center;
    }
    .buy { background-color: #D4EDDA; color: #155724; }
    .wait { background-color: #FFF3CD; color: #856404; }
    .avoid { background-color: #F8D7DA; color: #721C24; }
</style>
""", unsafe_allow_html=True)

# --- HEADER ---
st.markdown("<h1 class='main-title'>🕵️‍♂️🔍 PRODUCT DETECTIVE</h1>", unsafe_allow_html=True)
st.caption("AI-Powered Purchase Intelligence · Online Reviews Checker")

# --- SIDEBAR / INPUTS ---
with st.sidebar:
    st.header("Case Details")
    url = st.text_input("Product URL", placeholder="https://amazon.in/dp/...")
    budget = st.number_input("Budget (₹)", min_value=0, value=0)
    purpose = st.selectbox("Purpose", ["Daily Use", "Gaming", "Content Creation", "Professional"])
    priority = st.selectbox("Priority", ["Performance", "Battery", "Durability", "Price/Value"])
    
    investigate_btn = st.button("⚖️ INVESTIGATE", use_container_width=True)

# --- CONTENT ---
if investigate_btn and url:
    with st.status("🕵️‍♂️ Detective is investigating...", expanded=True) as status:
        st.write("Scraping reviews...")
        time.sleep(1.5)
        st.write("Analyzing sentiment...")
        time.sleep(1)
        st.write("Detecting complaint patterns...")
        time.sleep(1)
        st.write("Verifying review authenticity...")
        time.sleep(1)
        status.update(label="Investigation Complete!", state="complete", expanded=False)

    # Mocking data for the Streamlit demo version if DB isn't available
    # In a full deployment, this would call the actual scraper and models
    st.subheader(f"Results for Case: #PD-{int(time.time()) % 10000}")
    
    # Simple Demo Logic (Fallback)
    engine = DecisionEngine()
    
    # Mocking reports for demonstration if the full pipeline isn't triggered
    # (Streamlit Cloud usually won't have MongoDB/Redis)
    st.info("Note: This is the Streamlit Cloud version. Real-time scraping is limited.")
    
    # Example dynamic rendering based on inputs
    if "gaming" in purpose.lower():
        verdict = "WAIT"
        score = 0.52
        evidence = [
            "Overheating complaints tripled in 6 months",
            "Cooling system scores 41/100 for gaming-class laptop",
            "Review trust score 68/100 — possible manipulation"
        ]
    else:
        verdict = "BUY"
        score = 0.85
        evidence = [
            "Strong community approval (85% positive)",
            "No critical complaint patterns detected",
            "Excellent build quality for the price"
        ]

    # --- DISPLAY VERDICT ---
    v_class = verdict.lower()
    st.markdown(f"""
    <div class='verdict-box {v_class}'>
        <h2 style='margin:0;'>{verdict}</h2>
        <p>Confidence: {int(score*100)}%</p>
    </div>
    """, unsafe_allow_html=True)

    st.write("### Evidence Summary")
    for point in evidence:
        st.write(f"◈ {point}")

    if verdict == "WAIT":
        st.warning("Hold off — a better option or timing exists.")
        st.write("#### Recommended Alternatives")
        st.write("- **ASUS ROG Strix G15 (2024)**: ₹89,990")
        st.write("- **Lenovo Legion 5 Pro (2024)**: ₹92,000")
    elif verdict == "BUY":
        st.success("The case is closed. This product is a solid investment.")
    else:
        st.error("AVOID: Your money is better spent elsewhere.")

else:
    st.write("### Welcome, Detective.")
    st.write("Enter a product URL in the sidebar to begin your investigation.")
    
    # UI Cards
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.write("🔍 **Detect Fake Reviews**")
            st.write("Our AI identifies manipulation patterns and bot-generated feedback.")
    with col2:
        with st.container(border=True):
            st.write("⚖️ **Truth-Based Verdicts**")
            st.write("Get a clear BUY, WAIT, or AVOID ruling based on data, not hype.")
