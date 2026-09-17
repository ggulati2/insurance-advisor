"""Do I Actually Need This Insurance? — educational insurance breakdown tool for Germany."""

import json
import re

import requests
import streamlit as st

APP_TITLE = "Do I Actually Need This Insurance?"
MODEL = "liquid/lfm-2.5-2.6b:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

CATEGORY_META = {
    "essential": {"label": "Essential", "icon": "✅", "css": "card-essential"},
    "situational": {"label": "Situational", "icon": "🤔", "css": "card-considering"},
    "skippable": {"label": "Often Skippable", "icon": "⏭️", "css": "card-skippable"},
}

GUIDE_ENTRIES = [
    {
        "category": "essential", "icon": "🛟",
        "name": "Private liability insurance", "name_de": "Privathaftpflichtversicherung",
        "blurb": (
            "If you accidentally break, damage, or injure something or someone else — a "
            "shattered vase at a friend's, a cyclist you bump into — this covers the cost of "
            "the claim. It's one of the cheapest policies you can buy relative to how much "
            "financial risk it removes, which is why it's treated as close to essential for "
            "almost everyone in Germany."
        ),
    },
    {
        "category": "situational", "icon": "💼",
        "name": "Occupational disability insurance", "name_de": "Berufsunfähigkeitsversicherung",
        "blurb": (
            "Replaces a portion of your income if illness or injury permanently stops you from "
            "working in your profession. Most valuable for people whose income depends on their "
            "own ability to work and who have a family, rent, or a mortgage relying on that income."
        ),
    },
    {
        "category": "situational", "icon": "📦",
        "name": "Household contents insurance", "name_de": "Hausratversicherung",
        "blurb": (
            "Covers your belongings inside your home — furniture, electronics, clothing — "
            "against fire, theft, and water damage. Matters most if you own things that would "
            "be expensive to replace all at once."
        ),
    },
    {
        "category": "situational", "icon": "🏠",
        "name": "Building insurance", "name_de": "Wohngebäudeversicherung",
        "blurb": (
            "Protects the physical structure of a building against fire, storm, and water "
            "damage. Only relevant if you own the building itself, and effectively required by "
            "most mortgage lenders."
        ),
    },
    {
        "category": "situational", "icon": "🐕",
        "name": "Dog liability insurance", "name_de": "Hundehaftpflichtversicherung",
        "blurb": (
            "A liability policy specifically for damage your dog causes — a torn coat, a "
            "bitten mail carrier, a knocked-over child. Standard private liability policies "
            "usually exclude dogs, and several German states legally require this."
        ),
    },
    {
        "category": "situational", "icon": "⚖️",
        "name": "Legal protection insurance", "name_de": "Rechtsschutzversicherung",
        "blurb": (
            "Covers legal fees when you end up in a dispute — with an employer, a landlord, or "
            "over a contract. More useful the more contracts and relationships you have "
            "exposure through (a lease, a job, a car)."
        ),
    },
    {
        "category": "situational", "icon": "❤️",
        "name": "Term life insurance", "name_de": "Risikolebensversicherung",
        "blurb": (
            "Pays a lump sum to whoever you name if you die during the policy term. It exists "
            "for the people who depend on your income — a partner, children, or a joint "
            "mortgage — not for you."
        ),
    },
    {
        "category": "situational", "icon": "🚗",
        "name": "Car liability insurance", "name_de": "KFZ-Haftpflichtversicherung",
        "blurb": (
            "The liability portion of car insurance, and the only part that's legally required "
            "to register or drive a car in Germany. If you don't own or drive a car, it's "
            "simply not applicable."
        ),
    },
    {
        "category": "situational", "icon": "✈️",
        "name": "Foreign travel health insurance", "name_de": "Auslandskrankenversicherung",
        "blurb": (
            "German statutory health insurance often doesn't reliably cover you once you're "
            "outside the EU/EEA, and can be limited even within Europe. This is a cheap add-on "
            "that closes that gap whenever you travel."
        ),
    },
    {
        "category": "situational", "icon": "🧳",
        "name": "Trip cancellation insurance", "name_de": "Reiserücktrittsversicherung",
        "blurb": (
            "Reimburses non-refundable trip costs if you have to cancel or cut a trip short — "
            "illness, a family emergency, and similar disruptions. Worth it mainly if you book "
            "expensive, non-refundable travel."
        ),
    },
    {
        "category": "skippable", "icon": "📱",
        "name": "Phone insurance", "name_de": "Handyversicherung",
        "blurb": (
            "Insures your smartphone against damage or theft. It's frequently oversold relative "
            "to what it actually pays out, and often duplicates protection you already have "
            "through a bank card or manufacturer warranty."
        ),
    },
    {
        "category": "skippable", "icon": "🎒",
        "name": "Luggage insurance", "name_de": "Reisegepäckversicherung",
        "blurb": (
            "Covers lost or damaged luggage while traveling. The coverage is narrow and payouts "
            "are rare enough that most travelers get little practical value from it."
        ),
    },
    {
        "category": "skippable", "icon": "🕯️",
        "name": "Whole life / funeral insurance",
        "name_de": "Kapitallebensversicherung / Sterbegeldversicherung",
        "blurb": (
            "A life insurance policy bundled with a savings component, sometimes marketed as "
            "covering funeral costs. As an investment vehicle it performs poorly compared to "
            "just investing directly, and a funeral is usually cheaper to plan for directly."
        ),
    },
    {
        "category": "skippable", "icon": "🩹",
        "name": "Private accident insurance", "name_de": "Private Unfallversicherung",
        "blurb": (
            "Pays out for injuries from accidents, on top of whatever statutory or occupational "
            "disability coverage already applies. For most people it overlaps heavily with "
            "coverage they already have elsewhere."
        ),
    },
    {
        "category": "skippable", "icon": "🪟",
        "name": "Glass insurance", "name_de": "Glasversicherung",
        "blurb": (
            "Covers breakage of windows, mirrors, and glass fixtures in your home. It's a "
            "narrow risk that's usually inexpensive to fix out of pocket, so the policy rarely "
            "pays for itself."
        ),
    },
]

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🛡️",
    layout="centered",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --brand: #4F46E5;
    --brand-dark: #4338CA;
    --brand-tint: rgba(79, 70, 229, 0.08);
    --ink: #14151a;
    --ink-soft: #5b5f73;
    --ink-faint: #8a8fa3;
    --border: #e6e7eb;
    --surface: #ffffff;
    --surface-subtle: #f6f6f9;
    --radius-lg: 16px;
    --radius-md: 12px;
    --radius-sm: 8px;
    --shadow-sm: 0 1px 2px rgba(16, 24, 40, 0.04);
    --shadow-md: 0 4px 14px rgba(16, 24, 40, 0.07), 0 1px 2px rgba(16, 24, 40, 0.04);
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    color: var(--ink);
}

