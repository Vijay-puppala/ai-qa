"""Tests derived from DC-11: Build login screen UI with validation and password visibility toggle

generated-by: ai-qa
ticket: DC-11
ticket-summary: Build login screen UI with validation and password visibility toggle
ticket-updated:
ticket-digest: e794656c8730
generated-at: 2026-10-04T06:33:43Z
generated-by-identity: vijayanand.hyd@gmail.com
approval: DC-11/20261004T063740Z-approved
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from ai_qa.pages.login import LoginPage

pytestmark = [pytest.mark.ui, pytest.mark.ticket("DC-11")]


@pytest.fixture
def login(page: Page, base_url: str) -> LoginPage:
    return LoginPage(page, base_url).open()


# --- ai-qa: generated test functions below ---


def test_login_form_presents_every_required_control(login: LoginPage) -> None:
    """The login page shows an email/username field, a password field, a Login
    button and a Forgot Password link.

    From DC-11: "Implement the login page with Email/Username and Password
    fields, Login button, Forgot Password link".
    """
    expect(login.email).to_be_visible()
    expect(login.password).to_be_visible()
    expect(login.submit_button).to_be_visible()
    expect(login.forgot_password_link).to_be_visible()


def test_password_is_masked_by_default(login: LoginPage) -> None:
    """The password field hides its contents until the user asks otherwise.

    The show/hide control in DC-11 only means anything if the default is
    hidden, so this is asserted separately from the toggle itself.
    """
    login.password.fill("hunter2")
    assert login.password_is_masked(), "password field is not masked by default"


def test_visibility_toggle_reveals_and_re_masks_the_password(login: LoginPage) -> None:
    """Activating the show/hide control reveals the typed password, and
    activating it again masks it.

    From DC-11: "show/hide password control". Both directions are asserted -
    a toggle that reveals but cannot re-mask leaves the password on screen.
    """
    login.password.fill("hunter2")
    expect(login.visibility_toggle.first).to_be_visible()

    login.visibility_toggle.first.click()
    assert not login.password_is_masked(), "toggle did not reveal the password"

    login.visibility_toggle.first.click()
    assert login.password_is_masked(), "toggle did not re-mask the password"


def test_submitting_an_empty_email_shows_a_required_field_message(
    login: LoginPage,
) -> None:
    """Leaving email/username blank and submitting shows a required-field
    validation message naming that field, and does not attempt to log in.

    From DC-11: "client-side required-field ... validation messages".
    """
    login.password.fill("hunter2")
    login.submit()

    assert login.native_validation_message(login.email), (
        "no required-field validation message for an empty email"
    )
    expect(login.page).to_have_url(login.url)


def test_submitting_an_empty_password_shows_a_required_field_message(
    login: LoginPage,
) -> None:
    """Leaving the password blank and submitting shows a required-field
    validation message naming that field, and does not attempt to log in.

    Separate from the email case: a form that validates one field and not the
    other satisfies neither requirement.
    """
    login.email.fill("someone@example.com")
    login.submit()

    assert login.native_validation_message(login.password), (
        "no required-field validation message for an empty password"
    )
    expect(login.page).to_have_url(login.url)


def test_a_malformed_email_shows_a_format_validation_message(
    login: LoginPage,
) -> None:
    """Entering a value that is not a valid email address shows a format
    validation message distinct from the required-field message.

    From DC-11: "format validation messages". The message must differ from the
    empty-field one, or the user cannot tell what is wrong.
    """
    login.email.fill("")
    login.password.fill("hunter2")
    login.submit()
    required_message = login.native_validation_message(login.email)

    login.email.fill("not-an-email")
    login.submit()
    format_message = login.native_validation_message(login.email)

    assert format_message, "no format validation message for a malformed email"
    assert format_message != required_message, (
        "the malformed-email message is identical to the empty-field message, "
        "so the user cannot tell which problem they have"
    )


def test_validation_messages_clear_once_the_input_is_corrected(
    login: LoginPage,
) -> None:
    """A validation message disappears after the user fixes the offending
    field.

    Not stated explicitly in DC-11, but a validation message that persists
    after correction reads as an unfixable error. Flagged for the reviewer:
    remove this test if the ticket does not intend it.
    """
    login.email.fill("not-an-email")
    login.password.fill("hunter2")
    login.submit()
    assert login.native_validation_message(login.email), "expected a message to clear"

    login.email.fill("someone@example.com")

    assert not login.native_validation_message(login.email), (
        "validation message persisted after the input was corrected"
    )


def test_duplicate_submission_is_prevented_while_authenticating(
    login: LoginPage,
) -> None:
    """Once Login is submitted, further submissions are refused until
    authentication finishes.

    From DC-11: "prevent duplicate submissions while authentication is in
    progress". This is the requirement most likely to be implemented as a
    disabled button but still reachable by pressing Enter, so the test must
    cover more than the button's visual state.
    """
    requests: list[str] = []
    login.page.on(
        "request",
        lambda r: requests.append(r.url) if r.method == "POST" else None,
    )

    login.email.fill("nobody@example.com")
    login.password.fill("wrongpassword123")

    login.submit()
    login.page.keyboard.press("Enter")
    login.submit_button.click(force=True)
    login.page.wait_for_timeout(2500)

    assert len(requests) <= 1, (
        f"{len(requests)} authentication requests were sent for one login "
        f"attempt - duplicate submissions are not being prevented"
    )


def test_forgot_password_link_navigates_away_from_the_login_form(
    login: LoginPage,
) -> None:
    """Activating Forgot Password takes the user to the recovery flow.

    DC-11 requires the link to exist; this asserts it does something. The
    destination's own behaviour belongs to whichever ticket covers recovery.
    """
    expect(login.forgot_password_link).to_be_visible()
    login.forgot_password_link.click()

    expect(login.page).not_to_have_url(login.url)
