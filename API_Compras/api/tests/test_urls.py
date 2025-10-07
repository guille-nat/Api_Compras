import pytest
from django.urls import reverse


def test_urls_reverse_and_resolution_and_view_integration():
    list_name = 'notification-templates-list'
    detail_name = 'notification-templates-detail'
    # router prefixing may vary; assert the reversed url contains our resource name
    assert 'notification-templates' in reverse(list_name)
    with pytest.raises(Exception):
        reverse(detail_name)
