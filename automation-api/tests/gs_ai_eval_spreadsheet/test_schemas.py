import pandas as pd
import pandera as pa
import pytest
from pandera.engines.pandas_engine import PydanticModel
from pandera.errors import SchemaError
from pydantic.main import BaseModel


class Record(BaseModel):
    name: str
    xcoord: str
    ycoord: str


class PydanticSchema(pa.DataFrameModel):
    """Pandera schema using the pydantic model."""

    class Config:
        """Config with dataframe-level data type."""

        dtype = PydanticModel(Record)
        coerce = True  # this is required, otherwise a SchemaInitError is raised


class PanderaSchema(pa.DataFrameModel):
    """Pandera schema that's equivalent to PydanticSchema."""

    name: pa.typing.Series[str]
    xcoord: pa.typing.Series[str]
    ycoord: pa.typing.Series[str]


# Just to demonstrate the pandera-pydantic combo we use in the codebase
def test_pandera_pydantic_schema() -> None:
    valid_df = pd.DataFrame(
        [
            {"name": "Foo", "xcoord": "123", "ycoord": "457"},
            {"name": "Bar", "xcoord": "123", "ycoord": "457"},
        ]
    )
    PydanticSchema.validate(valid_df)

    invalid_df = pd.DataFrame(
        [
            {"name": "Foo", "xcoord": "123"},
            {"name": "Bar", "xcoord": "123"},
        ]
    )
    with pytest.raises(SchemaError):
        PydanticSchema.validate(invalid_df)


# This oddity is reported upstream as https://github.com/unionai-oss/pandera/issues/1195
def test_pandera_pydantic_schema_empty_df_issue() -> None:

    columns = list(PanderaSchema.to_schema().columns.keys())
    empty_df = pd.DataFrame(columns=columns)
    PanderaSchema.validate(empty_df)

    columns = list(Record.schema().get("properties").keys())
    empty_df = pd.DataFrame(columns=columns)
    with pytest.raises(SchemaError):
        PydanticSchema.validate(empty_df)
