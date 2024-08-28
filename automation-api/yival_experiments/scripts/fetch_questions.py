from pathlib import Path

import pandas as pd

from lib.pilot.helpers import get_questions, read_ai_eval_spreadsheet

current_script_path = Path(__file__).parent


correctness_map = {1: "Correct", 2: "Wrong", 3: "Very Wrong"}


def main():
    print("Reading AI eval spreadsheet")
    sheet = read_ai_eval_spreadsheet()
    print("Getting questions")
    questions = get_questions(sheet)

    if len(questions) == 0:
        print("Empty Question set. Please double check the Questions sheet.")
        return

    output_list = []

    for q, opts in questions:
        output_item = {
            "question_id": q.question_id,
            "question_text": q.published_version_of_question.strip(),
            "language": q.language,
        }

        # sometimes option letter is missing. We will keep a list of available
        # letters for this situation.
        available_letters = ["a", "b", "c"]
        for opt in opts:
            letter = opt.letter.lower()
            if letter in available_letters:
                available_letters.remove(letter)

        for opt in opts:
            letter = opt.letter.lower()
            if letter not in ["a", "b", "c"]:
                letter = available_letters.pop(0)  # pick one available
            output_item[f"option_{letter}"] = opt.question_option
            output_item[f"option_{letter}_correctness"] = correctness_map[
                opt.correctness_of_answer_option
            ]
            if opt.correctness_of_answer_option == 1:
                output_item["correct_answer"] = opt.question_option

        # detect any null columns
        for k, v in output_item.items():
            if pd.isnull(v):
                raise ValueError(f"nan found in item: {output_item}")

        output_list.append(output_item)

    output_df = pd.DataFrame.from_records(output_list)

    # Grouping the DataFrame by 'language'
    grouped = output_df.groupby("language")

    for language, group in grouped:
        # Constructing the filename for each language
        output_file = current_script_path / f"../data/questions_{language}.csv"
        # Saving each group to a separate CSV file
        group.to_csv(output_file, index=False)
        print(f"Questions in '{language}' language saved to {output_file}")


if __name__ == "__main__":
    main()
