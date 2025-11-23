import streamlit as st
import json
import os
from anthropic import Anthropic
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Initialize Claude client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Page config
st.set_page_config(
    page_title="AI Sourcing Assistant",
    page_icon="🎯",
    layout="wide"
)

# Load mock distributor data
@st.cache_data
def load_distributors():
    try:
        with open('data/mock_distributors.json', 'r') as f:
            return json.load(f)
    except:
        return {}

DISTRIBUTORS = load_distributors()

# Category mapping
CATEGORY_MAP = {
    "pet": ["pet_products"],
    "electronics": ["electronics"],
    "phone": ["electronics"],
    "wireless": ["electronics"],
    "health": ["health_wellness"],
    "vitamin": ["health_wellness"],
    "supplement": ["health_wellness"]
}

def get_product_ideas(category: str, count: int = 5):
    """Use Claude to generate product ideas"""
    prompt = f"""You are an e-commerce market research expert. Generate {count} best-selling product ideas in the "{category}" category.

For each product, provide:
1. Product name
2. Brief description (1 sentence)
3. Estimated retail price
4. Profit potential score (0-100)
5. Demand level (High/Medium/Low)

Format as JSON array with keys: name, description, price, profit_score, demand

Focus on real, popular products that exist in wholesale markets."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract JSON from response
        content = response.content[0].text
        # Try to find JSON in the response
        start = content.find('[')
        end = content.rfind(']') + 1
        if start != -1 and end > start:
            products = json.loads(content[start:end])
            return products
        else:
            raise ValueError("No JSON found in response")
    except Exception as e:
        st.error(f"Error generating products: {e}")
        # Fallback mock data
        return [
            {
                "name": f"Popular {category} Product {i+1}",
                "description": f"High-demand {category} item with proven sales",
                "price": f"${20 + i*10}-{30 + i*10}",
                "profit_score": 70 + i*5,
                "demand": "High"
            } for i in range(count)
        ]

def find_distributors(category: str, product_name: str):
    """Find relevant distributors based on category"""
    # Map category to distributor categories
    dist_categories = []
    for key, cats in CATEGORY_MAP.items():
        if key.lower() in category.lower():
            dist_categories.extend(cats)
    
    if not dist_categories:
        dist_categories = list(DISTRIBUTORS.keys())
    
    # Collect distributors
    found = []
    for cat in dist_categories:
        if cat in DISTRIBUTORS:
            found.extend(DISTRIBUTORS[cat])
    
    return found[:4] if found else []

def verify_legitimacy(distributor: dict):
    """Use Claude to verify distributor legitimacy"""
    prompt = f"""Analyze this distributor's legitimacy as a wholesale supplier:

Name: {distributor['name']}
Location: {distributor['location']}
Website: {distributor['website']}
Legitimacy Signals: {', '.join(distributor.get('legitimacy_signals', []))}
Has 3PL/Prep Services: {distributor.get('has_3pl', False)}

Provide:
1. Legitimacy score (0-100)
2. Brief reasoning (2-3 sentences)
3. Risk level (Low/Medium/High)

