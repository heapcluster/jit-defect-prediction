"""统一响应包络与错误码的单元测试（app/errors.py）。

`ok` / `error_payload` 是全部接口的响应包络唯一定义点，锁死结构
（code/message/data 三字段）与 AppError 的 code/message 属性。
"""

from __future__ import annotations

from app.errors import AppError, error_payload, ok


def test_ok_envelope():
    assert ok({"a": 1}) == {"code": 0, "message": "ok", "data": {"a": 1}}


def test_ok_envelope_with_none_data():
    assert ok(None) == {"code": 0, "message": "ok", "data": None}


def test_error_payload_envelope():
    assert error_payload(40001, "参数非法") == {
        "code": 40001,
        "message": "参数非法",
        "data": None,
    }


def test_app_error_carries_code_and_message():
    err = AppError(40400, "commit not found")
    assert err.code == 40400
    assert err.message == "commit not found"
    assert isinstance(err, Exception)
