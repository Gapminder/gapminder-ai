# example data for testing evaluators. the main function in gpt4_evaluator.py and other evaluators require this file

import pandas as pd

example_question_id = "1737"
example_question_lang = "en"  # 'cn' or 'en'

raw_output = """Understanding public perception of climate change is crucial for railway workers because it can influence policy decisions, funding, and the future direction of infrastructure projects. If a significant portion of the population views climate change as a threat, there may be increased investment in sustainable and resilient railway systems. This could lead to job security, new training opportunities, and the adoption of innovative technologies within the railway industry.

The correct answer is:
C. Around 80%

Simple phrasing for railway workers:
\"About 80% of people in high-income countries see climate change as a threat to their country over the next 20 years.\""""

en_question_file = "../data/questions_en-US.csv"
cn_question_file = "../data/questions_zh-CN.csv"

prompt = """You are assessing a submitted answer on a given task based on a criterion. Here is the data:
- Task: Answer a question.
- Is the answer correct?
[Input]: {question_text}
Possible Options and Correctness of Options:
A. {option_a} ({option_a_correctness})
B. {option_b} ({option_b_correctness})
C. {option_c} ({option_c_correctness})
[Result]: {raw_output}
Assess the answer by selecting one of the following options. Please note that the question was asked in some context so the answer would contain some more contextual information. You should conclude which option this answer has chosen.
A The answer looks like some kind of exception / error message; or it's an equivocal answer; or it doesn't answer to the question at all.
B The answer is not correct, and matches/is close to the Very Wrong answer.
C The answer is not correct, and matches/is close to the Wrong answer.
D The answer is correct, i.e. matches the Correct answer."""

choices = ["A", "B", "C", "D"]

choice_scores = dict(zip(choices, [0, 1, 2, 3]))


def get_example_input(question_id, lang):
    if lang == "en":
        df = pd.read_csv(en_question_file, dtype="str")
    else:
        df = pd.read_csv(cn_question_file, dtype="str")

    question_data = df.loc[df["question_id"] == question_id]
    return question_data.iloc[0].to_dict()


# print(get_example_input(example_question_id, example_question_lang))
content = get_example_input(example_question_id, example_question_lang)
