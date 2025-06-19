"""
The script converts halted unpublished questions into a format suitable for gm-eval to read.

The input CSV expected following columns:
- Question
- Answer options
- Correct answer
- Very Wrong answer
"""

import pandas as pd
import re
import random
import os
import argparse

def clean_option_text(option_text):
    """Removes leading option markers like 'A. ', 'B. ' etc."""
    # Regex to find patterns like "A. ", "B. ", "1. ", "a) "
    cleaned_text = re.sub(r'^[A-Za-z0-9][\.\)]\s+', '', option_text.strip())
    return cleaned_text.strip()


def split_options(options_text):
    options_text = options_text.strip()
    if '\n' in options_text and ',' in options_text:
        res = options_text.split('\n')
        # remove the tailing comma if there are any
        res = [x[:-1] if x[-1] == ',' else x for x in res]
    elif ',' not in options_text:
        res = options_text.split("\n")
    else:
        step1 = options_text.replace("\n", "")
        res = step1.split(',')

    return [x.strip() for x in res]


def extract_numerical_value(text):
    """Extract numerical value from text, handling percentages and comma-separated numbers."""
    # Remove any commas from numbers
    text = text.replace(',', '')

    # Try to extract a number with potential percentage sign
    match = re.search(r'([-+]?\d*\.?\d+)(?:\s*%)?', text)
    if match:
        value = float(match.group(1))
        # If it's a percentage, convert to the actual value
        if '%' in text:
            # Keep the percentage value as is, don't divide by 100
            pass
        return value

    return None


def determine_correctness(options, correct_index, very_wrong_answer):
    """
    Determine correctness values based on the rules:
    1. Correct answer gets 1
    2. For the other options:
       a. If very_wrong_answer exists, matching option gets 3, remaining gets 2
       b. If numerical values can be compared, furthest from correct gets 3
       c. Otherwise, assign in list order
    """
    correctness = {}
    correctness[correct_index] = 1

    # Get indices of incorrect options
    incorrect_indices = [i for i in range(len(options)) if i != correct_index]

    if len(incorrect_indices) < 2:
        # Not enough incorrect options to apply the rules
        for i in incorrect_indices:
            correctness[i] = 2
        return correctness

    # Case a: Check for Very Wrong Answer
    if very_wrong_answer:
        very_wrong_answer_cleaned = clean_option_text(very_wrong_answer)
        very_wrong_match_found = False

        for i in incorrect_indices:
            if options[i].lower() == very_wrong_answer_cleaned.lower():
                correctness[i] = 3
                very_wrong_match_found = True
                # Mark the other incorrect option as 2
                for j in incorrect_indices:
                    if j != i:
                        correctness[j] = 2
                break

        if very_wrong_match_found:
            return correctness

    # Case b: Try numerical comparison
    extracted_values = {}
    for i in range(len(options)):
        val = extract_numerical_value(options[i])
        if val is not None:
            extracted_values[i] = val

    # We only do numerical comparison if we have extracted values for all 3 options
    if len(extracted_values) == 3 and len(options) == 3 and correct_index in extracted_values:
        correct_val = extracted_values[correct_index]
        # Calculate distances from correct answer
        distances = {i: abs(v - correct_val) for i, v in extracted_values.items() if i != correct_index}

        if distances:
            # Find option with maximum distance from correct answer
            max_distance_index = max(distances.items(), key=lambda x: x[1])[0]
            for i in incorrect_indices:
                if i == max_distance_index:
                    correctness[i] = 3
                else:
                    correctness[i] = 2
            return correctness

    # Case c: Default to list order
    for i, idx in enumerate(incorrect_indices):
        correctness[idx] = 2 + i

    return correctness


