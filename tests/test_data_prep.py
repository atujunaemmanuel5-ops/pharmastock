import pandas as pd
import pytest

from src.data_prep import validate_and_prepare_data


def valid_frame():
    groups = {name: [1] for name in ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]}
    return pd.DataFrame({"datum": ["1/2/2014"], **groups})


def test_invalid_negative_value_is_rejected():
    frame = valid_frame()
    frame.loc[0, "R03"] = -1
    with pytest.raises(ValueError, match="Negative"):
        validate_and_prepare_data(frame)


def test_missing_column_is_rejected():
    frame = valid_frame().drop(columns="R06")
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_and_prepare_data(frame)
