import pytest
from aws_lambda_powertools.utilities.parser import ValidationError
from shared.models.invite_request import InviteRequest


def test_invalid_mobile():
    # Given an invalid mobile number
    mobile = "abc"
    first_name = "Joe"
    last_name = "Bloggs"

    # When InviteRequest is initialized then expect ValidationError
    with pytest.raises(ValidationError):
        InviteRequest(first_name=first_name, last_name=last_name, mobile=mobile)
