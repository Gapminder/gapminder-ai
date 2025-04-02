import re
from typing import Generic, Type, TypeVar

import numpy as np
import pandera as pa
from pandera import DataFrameModel
from pydantic import BaseModel

from lib.gsheets.gsheets_utils import get_pydantic_model_field_titles


def inv_dict(my_dict: dict) -> dict:
    return {v: k for k, v in my_dict.items()}


DfSchemaModel = TypeVar("DfSchemaModel", bound=Type[DataFrameModel])
RowSchemaModel = TypeVar("RowSchemaModel", bound=Type[BaseModel])


class GsheetsWorksheetData(Generic[DfSchemaModel, RowSchemaModel]):
    row_number_placeholder_in_formulas = "[[CURRENT_ROW]]"

    df_schema: DfSchemaModel
    row_schema: RowSchemaModel
    df: pa.typing.DataFrame[DfSchemaModel]
    header_row_number: int
    attributes_to_columns_map: dict

    def __init__(
        self,
        df_schema: DfSchemaModel,
        row_schema: RowSchemaModel,
        df: pa.typing.DataFrame[DfSchemaModel],
        header_row_number: int,
    ):
        self.df_schema = df_schema
        self.row_schema = row_schema
        self.header_row_number = header_row_number

        self.attributes_to_columns_map = get_pydantic_model_field_titles(self.row_schema)
        df = df.rename(columns=inv_dict(self.attributes_to_columns_map))
        df = self.replace_current_row_numbers_in_formulas(df)
        # import ipdb; ipdb.set_trace()
        self.df = df_schema(df)

    def replace_current_row_numbers_in_formulas(
        self, df: pa.typing.DataFrame[DfSchemaModel]
    ) -> pa.typing.DataFrame[DfSchemaModel]:
        df = df.copy()
        df["__row_number"] = np.arange(len(df)) + self.header_row_number + 2

        def replace_current_row_numbers(row: dict) -> dict:
            for col_name in df.columns:
                if col_name == "__row_number":
                    continue
                value = row[col_name]
                if isinstance(value, str) and len(value) > 0 and value[0] == "=":
                    row[col_name] = re.sub(
                        r"([A-Z]+)" + str(row["__row_number"]),
                        r"\1" + self.row_number_placeholder_in_formulas,
                        value,
                    )
            return row

        replaced_df = df.apply(replace_current_row_numbers, axis=1, result_type="broadcast")
        return replaced_df.drop(columns=["__row_number"])

    def restore_current_row_numbers_in_formulas(
        self, df: pa.typing.DataFrame[DfSchemaModel]
    ) -> pa.typing.DataFrame[DfSchemaModel]:
        df = df.copy()
        df["__row_number"] = np.arange(len(df)) + self.header_row_number + 2

        def restore_current_row_numbers(row: dict) -> dict:
            for col_name in self.df.columns:
                if col_name == "__row_number":
                    continue
                value = row[col_name]
                if isinstance(value, str) and len(value) > 0 and value[0] == "=":
                    row[col_name] = value.replace(
                        self.row_number_placeholder_in_formulas,
                        str(row["__row_number"]),
                    )
            return row

        replaced_df = df.apply(restore_current_row_numbers, axis=1, result_type="broadcast")
        return replaced_df.drop(columns=["__row_number"])

    def export(self) -> pa.typing.DataFrame[DfSchemaModel]:
        return self.restore_current_row_numbers_in_formulas(self.df).rename(columns=self.attributes_to_columns_map)
