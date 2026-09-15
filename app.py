"""Do I Actually Need This Insurance? — educational insurance breakdown tool for Germany."""

import json
import re

import requests
import streamlit as st

APP_TITLE = "Do I Actually Need This Insurance?"
MODEL = "liquid/lfm-2.5-2.6b:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🛡️",
    layout="centered",
)

CUSTOM_CSS = """
<style>
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}

.block-container {
    max-width: 720px;
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}

.app-header {
    text-align: center;
    margin-bottom: 1.75rem;
}

.app-header h1 {
    font-size: 2.1rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
    color: #1a2b3c;
}

.app-header p {
    font-size: 1.05rem;
    color: #5a6b7c;
    margin: 0;
}

.section-label {
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: #6b7684;
    margin: 1.5rem 0 0.5rem 0;
}

div[data-testid="stForm"] {
    border: 1px solid #e6e9ed;
    border-radius: 14px;
    padding: 1.75rem 1.75rem 1rem 1.75rem;
    background: #ffffff;
}

.insurance-card {
    border-radius: 10px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 0.65rem;
    border-left: 5px solid;
}

.insurance-card .item-name {
    font-weight: 600;
    font-size: 1.02rem;
    margin-bottom: 0.2rem;
}

.insurance-card .item-reason {
    font-size: 0.93rem;
    color: #4a5560;
    line-height: 1.4;
}

.card-essential {
    background: #eefaf1;
    border-left-color: #2e9e5b;
}
.card-essential .item-name { color: #1f6b3d; }

.card-considering {
    background: #fff8e8;
    border-left-color: #d99b1d;
}
.card-considering .item-name { color: #8a6110; }

.card-skippable {
    background: #f4f5f6;
    border-left-color: #9aa4ae;
}
.card-skippable .item-name { color: #5a6570; }

.category-heading {
    font-size: 1.25rem;
    font-weight: 700;
    margin: 1.75rem 0 0.75rem 0;
    color: #1a2b3c;
}

.footer-disclaimer {
    margin-top: 3rem;
    padding: 1rem 1.25rem;
    background: #f4f5f6;
    border-radius: 10px;
    font-size: 0.85rem;
    color: #6b7684;
    text-align: center;
    line-height: 1.5;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="app-header">
        <h1>🛡️ {APP_TITLE}</h1>
        <p>An unbiased, personalized breakdown of the insurance you actually need in Germany
        — no commission, no sales pitch.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def extract_json(raw_text: str):
    text = raw_text.strip()
    fence_match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    brace_match = re.search(r"\{.*\}", text, re.DOTALL)
    if brace_match:
        return json.loads(brace_match.group(0))
    raise ValueError("No JSON object found in model response.")


def call_openrouter(user_prompt: str) -> dict:
    api_key = st.secrets.get("OPENROUTER_API_KEY", "")
    system_prompt = st.secrets.get("SYSTEM_PROMPT", "")
    if not api_key or not system_prompt:
        raise RuntimeError("Missing required app secrets.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }

    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]

    try:
        return extract_json(content)
    except (ValueError, json.JSONDecodeError):
        repair_payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        "That was not valid JSON. Respond again with ONLY the valid JSON object "
                        "matching the schema — no markdown, no extra text."
                    ),
                },
            ],
            "temperature": 0.1,
        }
        retry_response = requests.post(
            OPENROUTER_URL, headers=headers, json=repair_payload, timeout=60
        )
        retry_response.raise_for_status()
        retry_content = retry_response.json()["choices"][0]["message"]["content"]
        return extract_json(retry_content)


def build_user_prompt(answers: dict) -> str:
    prompt = (
        f"Housing situation: {answers['housing']}\n"
        f"Employment: {answers['employment']}\n"
        f"Family situation: {answers['family']}\n"
        f"Owns a car: {'Yes' if answers['car'] else 'No'}\n"
        f"Owns a dog: {'Yes' if answers['dog'] else 'No'}\n"
        f"Owns notable valuables (electronics/jewelry/furniture): "
        f"{'Yes' if answers['valuables'] else 'No'}\n"
        f"Has a mortgage or major loan: {'Yes' if answers['loan'] else 'No'}\n"
        f"Risk tolerance: {answers['risk']}\n"
    )

    if answers.get("travel") and answers["travel"] != "Rarely or never":
        prompt += f"Travel frequency: {answers['travel']}\n"
    if answers.get("equity"):
        prompt += "Invests in stocks, ETFs, or other equity beyond a pension: Yes\n"
    if answers.get("premium_card"):
        prompt += "Holds a premium credit card with built-in travel/purchase protection: Yes\n"
    if answers.get("sends_money_abroad"):
        prompt += "Regularly sends money to or financially supports family abroad: Yes\n"

    return prompt


def dedupe_categories(essential: list, considering: list, skippable: list):
    seen = set()
    deduped = []
    for items in (essential, considering, skippable):
        kept = []
        for item in items:
            key = item.get("name", "").strip().lower()
            if key and key in seen:
                continue
            seen.add(key)
            kept.append(item)
        deduped.append(kept)
    return deduped


def render_category(title: str, icon: str, items: list, css_class: str):
    st.markdown(f'<div class="category-heading">{icon} {title}</div>', unsafe_allow_html=True)
    if not items:
        st.markdown(
            f'<div class="insurance-card {css_class}">'
            f'<div class="item-reason">Nothing in this category for your situation.</div></div>',
            unsafe_allow_html=True,
        )
        return
    for item in items:
        name = item.get("name", "").strip()
        reason = item.get("reason", "").strip()
        st.markdown(
            f'<div class="insurance-card {css_class}">'
            f'<div class="item-name">{name}</div>'
            f'<div class="item-reason">{reason}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )


with st.form("insurance_form"):
    st.markdown('<div class="section-label">Housing & Work</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        housing = st.selectbox("Housing situation", ["Renter", "Homeowner"])
    with col2:
        employment = st.selectbox(
            "Employment",
            ["Employed", "Self-employed / Freelancer", "Student", "Unemployed / Job-seeking"],
        )

    st.markdown('<div class="section-label">Family</div>', unsafe_allow_html=True)
    family = st.selectbox(
        "Family situation",
        [
            "Single, no dependents",
            "Married or partnered, no kids",
            "Have kids or other dependents",
            "Single parent",
        ],
    )

    st.markdown('<div class="section-label">What You Own</div>', unsafe_allow_html=True)
    col3, col4, col5 = st.columns(3)
    with col3:
        car = st.checkbox("🚗 Owns a car")
    with col4:
        dog = st.checkbox("🐕 Owns a dog")
    with col5:
        valuables = st.checkbox("💍 Notable valuables")
    loan = st.checkbox("🏦 Has a mortgage or major loan")

    st.markdown('<div class="section-label">Risk Tolerance</div>', unsafe_allow_html=True)
    risk = st.select_slider("How much financial risk are you comfortable carrying yourself?",
                             options=["Low", "Medium", "High"], value="Medium")

    with st.expander("🔍 A few more details (optional — sharpens your breakdown)"):
        travel = st.selectbox(
            "How often do you travel?",
            [
                "Rarely or never",
                "A few trips per year (mostly within Europe)",
                "Frequent traveler / long trips outside Europe",
            ],
        )
        col6, col7, col8 = st.columns(3)
        with col6:
            equity = st.checkbox("📈 Invests in stocks/ETFs")
        with col7:
            premium_card = st.checkbox("💳 Premium travel card")
        with col8:
            sends_money_abroad = st.checkbox("🌍 Supports family abroad")

    submitted = st.form_submit_button(
        "Get my breakdown", use_container_width=True, type="primary"
    )

if submitted:
    answers = {
        "housing": housing,
        "employment": employment,
        "family": family,
        "car": car,
        "dog": dog,
        "valuables": valuables,
        "loan": loan,
        "risk": risk,
        "travel": travel,
        "equity": equity,
        "premium_card": premium_card,
        "sends_money_abroad": sends_money_abroad,
    }
    user_prompt = build_user_prompt(answers)

    with st.spinner("Analyzing your situation — this usually takes 10-30 seconds..."):
        try:
            result = call_openrouter(user_prompt)
            essential, considering, skippable = dedupe_categories(
                result.get("essential", []),
                result.get("worth_considering", []),
                result.get("usually_skippable", []),
            )
        except requests.exceptions.RequestException:
            st.error(
                "We couldn't reach the AI service right now. Please try again in a moment."
            )
            result = None
        except (ValueError, KeyError, json.JSONDecodeError):
            st.error(
                "We got an unexpected response while preparing your breakdown. "
                "Please try submitting again."
            )
            result = None
        except RuntimeError:
            st.error(
                "This app isn't fully configured yet. "
                "Please contact the site owner."
            )
            result = None

    if result:
        st.divider()
        render_category("Essential", "✅", essential, "card-essential")
        render_category("Worth Considering", "🤔", considering, "card-considering")
        render_category("Usually Skippable", "⏭️", skippable, "card-skippable")

st.markdown(
    """
    <div class="footer-disclaimer">
        Educational tool only — not licensed financial or insurance advice.
        For major decisions, consult a fee-only (Honorarberater) advisor.
    </div>
    """,
    unsafe_allow_html=True,
)
