from typing import Any, Dict, Generic, Type, TypeVar, Union

import gspread_dataframe
import pandas as pd
from gspread import Spreadsheet, Worksheet
from gspread.utils import rowcol_to_a1
from pandera import DataFrameModel
from pydantic import BaseModel

from lib.gsheets.gsheets_utils import get_worksheet
from lib.gsheets.gsheets_worksheet_data import GsheetsWorksheetData

DfSchemaModel = TypeVar("DfSchemaModel", bound=Type[DataFrameModel])
RowSchemaModel = TypeVar("RowSchemaModel", bound=Type[BaseModel])


class GsheetsWorksheetEditor(Generic[DfSchemaModel, RowSchemaModel]):
    df_schema: DfSchemaModel
    row_schema: RowSchemaModel
    sh: Spreadsheet
    data: GsheetsWorksheetData[DfSchemaModel, RowSchemaModel]
    worksheet: Worksheet
    worksheet_name: str
    header_row_number: int
    evaluate_formulas: bool
    remove_empty_rows: bool
    remove_empty_columns: bool

    def __init__(
        self,
        df_schema: DfSchemaModel,
        row_schema: RowSchemaModel,
        sh: Spreadsheet,
        worksheet_name: str,
        header_row_number: int,
        evaluate_formulas: bool = False,
        remove_empty_rows: bool = True,
        remove_empty_columns: bool = False,
    ):
        self.df_schema = df_schema
        self.row_schema = row_schema
        self.sh = sh
        self.worksheet_name = worksheet_name
        self.worksheet = get_worksheet(self.sh, self.worksheet_name)
        self.header_row_number = header_row_number
        self.evaluate_formulas = evaluate_formulas
        self.remove_empty_rows = remove_empty_rows
        self.remove_empty_columns = remove_empty_columns
        self.load()

    def load(
        self,
    ) -> None:
        df = gspread_dataframe.get_as_dataframe(
            self.worksheet,
            header=self.header_row_number,
            evaluate_formulas=self.evaluate_formulas,
        )

        if self.remove_empty_rows:
            df = df.dropna(axis=0, how="all")
        if self.remove_empty_columns:
            df = df.dropna(axis=1, how="all")

        self.data = GsheetsWorksheetData(
            df_schema=self.df_schema,
            row_schema=self.row_schema,
            df=df,
            header_row_number=self.header_row_number,
        )

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__} (sh.id={self.sh.id}, "
            f"worksheet_name={self.worksheet_name},"
            f" header_row_number={self.header_row_number})"
        )

    def append_row(self, row: dict) -> None:
        df_with_row = pd.DataFrame([row])
        self.append_data(df_with_row)

    def remove_row(self, df_row_index: int) -> None:
        start_index = df_row_index + self.data.header_row_number + 2
        self.worksheet.delete_rows(start_index)  # , end_index=None
        self.data.df = self.data.df.drop([df_row_index])

    def replace_data(self, df: pd.DataFrame) -> None:
        self.data.df = df
        export_df = self.data.export()
        gspread_dataframe.set_with_dataframe(self.worksheet, export_df, resize=True)

    def append_data(self, df: pd.DataFrame) -> None:
        new_df = pd.concat([self.data.df, df], ignore_index=True)
        self.data.df = new_df
        export_df = self.data.export()
        appended_rows_export_df = export_df.tail(len(df))
        gspread_dataframe.set_with_dataframe(
            self.worksheet,
            appended_rows_export_df,
            resize=False,
            row=self.worksheet.row_count + 1,
            include_column_header=False,
        )
        # Gspread does not update the row count after a resize, so we must re-create the worksheet
        self.worksheet = get_worksheet(self.sh, self.worksheet_name)

    def update_a_cell(
        self,
        df_row_index: int,
        df_column_name: str,
        value: Any,
        batch: bool = False,
        only_if_empty: bool = False,
    ) -> Union[bool, Dict[str, Any]]:

        # check the existing value
        existing_value = self.data.df.at[df_row_index, df_column_name]

        if only_if_empty:
            empty = pd.isna(existing_value) or existing_value == ""
            if not empty:
                return False

        # create the update request
        row_number = df_row_index + self.data.header_row_number + 2
        column_number = self.data.df.columns.get_loc(df_column_name) + 1

        gs_range = rowcol_to_a1(row_number, column_number)
        if batch:
            return {"range": gs_range, "values": [[value]]}
        self.worksheet.update_acell(gs_range, value)

        # update the df as well so that it is up to date
        # TODO: find a way to support this properly in batch mode
        if not batch:
            self.data.df.at[df_row_index, df_column_name] = value

        return True
