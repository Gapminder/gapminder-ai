import streamlit as st
import random
from data_loader import load_parquet_data
from comparison_utils import get_comparison_data
from components.filters import render_filters
from components.comparison_view import render_comparison

st.set_page_config(page_title="Parquet Data Comparison", page_icon="📊", layout="wide")

# Add custom CSS
try:
    with open("styles/main.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass  # CSS file is optional

st.title("Model Response Comparison Tool")

# File uploader for parquet file
uploaded_file = st.file_uploader("Upload Parquet File", type=["parquet"])

if uploaded_file is not None:
    # Load data
    df = load_parquet_data(uploaded_file)

    # Initialize question navigation index in session state
    if "question_index" not in st.session_state:
        st.session_state["question_index"] = 0

    # Initialize prompt variation in session state if not present
    if "current_prompt_variation" not in st.session_state:
        st.session_state["current_prompt_variation"] = 0

    # Get sorted question IDs for navigation
    question_ids = sorted(df["question_id"].unique())

    # Random question selection function
    def select_random_question():
        if len(question_ids) > 0:
            st.session_state["question_index"] = random.randint(0, len(question_ids) - 1)
            # Reset the prompt variation when changing questions
            st.session_state["current_prompt_variation"] = None
            st.rerun()

    # Ensure question index is valid
    if len(question_ids) > 0:
        if st.session_state["question_index"] >= len(question_ids):
            st.session_state["question_index"] = len(question_ids) - 1
        elif st.session_state["question_index"] < 0:
            st.session_state["question_index"] = 0

        # Get current question from index
        current_question = question_ids[st.session_state["question_index"]]
    else:
        current_question = None

    # Get the current prompt variation
    current_prompt_variation = st.session_state["current_prompt_variation"]

    # Render filters with the current question and prompt variation
    model_config_id1, model_config_id2, question_id, prompt_variation_id = render_filters(
        df, current_question, current_prompt_variation
    )

    # Update the current prompt variation in session state
    st.session_state["current_prompt_variation"] = prompt_variation_id

    # Get comparison data
    data1, data2 = get_comparison_data(df, model_config_id1, model_config_id2, question_id, prompt_variation_id)

    # Show comparison
    render_comparison(data1, data2)

    # Navigation for browsing through questions
    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Previous Question") and st.session_state["question_index"] > 0:
            st.session_state["question_index"] -= 1
            # Reset the prompt variation when changing questions
            st.session_state["current_prompt_variation"] = None
            st.rerun()

    with col2:
        st.button("Random Question", on_click=select_random_question)

    with col3:
        if st.button("Next Question") and st.session_state["question_index"] < len(question_ids) - 1:
            st.session_state["question_index"] += 1
            # Reset the prompt variation when changing questions
            st.session_state["current_prompt_variation"] = None
            st.rerun()

    # Show navigation status
    st.caption(f"Viewing question {st.session_state['question_index'] + 1} of {len(question_ids)}")
else:
    st.info("Please upload a parquet file to begin.")
