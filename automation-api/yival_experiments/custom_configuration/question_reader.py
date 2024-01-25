from typing import Iterator, List

from question_reader_config import QuestionReaderConfig
from yival.data.base_reader import BaseReader
from yival.schemas.common_structures import InputData

from lib.pilot.helpers import get_questions, read_ai_eval_spreadsheet


class QuestionReader(BaseReader):
    """
    QuestionReader is ...

    Attributes:
        config (TXTReaderConfig): Configuration object specifying reader parameters.

    Methods:
        __init__(self, config: TXTReaderConfig): Initializes the TXTReader with
        a given configuration.
        read(self, path: str) -> Iterator[List[InputData]]: Reads the TXT file
        and yields chunks of InputData.
    """

    config: QuestionReaderConfig
    default_config = QuestionReaderConfig()

    def __init__(self, config: QuestionReaderConfig):
        super().__init__(config)
        self.config = config

    def read(self, path: str) -> Iterator[List[InputData]]:
        sheet = read_ai_eval_spreadsheet()
        questions = get_questions(sheet)

        for q, opts in questions:
            options_text = [f"{opt.letter}. {opt.question_option}" for opt in opts]
            content = {
                "question_id": q.question_id,
                "question_text": q.published_version_of_question,
                "options_text": options_text,
            }
            correct_answer = list(
                filter(lambda x: x.correctness_of_answer_option == 1, opts)
            )[0]
            expected_result = (
                f"{correct_answer.letter}. {correct_answer.question_option}"
            )

            example_id = self.generate_example_id({"content": content}, "")
            input_data_instance = InputData(
                example_id=example_id, content=content, expected_result=expected_result
            )
            yield [input_data_instance]
