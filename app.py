import os, json, re, difflib, time
from pathlib import Path

import streamlit as st

APP_TITLE = "Customer Support Chatbot"
GREETING = "Hi! 👋 I’m your support assistant. How can I help you today?"
FALLBACK = "Sorry, I’m not sure about that. Could you rephrase? You can ask about orders, returns, refunds, payments, offers, and more."

def load_faq(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize(text: str):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [t for t in text.split() if t]
    return tokens

def jaccard(a_tokens, b_tokens):
    a, b = set(a_tokens), set(b_tokens)
    if not a and not b: return 0.0
    return len(a & b) / max(1, len(a | b))

def score(query: str, candidate: str):
    a = normalize(query); b = normalize(candidate)
    j = jaccard(a, b)
    s = difflib.SequenceMatcher(None, " ".join(a), " ".join(b)).ratio()
    # Weighted blend
    return 0.6 * j + 0.4 * s

def best_match(query: str, faq_items):
    best = (None, 0.0, None)  # (answer, score, matched_question)
    for item in faq_items:
        candidates = [item["question"]] + item.get("alternates", [])
        for c in candidates:
            sc = score(query, c)
            if sc > best[1]:
                best = (item["answer"], sc, c)
    return best

def try_openai_fallback(prompt: str):
    # Optional: if user has OPENAI_API_KEY and 'openai' installed, use it for smarter fallback
    try:
        import openai  # type: ignore
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return None
        openai.api_key = api_key
        # Lightweight call; user may edit model as needed
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful e-commerce support assistant. Be concise and friendly."},
                      {"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        return completion["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="💬", layout="centered")
    st.title(APP_TITLE)

    # Load FAQ
    faq_path = Path(__file__).with_name("faq.json")
    faq_items = load_faq(faq_path)

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": GREETING}]

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    user_input = st.chat_input("Type your question...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        answer, sc, matched = best_match(user_input, faq_items)
        threshold = 0.45  # tune as needed
        if sc >= threshold:
            bot_reply = answer
        else:
            # Optional OpenAI fallback
            ai_reply = try_openai_fallback(user_input)
            bot_reply = ai_reply if ai_reply else FALLBACK

        with st.chat_message("assistant"):
            st.markdown(bot_reply)
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

    with st.expander("ℹ️ About this bot"):
        st.write("""
- Answers common customer support questions using a small FAQ knowledge base.
- If it can't find a good match, it shows a smart fallback. Optionally, set `OPENAI_API_KEY` to enable AI fallback.
- Customize by editing `faq.json` (add more questions, alternates, and answers).
- Deploy locally: `pip install streamlit` then run `streamlit run app.py`.
        """)

if __name__ == "__main__":
    main()
