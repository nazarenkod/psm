from aifashion.core.access import is_allowed


def test_allowed_via_static_list():
    assert is_allowed(111, static_whitelist={111, 222})


def test_allowed_via_db_list():
    assert is_allowed(333, static_whitelist={111}, db_allowed={333})


def test_denied_when_absent():
    assert not is_allowed(999, static_whitelist={111}, db_allowed={222})


def test_denied_with_empty_lists():
    assert not is_allowed(111)