def main():
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Convert halted questions CSV to questions and options CSV files.')
    parser.add_argument('-i', '--input',
                       default='halted_questions.csv',
                       help='Path to input CSV file (default: halted_questions.csv)')
    parser.add_argument('-o', '--output-dir',
                       default='./',
                       help='Output directory for generated CSV files (default: current directory)')
    parser.add_argument('-s', '--start-index',
                       type=int,
                       default=0,
                       help='Starting index for question IDs (default: 0)')

    args = parser.parse_args()

    # Use command line arguments
    input_csv_path = args.input
    output_dir = args.output_dir
    start_index = args.start_index

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    output_questions_path = os.path.join(output_dir, 'questions.csv')
    output_options_path = os.path.join(output_dir, 'question_options.csv')

    # Debug counters
    total_questions = 0
    skipped_no_options = 0
    skipped_too_few_options = 0
    skipped_no_correct_answer = 0
    processed_questions = 0

    try:
        # Read the input CSV. Attempt to find the correct header row.
        # The CSV has multiple initial rows that are not the true header.
        # We'll look for a row that contains expected column names.
        df_full = pd.read_csv(input_csv_path, dtype=str)
        df_full.columns = df_full.columns.map(lambda x: x.strip().replace("\n", " ").lower())

        expected_cols = ['question', 'correct answer', 'answer options', 'very wrong answer']

        # Drop rows where essential information for questions or options is missing
        # or where ID combo is a placeholder like '#REF!'
        # Note: Very Wrong Answer can be missing, so we don't include it in the required columns
        required_cols = ['question', 'correct answer', 'answer options']
        df_input = df_full.dropna(subset=required_cols)[expected_cols]
        if not df_input[df_input.duplicated(subset=["question"])].empty:
            print(df_input[df_input.duplicated(subset=["question"])])
            raise ValueError("Duplicated question")

        total_questions = len(df_input)
        print(f"Total questions found in CSV: {total_questions}")

        questions_data = []
        options_data = []

        processed_question_ids = set()

        for index, row in df_input.iterrows():
            question_id_raw = str(index + start_index)

            # Safely extract question text, handling cases where it might be a Series
            raw_question_val = row['question']
            if isinstance(raw_question_val, pd.Series):
                actual_question_string = raw_question_val.iloc[0]
            else:
                actual_question_string = raw_question_val
            question_text = str(actual_question_string).strip()

            correct_answer_text_raw = str(row.get('correct answer', '')).strip()
            answer_options_str = str(row.get('answer options', '')).strip()

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
            # drop empty ones
            parsed_options = [x for x in parsed_options if x != ""]

            # Clean the correct answer text as well, in case it has markers
            correct_answer_text_cleaned = clean_option_text(correct_answer_text_raw)

            if not parsed_options:
                print(f"Warning: No options found for QID {question_id_raw} after parsing '{answer_options_str}'. Skipping options for this question.")
                skipped_no_options += 1
                # Remove the question from questions_data
                questions_data = [q for q in questions_data if q['question_id'] != question_id_raw]
                processed_question_ids.discard(question_id_raw)
                continue

            # Skip questions with fewer than 3 options
            if len(parsed_options) < 3:
                print(f"Warning: Question QID {question_id_raw} has fewer than 3 options ({len(parsed_options)}). Skipping this question.")
                print(f"parsed options: {parsed_options}")
                skipped_too_few_options += 1
                # Remove the question from questions_data
                questions_data = [q for q in questions_data if q['question_id'] != question_id_raw]
                processed_question_ids.discard(question_id_raw)
                continue

            if len(parsed_options) != 3:
                print(f"Warning: Question QID {question_id_raw} has {len(parsed_options)} options, will select 3 options. Options: {parsed_options}")

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
                print(f"Warning: Correct answer text '{correct_answer_text_raw}' (cleaned: '{correct_answer_text_cleaned}') "
                      f"not found in parsed options '{parsed_options}' for QID {question_id_raw}. Skipping this question.")
                skipped_no_correct_answer += 1
                # Remove the question from questions_data
                questions_data = [q for q in questions_data if q['question_id'] != question_id_raw]
                processed_question_ids.discard(question_id_raw)
                continue

            # Select the options to use (all if 3, or a random subset including correct if more than 3)
            selected_options = []
            if len(temp_options_details) > 3:
                # Find the correct option(s)
                correct_options = [opt for opt in temp_options_details if opt['is_correct']]
                incorrect_options = [opt for opt in temp_options_details if not opt['is_correct']]

                # Make sure we have at least one correct option
                if not correct_options:
                    print(f"Error: No correct option identified for QID {question_id_raw} despite earlier check. Skipping question.")
                    continue

                # Take the first correct option (in case there are multiple marked correct)
                first_correct = correct_options[0]

                # If we have more than one correct option, log a warning
                if len(correct_options) > 1:
                    print(f"Warning: Multiple options marked as correct for QID {question_id_raw}. Using the first one: '{first_correct['text']}'")

                # Randomly select incorrect options to fill up to 3 total options
                num_incorrect_needed = 2
                if len(incorrect_options) < num_incorrect_needed:
                    print(f"Warning: Not enough incorrect options for QID {question_id_raw}. Using all available.")
                    selected_options = [first_correct] + incorrect_options
                else:
                    random_incorrect = random.sample(incorrect_options, num_incorrect_needed)
                    selected_options = [first_correct] + random_incorrect
            else:
                # If exactly 3 options, use all of them
                selected_options = temp_options_details

            # Apply new lettering
            new_option_letter_map = {i: chr(65 + i) for i in range(len(selected_options))}

            # Get the very wrong answer for this question, if available
            raw_vwa_val = row.get('very wrong answer')
            very_wrong_answer = str(raw_vwa_val).strip() if pd.notna(raw_vwa_val) else ''

            # Create a map of options and their correctness values
            option_texts = [opt_detail['text'] for opt_detail in selected_options]
            correct_index = next((i for i, opt in enumerate(selected_options) if opt['is_correct']), -1)

            # Determine correctness values based on rules
            correctness_map = determine_correctness(option_texts, correct_index, very_wrong_answer)

            # Process selected options and assign correctness values
            for i, opt_detail in enumerate(selected_options):
                letter = new_option_letter_map[i]  # This is 'A', 'B', 'C'
                question_option_id = f"{question_id_raw}-a{i+1}"

                # Assign correctness values using the map
                correctness_value = correctness_map.get(i, 2)  # Default to 2 if not found in the map

                options_data.append({
                    'question_option_id': question_option_id,
                    'question_id': question_id_raw,
                    'language': 'en-US',
                    'letter': letter,
                    'question_option': opt_detail['text'],
                    'correctness_of_answer_option': correctness_value
                })

        processed_questions = len(questions_data)

        # Create DataFrames
        df_questions_output = pd.DataFrame(questions_data)
        df_options_output = pd.DataFrame(options_data)

        # Save to CSV
        df_questions_output.to_csv(output_questions_path, index=False)
        print(f"Successfully created {output_questions_path} with {len(df_questions_output)} questions.")

        df_options_output.to_csv(output_options_path, index=False)
        print(f"Successfully created {output_options_path} with {len(df_options_output)} options.")

        # Print summary statistics
        print("\nProcessing Summary:")
        print(f"Total questions found in CSV: {total_questions}")
        print(f"Questions skipped due to no options: {skipped_no_options}")
        print(f"Questions skipped due to fewer than 3 options: {skipped_too_few_options}")
        print(f"Questions skipped due to no matching correct answer: {skipped_no_correct_answer}")
        print(f"Total questions processed: {processed_questions}")
        print(f"Expected options count (3 per question): {processed_questions * 3}")
        print(f"Actual options count: {len(df_options_output)}")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_csv_path}")
    except Exception as e:
        raise
        # print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
