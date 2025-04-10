import streamlit as st
import random


def render_filters(df, current_question=None, current_prompt_variation=None):
    """Render filter selection UI components."""
    col1, col2 = st.columns(2)

    # Get unique values for filters
    model_config_ids = sorted(df["model_config_id"].unique())
    question_ids = sorted(df["question_id"].unique())

    # Initialize model selections if not already set
    if "model_config_id1" not in st.session_state and model_config_ids:
        st.session_state["model_config_id1"] = model_config_ids[0]

    if "model_config_id2" not in st.session_state and model_config_ids:
        st.session_state["model_config_id2"] = model_config_ids[1] if len(model_config_ids) > 1 else model_config_ids[0]

    # Model selection
    with col1:
        st.subheader("Model 1")
        model_config_id1 = st.selectbox(
            "Select Model Config ID (Left)",
            options=model_config_ids,
            key="model_config_id1",
        )

    with col2:
        st.subheader("Model 2")
        model_config_id2 = st.selectbox(
            "Select Model Config ID (Right)",
            options=model_config_ids,
            key="model_config_id2",
        )

    # Question selection
    default_question = current_question if current_question else (question_ids[0] if question_ids else None)
    question_index = question_ids.index(default_question) if default_question in question_ids else 0

    question_id = st.selectbox(
        "Select Question ID",
        options=question_ids,
        index=question_index,
        key="question_selector",
    )

    # Update question index in session state when manual selection changes
    if question_id != default_question and question_id in question_ids:
        st.session_state["question_index"] = question_ids.index(question_id)

    # Get prompt variations for the selected question
    prompt_variations = (
        sorted(df[df["question_id"] == question_id]["prompt_variation_id"].unique()) if question_id else []
    )

    # Determine prompt variation index
    prompt_variation_index = (
        prompt_variations.index(current_prompt_variation) if current_prompt_variation in prompt_variations else 0
    )

    # Prompt variation selection and random button
    col1, col2 = st.columns([3, 1])

    with col1:
        prompt_variation_id = (
            st.selectbox(
                "Select Prompt Variation ID",
                options=prompt_variations,
                index=prompt_variation_index,
                key="prompt_variation_selector",
            )
            if prompt_variations
            else None
        )

    with col2:
        st.write("")  # Add some spacing
        st.write("")  # Add some spacing
        if st.button("Random Prompt", key="random_prompt_btn") and prompt_variations:
            prompt_variation_id = random.choice(prompt_variations)

    return model_config_id1, model_config_id2, question_id, prompt_variation_id
