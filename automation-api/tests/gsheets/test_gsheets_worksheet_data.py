from json import dumps
from typing import Optional, Type

import pandas as pd
import pandera as pa
import pytest
from pandera.engines.pandas_engine import PydanticModel
from pandera.errors import SchemaError
from pydantic.fields import Field
from pydantic.main import BaseModel

from lib.gsheets.gsheets_worksheet_data import GsheetsWorksheetData


def test_gsheets_worksheet_data() -> None:
    original_df = pd.DataFrame(
        [
            {"Foo": "=C$2:C2", "bar": "Cat", "bool": False},
            {"Foo": "=C$2:C3", "bar": "Mouse", "bool": False},
            {"Foo": "=C$2:C2", "bar": "Dog", "bool": True},
            {"Foo": "=C$2:C5", "bar": "Eagle", "bool": True},
            {"Foo": "C$2:C6", "bar": "Albatross", "bool": False},
            {"Foo": "", "bar": "Albatross", "bool": False},
        ]
    )

    internal_df = pd.DataFrame(
        [
            {"foo": "=C$2:C[[CURRENT_ROW]]", "bar": "Cat", "bool_column": False},
            {"foo": "=C$2:C[[CURRENT_ROW]]", "bar": "Mouse", "bool_column": False},
            {"foo": "=C$2:C2", "bar": "Dog", "bool_column": True},
            {"foo": "=C$2:C[[CURRENT_ROW]]", "bar": "Eagle", "bool_column": True},
            {"foo": "C$2:C6", "bar": "Albatross", "bool_column": False},
            {"foo": "", "bar": "Albatross", "bool_column": False},
        ]
    )

    class Foo(BaseModel):
        foo: Optional[str] = Field(..., title="Foo")
        bar: Optional[str] = Field(..., title="bar")
        bool_column: Optional[bool] = Field(..., title="bool")

    class FooDfModel(pa.DataFrameModel):
        class Config:
            dtype = PydanticModel(Foo)
            coerce = True
            # strict = True # Not compatible with only PydanticModel row-wise checks

    data = GsheetsWorksheetData[Type[FooDfModel], Type[Foo]](
        df_schema=FooDfModel,
        row_schema=Foo,
        df=original_df,
        header_row_number=0,
        # attributes_to_columns_map=get_pydantic_model_field_titles(Foo),
    )
    actual = dumps(data.df.to_dict(orient="records"), indent=2)
    expected = dumps(internal_df.to_dict(orient="records"), indent=2)
    assert actual == expected

    actual = dumps(data.export().to_dict(orient="records"), indent=2)
    expected = dumps(original_df.to_dict(orient="records"), indent=2)
    assert actual == expected


# This oddity is reported upstream as https://github.com/unionai-oss/pandera/issues/1195
def test_gsheets_worksheet_data_empty_df() -> None:
    class Foo(BaseModel):
        include_in_next_evaluation: Optional[bool] = Field(
            None, title="Include in next evaluation"
        )
        model_id: Optional[int] = Field(None, title="Model ID")
        vendor: Optional[str] = Field(None, title="Vendor")
        model_name: Optional[str] = Field(None, title="Model name")

    class FooDfModel(pa.DataFrameModel):
        class Config:
            dtype = PydanticModel(Foo)
            coerce = True
            # strict = True

    empty_df = pd.DataFrame(columns=Foo.schema().get("properties").keys())
    with pytest.raises(SchemaError):
        FooDfModel.validate(empty_df)
