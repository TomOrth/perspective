# *****************************************************************************
#
# Copyright (c) 2019, the Perspective Authors.
#
# This file is part of the Perspective library, distributed under the terms of
# the Apache License 2.0.  The full license can be found in the LICENSE file.
#
import six
import time
from io import StringIO
from datetime import date, datetime
import numpy as np
import pandas as pd
from perspective.table import Table
from random import random, randint, choice
from faker import Faker
fake = Faker()


def _to_timestamp(obj):
    if six.PY2:
        return int((time.mktime(obj.timetuple()) + obj.microsecond / 1000000.0))
    else:
        return obj.timestamp()


def superstore(count=10):
    data = []
    for id in range(count):
        dat = {}
        dat['Row ID'] = id
        dat['Order ID'] = fake.ein()
        dat['Order Date'] = fake.date_this_year()
        dat['Ship Date'] = fake.date_between_dates(dat['Order Date']).strftime('%Y-%m-%d')
        dat['Order Date'] = dat['Order Date'].strftime('%Y-%m-%d')
        dat['Ship Mode'] = choice(['First Class', 'Standard Class', 'Second Class'])
        dat['Ship Mode'] = choice(['First Class', 'Standard Class', 'Second Class'])
        dat['Customer ID'] = fake.license_plate()
        dat['Segment'] = choice(['A', 'B', 'C', 'D'])
        dat['Country'] = 'US'
        dat['City'] = fake.city()
        dat['State'] = fake.state()
        dat['Postal Code'] = fake.zipcode()
        dat['Region'] = choice(['Region %d' % i for i in range(5)])
        dat['Product ID'] = fake.bban()
        sector = choice(['Industrials', 'Technology', 'Financials'])
        industry = choice(['A', 'B', 'C'])
        dat['Category'] = sector
        dat['Sub-Category'] = industry
        dat['Sales'] = randint(1, 100) * 100
        dat['Quantity'] = randint(1, 100) * 10
        dat['Discount'] = round(random() * 100, 2)
        dat['Profit'] = round(random() * 1000, 2)
        data.append(dat)
    return pd.DataFrame(data)