#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

.block-container {
    max-width: 760px;
    padding-top: 2.25rem;
    padding-bottom: 3rem;
}

.app-header { text-align: center; margin-bottom: 2rem; }

.eyebrow {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    color: var(--brand);
    background: var(--brand-tint);
    padding: 0.32rem 0.85rem;
    border-radius: 999px;
    margin-bottom: 1rem;
}

.app-header h1 {
    font-size: 2.15rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    margin: 0 0 0.5rem 0;
    color: var(--ink);
}

.app-header p {
    font-size: 1.05rem;
    color: var(--ink-soft);
    margin: 0;
    line-height: 1.5;
}

.tab-intro {
    color: var(--ink-soft);
    font-size: 0.96rem;
    line-height: 1.55;
    margin: 0.25rem 0 1.4rem 0;
}

/* Tabs — segmented-control look */
[data-testid="stTabs"] [role="tablist"] {
    gap: 4px;
    background: var(--surface-subtle);
    padding: 5px;
    border-radius: var(--radius-md);
    border-bottom: none;
}
[data-testid="stTab"] {
    height: 40px;
    border-radius: var(--radius-sm);
    padding: 0 16px;
    color: var(--ink-soft);
    font-weight: 500;
    font-size: 0.92rem;
}
[data-testid="stTab"][aria-selected="true"] {
    background: var(--surface);
    color: var(--ink);
    box-shadow: var(--shadow-sm);
}
[data-testid="stTabs"] .react-aria-SelectionIndicator { display: none; }

@media (max-width: 480px) {
    [data-testid="stTab"] { padding: 0 10px; font-size: 0.85rem; }
}

div[data-testid="stForm"] {
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.75rem 1.75rem 1.1rem 1.75rem;
    background: var(--surface);
    box-shadow: var(--shadow-md);
}

.section-label {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--ink-faint);
    margin: 1.5rem 0 0.6rem 0;
}

.stButton button, .stFormSubmitButton button {
    border-radius: var(--radius-sm);
    font-weight: 600;
    transition: transform 0.05s ease, box-shadow 0.15s ease;
}
.stFormSubmitButton button[kind="primary"] {
    box-shadow: var(--shadow-sm);
}
.stFormSubmitButton button[kind="primary"]:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-1px);
}

.insurance-card {
    border: 1px solid rgba(16, 24, 40, 0.05);
    border-radius: var(--radius-md);
    padding: 1rem 1.15rem;
    margin-bottom: 0.7rem;
    border-left: 4px solid;
    box-shadow: var(--shadow-sm);
    transition: transform 0.12s ease, box-shadow 0.15s ease;
}
.insurance-card:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md);
}

.insurance-card .item-name {
    font-weight: 600;
    font-size: 1.02rem;
    margin-bottom: 0.25rem;
}
.insurance-card .item-name-de {
    font-weight: 400;
    font-size: 0.86em;
    color: var(--ink-faint);
}

.insurance-card .item-reason {
    font-size: 0.93rem;
    color: var(--ink-soft);
    line-height: 1.5;
}