Format as JSON: {{"score": <number>, "reasoning": "<text>", "risk": "<level>"}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.content[0].text
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end > start:
            result = json.loads(content[start:end])
            return result
        else:
            raise ValueError("No JSON found")
    except Exception as e:
        # Fallback scoring
        signals = distributor.get('legitimacy_signals', [])
        score = 50 + len(signals) * 10
        return {
            "score": min(score, 95),
            "reasoning": f"Distributor has {len(signals)} verification signals including {', '.join(signals[:2])}.",
            "risk": "Low" if score > 70 else "Medium"
        }

def generate_outreach_email(product: dict, distributor: dict, user_info: dict):
    """Generate personalized outreach email"""
    prompt = f"""Generate a professional B2B outreach email for wholesale sourcing.

Context:
- I'm an e-commerce business owner looking to source: {product['name']}
- Contacting: {distributor['name']} ({distributor['location']})
- My business: {user_info.get('business_name', 'My E-commerce Business')}
- Target: {user_info.get('monthly_volume', '500-1000')} units/month

The email should:
1. Introduce my business professionally
2. Express interest in {product['name']}
3. Ask about: wholesale pricing, MOQ, shipping to prep centers/3PL, lead times
4. Be concise (under 200 words)
5. Professional but friendly tone

Write just the email body (no subject line). Use my name: {user_info.get('name', 'Business Owner')}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"""Hello {distributor['name']} Team,

I'm reaching out from {user_info.get('business_name', 'my e-commerce business')} regarding wholesale sourcing for {product['name']}.

We're currently scaling our operations and looking for reliable suppliers who can provide:
- Competitive wholesale pricing
- Flexible MOQ options
- Shipping to our prep center/3PL facility
- Consistent inventory availability

Could you please share your current pricing and terms for this product?

Best regards,
{user_info.get('name', 'Business Owner')}"""

# ===== STREAMLIT UI =====

st.title("🎯 AI-Powered Sourcing Assistant")
st.markdown("*Find profitable products, discover distributors, and automate outreach*")

# Sidebar for user info
with st.sidebar:
    st.header("Your Business Info")
    user_name = st.text_input("Your Name", "Alex Johnson")
    business_name = st.text_input("Business Name", "Prime Retail Co.")
    monthly_volume = st.text_input("Target Monthly Volume", "500-1000 units")
    your_state = st.text_input("Your Location", "California")
    
    st.markdown("---")
    st.info("💡 This demo uses AI + mock data to simulate the full sourcing workflow")

# Main input
st.header("Step 1: Enter Product Category")
category = st.text_input(
    "Product Category",
    placeholder="e.g., pet toys, wireless earbuds, vitamin supplements",
    help="Enter any product category you want to source"
)

col1, col2 = st.columns([1, 3])
with col1:
    num_products = st.number_input("Number of Products", 3, 10, 5)

# Main action button
if st.button("🔍 Find Products & Distributors", type="primary", use_container_width=True):
    if not category:
        st.warning("Please enter a product category")
    else:
        user_info = {
            "name": user_name,
            "business_name": business_name,
            "monthly_volume": monthly_volume,
            "state": your_state
        }
        
        # Step 1: Generate products
        with st.spinner("🤖 AI is analyzing market trends and generating product ideas..."):
            products = get_product_ideas(category, num_products)
            time.sleep(1)  # Simulate processing
        
        st.success(f"✅ Found {len(products)} promising products!")
        
        # Display products and distributors
        st.header("Step 2: Products & Distributors")
        
        for idx, product in enumerate(products):
            with st.expander(f"📦 {product['name']} - Profit Score: {product['profit_score']}/100", expanded=(idx==0)):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"*Description:* {product['description']}")
                    st.markdown(f"*Price Range:* {product['price']}")
                    st.markdown(f"*Demand:* {product['demand']}")
                
                with col2:
                    st.metric("Profit Score", f"{product['profit_score']}/100")
                
                # Find distributors
                st.markdown("---")
                st.subheader("🏢 Available Distributors")
                
                with st.spinner("Searching for distributors..."):
                    distributors = find_distributors(category, product['name'])
                
                if not distributors:
                    st.warning("No distributors found for this category in mock data")
                    continue
                
                for dist_idx, dist in enumerate(distributors):
                    st.markdown(f"### {dist['name']}")
                    
                    dcol1, dcol2, dcol3 = st.columns([2, 1, 1])
                    
                    with dcol1:
                        st.markdown(f"📍 *Location:* {dist['location']}")
                        st.markdown(f"🌐 *Website:* [{dist['website']}]({dist['website']})")
                        st.markdown(f"✉ *Email:* {dist['email']}")
                        if dist.get('has_3pl'):
                            st.markdown("✅ *3PL/Prep Services Available*")
                    
                    with dcol2:
                        # Verify legitimacy
                        with st.spinner("Verifying..."):
                            verification = verify_legitimacy(dist)
                        
                        score = verification['score']
                        color = "green" if score >= 75 else "orange" if score >= 50 else "red"
                        st.markdown(f"*Legitimacy Score*")
                        st.markdown(f"<h2 style='color: {color};'>{score}/100</h2>", unsafe_allow_html=True)
                        st.caption(f"Risk: {verification['risk']}")
                    
                    with dcol3:
                        if st.button(f"📧 Generate Email", key=f"email_{idx}_{dist_idx}"):
                            st.session_state[f'show_email_{idx}_{dist_idx}'] = True
                    
                    # Show verification reasoning
                    with st.container():
                        st.info(f"*Verification:* {verification['reasoning']}")
                    
                    # Show email if generated
                    if st.session_state.get(f'show_email_{idx}_{dist_idx}', False):
                        with st.spinner("🤖 AI is crafting personalized outreach email..."):
                            email = generate_outreach_email(product, dist, user_info)
                        
                        st.markdown("#### 📧 Generated Outreach Email")
                        st.text_area(
                            "Email Body",
                            email,
                            height=250,
                            key=f"email_text_{idx}_{dist_idx}"
                        )
                        
                        st.markdown(f"""
                        *To:* {dist['email']}  
                        *Subject:* Wholesale Inquiry - {product['name']}
                        """)
                        
                        if st.button("📋 Copy to Clipboard", key=f"copy_{idx}_{dist_idx}"):
                            st.success("✅ Email copied! (In production, this would use clipboard API)")
                    
                    st.markdown("---")

# Footer
st.markdown("---")
st.caption("🚀 Powered by Claude AI | Deployed on AWS | Built for rapid product s