class TestTablePandas(object):
    def test_empty_table(self):
        tbl = Table([])
        assert tbl.size() == 0
        assert tbl.schema() == {}

    def test_table_dataframe(self):
        d = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        data = pd.DataFrame(d)
        tbl = Table(data)
        assert tbl.size() == 2
        assert tbl.schema() == {
            "index": int,
            "a": int,
            "b": int
        }
        assert tbl.view().to_records() == [
            {"a": 1, "b": 2, "index": 0},
            {"a": 3, "b": 4, "index": 1}
        ]

    def test_table_dataframe_does_not_mutate(self):
        # make sure we don't mutate the dataframe that a user passes in
        data = pd.DataFrame({
            "a": np.array([None, 1, None, 2], dtype=object),
            "b": np.array([1.5, None, 2.5, None], dtype=object)
        })
        assert data["a"].tolist() == [None, 1, None, 2]
        assert data["b"].tolist() == [1.5, None, 2.5, None]

        tbl = Table(data)
        assert tbl.size() == 4
        assert tbl.schema() == {
            "index": int,
            "a": float,
            "b": float
        }

        assert data["a"].tolist() == [None, 1, None, 2]
        assert data["b"].tolist() == [1.5, None, 2.5, None]

    def test_table_pandas_from_schema_int(self):
        data = [None, 1, None, 2, None, 3, 4]
        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": int
        })
        table.update(df)
        assert table.view().to_dict()["a"] == data

    def test_table_pandas_from_schema_bool(self):
        data = [True, False, True, False]
        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": bool
        })
        table.update(df)
        assert table.view().to_dict()["a"] == data

    def test_table_pandas_from_schema_float(self):
        data = [None, 1.5, None, 2.5, None, 3.5, 4.5]
        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": float
        })
        table.update(df)
        assert table.view().to_dict()["a"] == data

    def test_table_pandas_from_schema_float_all_nan(self):
        data = [np.nan, np.nan, np.nan, np.nan]
        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": float
        })
        table.update(df)
        assert table.view().to_dict()["a"] == [None, None, None, None]

    def test_table_pandas_from_schema_float_to_int(self):
        data = [None, 1.5, None, 2.5, None, 3.5, 4.5]
        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": int
        })
        table.update(df)
        # truncates decimal
        assert table.view().to_dict()["a"] == [None, 1, None, 2, None, 3, 4]

    def test_table_pandas_from_schema_int_to_float(self):
        data = [None, 1, None, 2, None, 3, 4]
        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": float
        })
        table.update(df)
        assert table.view().to_dict()["a"] == [None, 1.0, None, 2.0, None, 3.0, 4.0]

    def test_table_pandas_from_schema_date(self):
        data = [date(2019, 8, 15), None, date(2019, 8, 16)]
        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": date
        })
        table.update(df)
        assert table.view().to_dict()["a"] == [datetime(2019, 8, 15, 0, 0), None, datetime(2019, 8, 16, 0, 0)]

    def test_table_pandas_from_schema_datetime(self):
        data = [datetime(2019, 7, 11, 12, 30, 5), None, datetime(2019, 7, 11, 13, 30, 5), None]
        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": datetime
        })
        table.update(df)
        assert table.view().to_dict()["a"] == data

    def test_table_pandas_from_schema_datetime_timestamp_s(self):
        data = [_to_timestamp(datetime(2019, 7, 11, 12, 30, 5)), np.nan, _to_timestamp(datetime(2019, 7, 11, 13, 30, 5)), np.nan]
        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": datetime
        })
        table.update(df)
        assert table.view().to_dict()["a"] == [
            datetime(2019, 7, 11, 12, 30, 5),
            None,
            datetime(2019, 7, 11, 13, 30, 5),
            None
        ]

    def test_table_pandas_from_schema_datetime_timestamp_ms(self):
        data = [
            _to_timestamp(datetime(2019, 7, 11, 12, 30, 5)) * 1000,
            np.nan,
            _to_timestamp(datetime(2019, 7, 11, 13, 30, 5)) * 1000,
            np.nan
        ]

        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": datetime
        })
        table.update(df)
        assert table.view().to_dict()["a"] == [
            datetime(2019, 7, 11, 12, 30, 5),
            None,
            datetime(2019, 7, 11, 13, 30, 5),
            None
        ]

    def test_table_pandas_from_schema_str(self):
        data = ["a", None, "b", None, "c"]
        df = pd.DataFrame({
            "a": data
        })
        table = Table({
            "a": str
        })
        table.update(df)
        assert table.view().to_dict()["a"] == data

    def test_table_pandas_none(self):
        data = [None, None, None]
        df = pd.DataFrame({
            "a": data
        })
        table = Table(df)
        assert table.view().to_dict()["a"] == data

    def test_table_pandas_symmetric_table(self):
        # make sure that updates are symmetric to table creation
        df = pd.DataFrame({
            "a": [1, 2, 3, 4],
            "b": [1.5, 2.5, 3.5, 4.5]
        })
        t1 = Table(df)
        t2 = Table({
            "a": int,
            "b": float
        })
        t2.update(df)
        assert t1.view().to_dict() == {
            "index": [0, 1, 2, 3],
            "a": [1, 2, 3, 4],
            "b": [1.5, 2.5, 3.5, 4.5]
        }

    def test_table_pandas_symmetric_stacked_updates(self):
        # make sure that updates are symmetric to table creation
        df = pd.DataFrame({
            "a": [1, 2, 3, 4],
            "b": [1.5, 2.5, 3.5, 4.5]
        })

        t1 = Table(df)
        t1.update(df)

        t2 = Table({
            "a": int,
            "b": float
        })
        t2.update(df)
        t2.update(df)

        assert t1.view().to_dict() == {
            "index": [0, 1, 2, 3, 0, 1, 2, 3],
            "a": [1, 2, 3, 4, 1, 2, 3, 4],
            "b": [1.5, 2.5, 3.5, 4.5, 1.5, 2.5, 3.5, 4.5]
        }

    def test_table_pandas_transitive(self):
        # serialized output -> table -> serialized output
        df = pd.DataFrame({
            "a": [1, 2, 3, 4],
            "b": [1.5, 2.5, 3.5, 4.5],
            "c": [np.nan, np.nan, "abc", np.nan],
            "d": [np.nan, True, np.nan, False],
            "e": [float("nan"), datetime(2019, 7, 11, 12, 30), float("nan"), datetime(2019, 7, 11, 12, 30)]
        })

        t1 = Table(df)
        out1 = t1.view().to_df()

        t2 = Table(out1)

        assert t1.schema() == t2.schema()

        out2 = t2.view().to_dict()

        assert t1.view().to_dict() == out2

    # dtype=object should have correct inferred types

    def test_table_pandas_object_to_int(self):
        df = pd.DataFrame({
            "a": np.array([1, 2, None, 2, None, 3, 4], dtype=object)
        })
        table = Table(df)
        assert table.schema() == {
            "index": int,
            "a": float
        }
        assert table.view().to_dict()["a"] == [1, 2, None, 2, None, 3, 4]

    def test_table_pandas_object_to_float(self):
        df = pd.DataFrame({
            "a": np.array([None, 1, None, 2, None, 3, 4], dtype=object)
        })
        table = Table(df)
        assert table.schema() == {
            "index": int,
            "a": float  # None -> np.nan which is a float
        }
        assert table.view().to_dict()["a"] == [None, 1.0, None, 2.0, None, 3.0, 4.0]

    def test_table_pandas_object_to_bool(self):
        df = pd.DataFrame({
            "a": np.array([True, False, True, False, True, False], dtype=object)
        })
        table = Table(df)
        assert table.schema() == {
            "index": int,
            "a": bool
        }
        assert table.view().to_dict()["a"] == [True, False, True, False, True, False]

    def test_table_pandas_object_to_date(self):
        df = pd.DataFrame({
            "a": np.array([date(2019, 7, 11), date(2019, 7, 12), None], dtype=object)
        })
        table = Table(df)
        assert table.schema() == {
            "index": int,
            "a": date
        }
        assert table.view().to_dict()["a"] == [datetime(2019, 7, 11, 0, 0), datetime(2019, 7, 12, 0, 0), None]

    def test_table_pandas_object_to_datetime(self):
        df = pd.DataFrame({
            "a": np.array([datetime(2019, 7, 11, 1, 2, 3), datetime(2019, 7, 12, 1, 2, 3), None], dtype=object)
        })
        table = Table(df)
        assert table.schema() == {
            "index": int,
            "a": datetime
        }
        assert table.view().to_dict()["a"] == [datetime(2019, 7, 11, 1, 2, 3), datetime(2019, 7, 12, 1, 2, 3), None]

    def test_table_pandas_object_to_str(self):
        df = pd.DataFrame({
            "a": np.array(["abc", "def", None, "ghi"], dtype=object)
        })
        table = Table(df)
        assert table.schema() == {
            "index": int,
            "a": str
        }
        assert table.view().to_dict()["a"] == ["abc", "def", None, "ghi"]

    # Type matching

    def test_table_pandas_update_float_schema_with_int(self):
        df = pd.DataFrame({
            "a": [1.5, 2.5, 3.5, 4.5],
            "b": [1, 2, 3, 4]
        })

        table = Table({
            "a": float,
            "b": float
        })

        table.update(df)

        assert table.view().to_dict() == {
            "a": [1.5, 2.5, 3.5, 4.5],
            "b": [1.0, 2.0, 3.0, 4.0]
        }

    def test_table_pandas_update_int32_with_int64(self):
        df = pd.DataFrame({
            "a": [1, 2, 3, 4]
        })

        table = Table({
            "a": [1, 2, 3, 4]
        })

        table.update(df)

        assert table.view().to_dict() == {
            "a": [1, 2, 3, 4, 1, 2, 3, 4]
        }

    def test_table_pandas_update_int64_with_float(self):
        df = pd.DataFrame({
            "a": [1.5, 2.5, 3.5, 4.5]
        })

        table = Table(pd.DataFrame({
            "a": [1, 2, 3, 4]
        }))

        table.update(df)

        assert table.view().to_dict()["a"] == [1, 2, 3, 4, 1, 2, 3, 4]

    def test_table_pandas_update_date_schema_with_datetime(self):
        df = pd.DataFrame({
            "a": np.array([date(2019, 7, 11)])
        })

        table = Table({
            "a": date
        })

        table.update(df)

        assert table.schema() == {
            "a": date
        }

        assert table.view().to_dict() == {
            "a": [datetime(2019, 7, 11, 0, 0)]
        }

    def test_table_pandas_update_datetime_schema_with_date(self):
        df = pd.DataFrame({
            "a": np.array([datetime(2019, 7, 11, 11, 12, 30)])
        })

        table = Table({
            "a": date
        })

        table.update(df)

        assert table.schema() == {
            "a": date
        }

        assert table.view().to_dict() == {
            "a": [datetime(2019, 7, 11, 0, 0)]
        }

    # Timestamps

    def test_table_pandas_timestamp_to_datetime(self):
        data = [pd.Timestamp(2019, 7, 11, 12, 30, 5), None, pd.Timestamp(2019, 7, 11, 13, 30, 5), None]
        df = pd.DataFrame({
            "a": data
        })
        table = Table(df)
        assert table.view().to_dict()["a"] == [datetime(2019, 7, 11, 12, 30, 5), None, datetime(2019, 7, 11, 13, 30, 5), None]

    def test_table_pandas_timestamp_explicit_dtype(self):
        data = [pd.Timestamp(2019, 7, 11, 12, 30, 5), None, pd.Timestamp(2019, 7, 11, 13, 30, 5), None]
        df = pd.DataFrame({
            "a": np.array(data, dtype="datetime64[ns]")
        })
        table = Table(df)
        assert table.view().to_dict()["a"] == [datetime(2019, 7, 11, 12, 30, 5), None, datetime(2019, 7, 11, 13, 30, 5), None]

    def test_table_pandas_update_datetime_with_timestamp(self):
        data = [datetime(2019, 7, 11, 12, 30, 5), None, datetime(2019, 7, 11, 13, 30, 5), None]
        df = pd.DataFrame({
            "a": data
        })
        df2 = pd.DataFrame({
            "a": [pd.Timestamp(2019, 7, 11, 12, 30, 5), None, pd.Timestamp(2019, 7, 11, 13, 30, 5), None]
        })
        table = Table(df)
        table.update(df2)
        assert table.view().to_dict()["a"] == [datetime(2019, 7, 11, 12, 30, 5), None, datetime(2019, 7, 11, 13, 30, 5), None,
                                               datetime(2019, 7, 11, 12, 30, 5), None, datetime(2019, 7, 11, 13, 30, 5), None]

    def test_tables_pandas_timedf(self):
        data = pd.util.testing.makeTimeDataFrame(5)
        table = Table(data)
        assert table.size() == 5
        assert table.view().to_dict()["index"] == [
            datetime(2000, 1, 3, 0, 0),
            datetime(2000, 1, 4, 0, 0),
            datetime(2000, 1, 5, 0, 0),
            datetime(2000, 1, 6, 0, 0),
            datetime(2000, 1, 7, 0, 0)
        ]
    # Timeseries/Period index

    def test_table_pandas_timeseries(self):
        df = pd.DataFrame(pd.util.testing.getTimeSeriesData())
        tbl = Table(df)
        assert tbl.size() == 30
        assert tbl.schema() == {
            "index": datetime,
            "A": float,
            "B": float,
            "C": float,
            "D": float
        }

    def test_table_pandas_periodindex(self):
        df = pd.DataFrame(pd.util.testing.getPeriodData())
        tbl = Table(df)
        assert tbl.size() == 30
        assert tbl.schema() == {
            "index": datetime,
            "A": float,
            "B": float,
            "C": float,
            "D": float
        }

    def test_table_pandas_period(self):
        df = pd.DataFrame({"a": [pd.Period("1Q2019"), pd.Period("2Q2019"), pd.Period("3Q2019"), pd.Period("4Q2019")]})
        tbl = Table(df)
        assert tbl.size() == 4
        assert tbl.schema() == {
            "index": int,
            "a": datetime
        }
        assert tbl.view().to_dict()["a"] == [
            datetime(2019, 1, 1, 0, 0),
            datetime(2019, 4, 1, 0, 0),
            datetime(2019, 7, 1, 0, 0),
            datetime(2019, 10, 1, 0, 0),
        ]

    # NaN/NaT reading

    def test_table_pandas_nan(self):
        data = [np.nan, np.nan, np.nan, np.nan]
        df = pd.DataFrame({
            "a": data
        })
        table = Table(df)
        assert table.view().to_dict()["a"] == [None, None, None, None]

    def test_table_pandas_int_nan(self):
        data = [np.nan, 1, np.nan, 2]
        df = pd.DataFrame({
            "a": data
        })
        table = Table(df)
        assert table.view().to_dict()["a"] == [None, 1, None, 2]

    def test_table_pandas_float_nan(self):
        data = [np.nan, 1.5, np.nan, 2.5]
        df = pd.DataFrame({
            "a": data
        })
        table = Table(df)
        assert table.view().to_dict()["a"] == [None, 1.5, None, 2.5]

    def test_table_read_nan_int_col(self):
        data = pd.DataFrame({"str": ["abc", float("nan"), "def"], "int": [np.nan, 1, 2]})
        tbl = Table(data)
        assert tbl.schema() == {
            "index": int,
            "str": str,
            "int": float  # np.nan is float type - ints convert to floats when filled in
        }
        assert tbl.size() == 3
        assert tbl.view().to_dict() == {
            "index": [0, 1, 2],
            "str": ["abc", None, "def"],
            "int": [None, 1.0, 2.0]
        }

    def test_table_read_nan_float_col(self):
        data = pd.DataFrame({"str": [float("nan"), "abc", float("nan")], "float": [np.nan, 1.5, 2.5]})
        tbl = Table(data)
        assert tbl.schema() == {
            "index": int,
            "str": str,
            "float": float  # can only promote to string or float
        }
        assert tbl.size() == 3
        assert tbl.view().to_dict() == {
            "index": [0, 1, 2],
            "str": [None, "abc", None],
            "float": [None, 1.5, 2.5]
        }

    def test_table_read_nan_bool_col(self):
        data = pd.DataFrame({"bool": [np.nan, True, np.nan], "bool2": [False, np.nan, True]})
        tbl = Table(data)
        # if np.nan begins a column, it is inferred as float and then can be promoted. if np.nan is in the values (but not at start), the column type is whatever is inferred.
        assert tbl.schema() == {
            "index": int,
            "bool": str,
            "bool2": bool
        }
        assert tbl.size() == 3
        # np.nans are always serialized as None
        assert tbl.view().to_dict() == {
            "index": [0, 1, 2],
            "bool": [None, "True", None],
            "bool2": [False, None, True]
        }

    def test_table_read_nan_date_col(self):
        data = pd.DataFrame({"str": ["abc", "def"], "date": [float("nan"), date(2019, 7, 11)]})
        tbl = Table(data)
        assert tbl.schema() == {
            "index": int,
            "str": str,
            "date": str  # can only promote to string or float
        }
        assert tbl.size() == 2
        assert tbl.view().to_dict() == {
            "index": [0, 1],
            "str": ["abc", "def"],
            "date": [None, '2019-07-11']
        }

    def test_table_read_nan_datetime_col(self):
        data = pd.DataFrame({"str": ["abc", "def"], "datetime": [float("nan"), datetime(2019, 7, 11, 11, 0)]})
        tbl = Table(data)
        assert tbl.schema() == {
            "index": int,
            "str": str,
            "datetime": datetime  # can only promote to string or float
        }
        assert tbl.size() == 2
        assert tbl.view().to_dict() == {
            "index": [0, 1],
            "str": ["abc", "def"],
            "datetime": [None, datetime(2019, 7, 11, 11, 0)]
        }

    def test_table_read_nat_datetime_col(self):
        data = pd.DataFrame({"str": ["abc", "def"], "datetime": ["NaT", datetime(2019, 7, 11, 11, 0)]})
        tbl = Table(data)
        assert tbl.schema() == {
            "index": int,
            "str": str,
            "datetime": datetime  # can only promote to string or float
        }
        assert tbl.size() == 2
        assert tbl.view().to_dict() == {
            "index": [0, 1],
            "str": ["abc", "def"],
            "datetime": [None, datetime(2019, 7, 11, 11, 0)]
        }

    def test_table_read_nan_datetime_as_date_col(self):
        data = pd.DataFrame({"str": ["abc", "def"], "datetime": [float("nan"), datetime(2019, 7, 11)]})
        tbl = Table(data)
        assert tbl.schema() == {
            "index": int,
            "str": str,
            "datetime": datetime  # can only promote to string or float
        }
        assert tbl.size() == 2
        assert tbl.view().to_dict() == {
            "index": [0, 1],
            "str": ["abc", "def"],
            "datetime": [None, datetime(2019, 7, 11)]
        }

    def test_table_read_nan_datetime_no_seconds(self):
        data = pd.DataFrame({"str": ["abc", "def"], "datetime": [float("nan"), datetime(2019, 7, 11, 11, 0)]})
        tbl = Table(data)
        assert tbl.schema() == {
            "index": int,
            "str": str,
            "datetime": datetime  # can only promote to string or float
        }
        assert tbl.size() == 2
        assert tbl.view().to_dict() == {
            "index": [0, 1],
            "str": ["abc", "def"],
            "datetime": [None, datetime(2019, 7, 11, 11, 0)]
        }

    def test_table_read_nan_datetime_milliseconds(self):
        data = pd.DataFrame({"str": ["abc", "def"], "datetime": [np.nan, datetime(2019, 7, 11, 10, 30, 55)]})
        tbl = Table(data)
        assert tbl.schema() == {
            "index": int,
            "str": str,
            "datetime": datetime  # can only promote to string or float
        }
        assert tbl.size() == 2
        assert tbl.view().to_dict() == {
            "index": [0, 1],
            "str": ["abc", "def"],
            "datetime": [None, datetime(2019, 7, 11, 10, 30, 55)]
        }

    def test_table_correct_csv_nan_end(self):
        s = "str,int\n,1\n,2\nabc,3"
        if six.PY2:
            s = unicode(s)
        csv = StringIO(s)
        data = pd.read_csv(csv)
        tbl = Table(data)
        assert tbl.schema() == {
            "index": int,
            "str": str,
            "int": int
        }
        assert tbl.size() == 3
        assert tbl.view().to_dict() == {
            "index": [0, 1, 2],
            "str": [None, None, "abc"],
            "int": [1, 2, 3]
        }

    def test_table_correct_csv_nan_intermittent(self):
        s = "str,float\nabc,\n,2\nghi,"
        if six.PY2:
            s = unicode(s)
        csv = StringIO(s)
        data = pd.read_csv(csv)
        tbl = Table(data)
        assert tbl.schema() == {
            "index": int,
            "str": str,
            "float": float
        }
        assert tbl.size() == 3
        assert tbl.view().to_dict() == {
            "index": [0, 1, 2],
            "str": ["abc", None, "ghi"],
            "float": [None, 2, None]
        }

    def test_table_series(self):
        import pandas as pd
        data = pd.Series([1, 2, 3], name="a")
        tbl = Table(data)
        assert tbl.size() == 3

    def test_table_indexed_series(self):
        import pandas as pd
        data = pd.Series([1, 2, 3], index=["a", "b", "c"], name="a")
        tbl = Table(data)
        assert tbl.schema() == {
            "index": str,
            "a": int
        }
        assert tbl.size() == 3

    def test_rowpivots(self):
        df = superstore()
        df_pivoted = df.set_index(['Country', 'Region'])
        table = Table(df_pivoted)
        columns = table.columns()
        assert table.size() == 10
        assert "Country" in columns
        assert "Region" in columns

    def test_pivottable(self):
        df = superstore()
        pt = pd.pivot_table(df, values='Discount', index=['Country', 'Region'], columns='Category')
        table = Table(pt)
        columns = table.columns()
        assert "Country" in columns
        assert "Region" in columns

    def test_colpivots(self):
        arrays = [np.array(['bar', 'bar', 'bar', 'bar', 'baz', 'baz', 'baz', 'baz', 'foo', 'foo', 'foo', 'foo', 'qux', 'qux', 'qux', 'qux']),
                  np.array(['one', 'one', 'two', 'two', 'one', 'one', 'two', 'two', 'one', 'one', 'two', 'two', 'one', 'one', 'two', 'two']),
                  np.array(['X', 'Y', 'X', 'Y', 'X', 'Y', 'X', 'Y', 'X', 'Y', 'X', 'Y', 'X', 'Y', 'X', 'Y'])]
        tuples = list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples, names=['first', 'second', 'third'])

        df_both = pd.DataFrame(np.random.randn(3, 16), index=['A', 'B', 'C'], columns=index)
        table = Table(df_both)
        assert table.size() == 48