.card-essential { background: #eefaf1; border-left-color: #2e9e5b; }
.card-essential .item-name { color: #1f6b3d; }

.card-considering { background: #fff8e8; border-left-color: #d99b1d; }
.card-considering .item-name { color: #8a6110; }

.card-skippable { background: #f4f5f6; border-left-color: #9aa4ae; }
.card-skippable .item-name { color: #5a6570; }

.category-heading {
    font-size: 1.2rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    margin: 1.9rem 0 0.8rem 0;
    color: var(--ink);
}

.footer-disclaimer {
    margin-top: 2.5rem;
    padding: 1rem 1.25rem;
    background: var(--surface-subtle);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    font-size: 0.83rem;
    color: var(--ink-faint);
    text-align: center;
    line-height: 1.55;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="app-header">
        <span class="eyebrow">🇩🇪 For Germany · Educational, not advice</span>
        <h1>🛡️ {APP_TITLE}</h1>
        <p>An unbiased, personalized breakdown of the insurance you actually need
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


def _post_chat_completion(messages: list, temperature: float = 0.3) -> str:
    api_key = st.secrets.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("Missing required app secrets.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"model": MODEL, "messages": messages, "temperature": temperature}
    response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def call_breakdown(user_prompt: str) -> dict:
    system_prompt = st.secrets.get("SYSTEM_PROMPT", "")
    if not system_prompt:
        raise RuntimeError("Missing required app secrets.")

    content = _post_chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    try:
        return extract_json(content)
    except (ValueError, json.JSONDecodeError):
        retry_content = _post_chat_completion(
            [
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
            temperature=0.1,
        )
        return extract_json(retry_content)


def call_chat(chat_history: list) -> str:
    chatbot_prompt = st.secrets.get("CHATBOT_SYSTEM_PROMPT", "")
    if not chatbot_prompt:
        raise RuntimeError("Missing required app secrets.")
    messages = [{"role": "system", "content": chatbot_prompt}] + chat_history
    return _post_chat_completion(messages, temperature=0.4)


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


def render_guide():
    st.markdown(
        '<p class="tab-intro">A quick reference for the insurance types your breakdown draws '
        "on, grouped by how relevant they typically are for most people in Germany. Your "
        "personal result may vary based on your situation.</p>",
        unsafe_allow_html=True,
    )
    for cat_key in ("essential", "situational", "skippable"):
        meta = CATEGORY_META[cat_key]
        entries = [e for e in GUIDE_ENTRIES if e["category"] == cat_key]
        st.markdown(
            f'<div class="category-heading">{meta["icon"]} {meta["label"]}</div>',
            unsafe_allow_html=True,
        )
        for entry in entries:
            st.markdown(
                f'<div class="insurance-card {meta["css"]}">'
                f'<div class="item-name">{entry["icon"]} {entry["name"]} '
                f'<span class="item-name-de">({entry["name_de"]})</span></div>'
                f'<div class="item-reason">{entry["blurb"]}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )


def render_breakdown_tab():
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
        risk = st.select_slider(
            "How much financial risk are you comfortable carrying yourself?",
            options=["Low", "Medium", "High"], value="Medium",
        )

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
                result = call_breakdown(user_prompt)
                essential, considering, skippable = dedupe_categories(
                    result.get("essential", []),
                    result.get("worth_considering", []),
                    result.get("usually_skippable", []),
                )
            except requests.exceptions.RequestException:
                st.error("We couldn't reach the AI service right now. Please try again in a moment.")
                result = None
            except (ValueError, KeyError, json.JSONDecodeError):
                st.error(
                    "We got an unexpected response while preparing your breakdown. "
                    "Please try submitting again."
                )
                result = None
            except RuntimeError:
                st.error("This app isn't fully configured yet. Please contact the site owner.")
                result = None

        if result:
            st.divider()
            render_category("Essential", "✅", essential, "card-essential")
            render_category("Worth Considering", "🤔", considering, "card-considering")
            render_category("Usually Skippable", "⏭️", skippable, "card-skippable")


def render_chat_tab():
    st.markdown(
        '<p class="tab-intro">Ask anything about German personal insurance — coverage, '
        "typical cost, whether something applies to you. Educational only, not personalized "
        "advice.</p>",
        unsafe_allow_html=True,
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.session_state.chat_history:
        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    question = st.chat_input("e.g. Do I need Hausratversicherung as a renter?")
    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    reply = call_chat(st.session_state.chat_history)
                except requests.exceptions.RequestException:
                    st.error("We couldn't reach the AI service right now. Please try again in a moment.")
                    reply = None
                except RuntimeError:
                    st.error("This app isn't fully configured yet. Please contact the site owner.")
                    reply = None

            if reply:
                st.markdown(reply)
                st.session_state.chat_history.append({"role": "assistant", "content": reply})


tab_breakdown, tab_guide, tab_chat = st.tabs(
    ["🛡️ Get My Breakdown", "📖 Insurance Guide", "💬 Ask a Question"]
)

with tab_breakdown:
    render_breakdown_tab()

with tab_guide:
    render_guide()

with tab_chat:
    render_chat_tab()

st.markdown(
    """
    <div class="footer-disclaimer">
        Educational tool only — not licensed financial or insurance advice.
        For major decisions, consult a fee-only (Honorarberater) advisor.
    </div>
    """,
    unsafe_allow_html=True,
)
