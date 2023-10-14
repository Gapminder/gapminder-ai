import pandas as pd
from lib.pilot.helpers import read_ai_eval_spreadsheet, get_questions


correctness_map = {1: "Correct", 2: "Wrong", 3: "Very Wrong"}


def main():
    sheet = read_ai_eval_spreadsheet()
    questions = get_questions(sheet)

    output_list = []

    for q, opts in questions:
        output_item = {
            "question_id": q.question_id,
            "question_text": q.published_version_of_question,
            "language": q.language,
        }

        for opt in opts:
            letter = opt.letter.lower()
            output_item[f"option_{letter}"] = opt.question_option
            output_item[f"option_{letter}_correctness"] = correctness_map[
                opt.correctness_of_answer_option
            ]
            if opt.correctness_of_answer_option == 1:
                output_item["correct_answer"] = opt.question_option

        output_list.append(output_item)

    output_df = pd.DataFrame.from_records(output_list)
    output_df.to_csv("data/questions.csv", index=False)


if __name__ == "__main__":
    main()
