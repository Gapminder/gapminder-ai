import streamlit as st


def render_comparison(data1, data2):
    """Render side-by-side comparison of the data."""
    if data1.empty and data2.empty:
        st.warning("No data available for either selection.")
        return

    col1, col2 = st.columns(2)

    # Left column - Model 1
    with col1:
        if data1.empty:
            st.warning("No data available for the first selection.")
        else:
            st.subheader(f"Model: {data1['model_config_id'].iloc[0]}")

            # Show response
            st.text_area("Response", data1["response"].iloc[0], height=500, key="response1")

            # Show metrics in a more compact way
            metrics_col1, metrics_col2 = st.columns(2)

            with metrics_col1:
                st.metric("GPT-4 Correctness", data1["gpt4_correctness"].iloc[0])
                st.metric("Claude Correctness", data1["claude_correctness"].iloc[0])

            with metrics_col2:
                st.metric("Gemini Correctness", data1["gemini_correctness"].iloc[0])
                st.metric("Final Correctness", data1["final_correctness"].iloc[0])

    # Right column - Model 2
    with col2:
        if data2.empty:
            st.warning("No data available for the second selection.")
        else:
            st.subheader(f"Model: {data2['model_config_id'].iloc[0]}")

            # Show response
            st.text_area("Response", data2["response"].iloc[0], height=500, key="response2")

            # Show metrics in a more compact way
            metrics_col1, metrics_col2 = st.columns(2)

            with metrics_col1:
                st.metric("GPT-4 Correctness", data2["gpt4_correctness"].iloc[0])
                st.metric("Claude Correctness", data2["claude_correctness"].iloc[0])

            with metrics_col2:
                st.metric("Gemini Correctness", data2["gemini_correctness"].iloc[0])
                st.metric("Final Correctness", data2["final_correctness"].iloc[0])

    # Additional information
    if not data1.empty and not data2.empty:
        st.divider()
        st.subheader("Question Details")

        if "question_id" in data1.columns:
            st.write(f"**Question ID:** {data1['question_id'].iloc[0]}")

        if "prompt_variation_id" in data1.columns:
            st.write(f"**Prompt Variation ID:** {data1['prompt_variation_id'].iloc[0]}")
