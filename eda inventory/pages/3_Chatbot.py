import streamlit as st
import pandas as pd
import requests

# --- Streamlit Page Config ---
st.set_page_config(layout="wide")
st.title("GenAI Inventory Assistant")

# --- Load merged_df from session ---
if "merged_df" not in st.session_state:
    st.warning("Please upload and process your data first in the Upload tab.")
    st.stop()

df = st.session_state["merged_df"]
df_sample = df.head(10).to_csv(index=False)

# --- GROQ Config ---
GROQ_API_KEY = "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"
MODEL = "llama3-70b-8192"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# --- User Input ---
st.subheader(" Ask your Inventory Question")
query = st.text_area("Enter your question:", height=100)

# --- Prompt ---
system_prompt = (
    "You are a best inventory analyst. Use the given sample inventory data (in CSV) to answer the question. "
    "Mention numbers from the data where relevant. Be concise, informative, and professional."
)

if query:
    with st.spinner("Thinking..."):
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Inventory Data Sample (CSV):\n{df_sample}\n\nQuestion: {query}"}
        ]

        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 700
        }

        response = requests.post(GROQ_URL, headers=headers, json=payload)

        if response.status_code == 200:
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            st.success(" Answer from GenAI:")
            st.markdown(answer)
        else:
            st.error(f"❌ API Error: {response.status_code}")
            st.code(response.text)
