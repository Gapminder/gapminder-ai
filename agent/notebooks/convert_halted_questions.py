import pandas as pd
import re

def clean_option_text(option_text):
    """Removes leading option markers like 'A. ', 'B. ' etc."""
    # Regex to find patterns like "A. ", "B. ", "1. ", "a) "
    cleaned_text = re.sub(r'^[A-Za-z0-9][\.\)]\s+', '', option_text.strip())
    return cleaned_text.strip()


def split_options(options_text):
    if ',' not in options_text:
        res = options_text.split("\n")
    else:
        step1 = options_text.replace("\n", "")
        res = step1.split(',')

    return [x.strip() for x in res]


def main():
    # Define input and output paths
    input_csv_path = 'halted_questions.csv'
    output_dir = './'
    output_questions_path = output_dir + 'questions.csv'
    output_options_path = output_dir + 'question_options.csv'

    try:
        # Read the input CSV. Attempt to find the correct header row.
        # The CSV has multiple initial rows that are not the true header.
        # We'll look for a row that contains expected column names.
        df_full = pd.read_csv(input_csv_path, dtype=str)
        df_full.columns = df_full.columns.map(lambda x: x.strip().replace("\n", " "))

        expected_cols = ['Question', 'Correct Answer', 'Answer options']

        # Drop rows where essential information for questions or options is missing
        # or where ID combo is a placeholder like '#REF!'
        df_input = df_full.dropna(subset=expected_cols)[expected_cols]
        if not df_input[df_input.duplicated(subset=["Question"])].empty:
            print(df_input[df_input.duplicated(subset=["Question"])])
            raise ValueError("Duplicated question")

        questions_data = []
        options_data = []

        processed_question_ids = set()

        for index, row in df_input.iterrows():
            question_id_raw = str(index)

            # Safely extract question text, handling cases where it might be a Series
            raw_question_val = row['Question']
            if isinstance(raw_question_val, pd.Series):
                actual_question_string = raw_question_val.iloc[0]
            else:
                actual_question_string = raw_question_val
            question_text = str(actual_question_string).strip().title()

            correct_answer_text_raw = str(row.get('Correct Answer', '')).strip().title()
            answer_options_str = str(row.get('Answer options', '')).strip()

            if not question_id_raw or not question_text:
                print(f"Skipping row {index} due to missing ID combo or Question text.")
                continue

            # Ensure unique question_id for questions.csv
            if question_id_raw not in processed_question_ids:
                questions_data.append({
                    'question_id': question_id_raw,
                    'language': 'en-US',
                    'published_version_of_question': question_text
                })
                processed_question_ids.add(question_id_raw)

            # Process options
            # Split options, then clean them
            parsed_options = [clean_option_text(opt) for opt in split_options(answer_options_str)]

            # Clean the correct answer text as well, in case it has markers
            correct_answer_text_cleaned = clean_option_text(correct_answer_text_raw)

            if not parsed_options:
                print(f"Warning: No options found for QID {question_id_raw} after parsing '{answer_options_str}'. Skipping options for this question.")
                continue

            if len(parsed_options) != 3:
                # print(f"Warning: Question QID {question_id_raw} has {len(parsed_options)} options, expected 3. Options: {parsed_options}")
                print(f"- AB{index+2}")

            option_letter_map = {i: chr(65 + i) for i in range(len(parsed_options))} # A, B, C...

            correct_option_found_in_list = False
            temp_options_details = []

            for i, opt_text_cleaned in enumerate(parsed_options):
                is_correct = (opt_text_cleaned.lower() == correct_answer_text_cleaned.lower())
                if is_correct:
                    correct_option_found_in_list = True
                temp_options_details.append({'text': opt_text_cleaned, 'is_correct': is_correct, 'original_order': i})

            if not correct_option_found_in_list:
                # Check if the raw correct answer text (before cleaning) matches any raw parsed option
                raw_parsed_options = split_options(answer_options_str)
                for i, raw_opt_text in enumerate(raw_parsed_options):
                    if raw_opt_text.lower() == correct_answer_text_raw.lower():
                         # Mark the corresponding cleaned option as correct
                        if i < len(temp_options_details):
                            temp_options_details[i]['is_correct'] = True
                            correct_option_found_in_list = True
                            print(f"Info: Correct answer for QID {question_id_raw} matched using raw text after initial cleaned mismatch: '{correct_answer_text_raw}'")
                        break

            if not correct_option_found_in_list:
                # print(f"Warning: Correct answer text '{correct_answer_text_raw}' (cleaned: '{correct_answer_text_cleaned}') "
                #       f"not found in parsed options '{parsed_options}' for QID {question_id_raw}. "
                #       f"Correctness for options might be inaccurate.")
                # print(f"- AB{index+2}")
                pass


            current_incorrect_rank = 2 # Start ranking incorrect options from 2

            has_assigned_correct_rank_1 = False

            for i, opt_detail in enumerate(temp_options_details):
                letter = option_letter_map[i] # This is 'A', 'B', 'C', etc.
                # New format for question_option_id: {id}-a1, {id}-a2, etc.
                question_option_id = f"{question_id_raw}-a{i+1}"

                correctness_value = 0 # Default for unassigned/error
                if opt_detail['is_correct']:
                    if not has_assigned_correct_rank_1: # Ensure only one option gets rank 1
                        correctness_value = 1
                        has_assigned_correct_rank_1 = True
                    else: # Multiple options marked as correct, this is an issue. Assign subsequent incorrect rank.
                        print(f"Warning: Multiple options marked as correct for QID {question_id_raw}. Option '{opt_detail['text']}' will be ranked as incorrect.")
                        correctness_value = current_incorrect_rank
                        current_incorrect_rank += 1
                else:
                    correctness_value = current_incorrect_rank
                    current_incorrect_rank += 1

                options_data.append({
                    'question_option_id': question_option_id,
                    'question_id': question_id_raw,
                    'language': 'en-US',
                    'letter': letter,
                    'question_option': opt_detail['text'],
                    'correctness_of_answer_option': correctness_value
                })

        # Create DataFrames
        df_questions_output = pd.DataFrame(questions_data)
        df_options_output = pd.DataFrame(options_data)

        # Save to CSV
        df_questions_output.to_csv(output_questions_path, index=False)
        print(f"Successfully created {output_questions_path} with {len(df_questions_output)} questions.")

        df_options_output.to_csv(output_options_path, index=False)
        print(f"Successfully created {output_options_path} with {len(df_options_output)} options.")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_csv_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
