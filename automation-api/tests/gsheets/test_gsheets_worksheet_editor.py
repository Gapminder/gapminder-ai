import unittest.mock
from typing import Optional, Type

import pandas as pd
import pandera as pa
from pandera.engines.pandas_engine import PydanticModel
from pydantic.fields import Field
from pydantic.main import BaseModel

from lib.gsheets.gsheets_worksheet_editor import GsheetsWorksheetEditor


@unittest.mock.patch("gspread_dataframe.set_with_dataframe")
@unittest.mock.patch("gspread_dataframe.get_as_dataframe")
@unittest.mock.patch("gspread.Worksheet")
@unittest.mock.patch("gspread.Spreadsheet")
def test_gsheets_worksheet_editor(
    mock_spreadsheet: unittest.mock.MagicMock,
    mock_worksheet: unittest.mock.MagicMock,
    mock_get_as_dataframe: unittest.mock.MagicMock,
    mock_set_with_dataframe: unittest.mock.MagicMock,
) -> None:

    mock_spreadsheet.return_value.get_worksheet.return_value = mock_worksheet
    mock_spreadsheet.return_value.id.return_value = "foo-123"

    # mock_worksheet_df = pd.DataFrame(columns=["Foo", "bar", "bool"])
    mock_worksheet_df = pd.DataFrame(
        [
            {"Foo": "=C$2:C2", "bar": "Cat", "bool": False},
            {"Foo": "=C$2:C3", "bar": "Mouse", "bool": False},
            {"Foo": "=C$2:C2", "bar": "Dog", "bool": True},
        ]
    )

    mock_get_as_dataframe.return_value = mock_worksheet_df
    mock_set_with_dataframe.return_value = True

    class Foo(BaseModel):
        model_id: Optional[int] = Field(None, title="Model ID")
        vendor: Optional[str] = Field(None, title="Vendor")
        model_name: Optional[str] = Field(None, title="Model name")

    class FooDfModel(pa.DataFrameModel):
        class Config:
            dtype = PydanticModel(Foo)
            coerce = True
            # strict = True

    editor = GsheetsWorksheetEditor[Type[FooDfModel], Type[Foo]](
        df_schema=FooDfModel,
        row_schema=Foo,
        sh=mock_spreadsheet,
        worksheet_name="Sheet1",
        header_row_number=0,
    )

    assert editor.data.df is not None

    df = editor.data.export()
    assert df is not None

    new_df = pd.DataFrame(
        [
            {"Foo": "=C$2:C2", "bar": "Cat", "bool": False},
            {"Foo": "=C$2:C3", "bar": "Mouse", "bool": False},
            {"Foo": "=C$2:C2", "bar": "Dog", "bool": True},
            {"Foo": "=C$2:C5", "bar": "Eagle", "bool": True},
            {"Foo": "C$2:C6", "bar": "Albatross", "bool": False},
            {"Foo": "", "bar": "Albatross", "bool": False},
        ]
    )
    editor.replace_data(new_df)
    assert editor.data.df.index[-1] == len(new_df) - 1

    editor.append_row({"Foo": "=C$2:C2", "bar": "New"})
    assert editor.data.df.index[-1] == len(new_df)

    editor.remove_row(editor.data.df.index[-1])
    assert editor.data.df.index[-1] == len(new_df) - 1

    append_df = pd.DataFrame(
        [
            {"Foo": "=C$2:C2", "zar": "Bat", "bool": False},
            {"Foo": "=C$2:C3", "zar": "House", "bool": False},
        ]
    )
    editor.append_data(append_df)
    assert editor.data.df.index[-1] == len(new_df) + len(append_df) - 1

    # Verify that the mock object's get_worksheet() method was called
    # mock_spreadsheet.assert_called_with()
    # mock_spreadsheet.return_value.get_worksheet.assert_called_with()
