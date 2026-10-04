# Homemade

Canonical language for Homemade's recipe and account-recovery domain. Terms here describe product meaning, not implementation details.

## Password Recovery

**Password-reset OTP**:
A short-lived, six-digit one-time code used to prove control of the email address associated with an account.
_Avoid_: Reset token, email token, verification email

**Delivery Accepted**:
The email provider has accepted a password-reset message for delivery; this does not mean the message reached the recipient's inbox.
_Avoid_: Delivered, received, inbox-confirmed

**Delivery Unconfirmed**:
The system did not receive reliable confirmation that the email provider accepted a password-reset message; this does not prove that the provider rejected or failed to send it.
_Avoid_: Not sent, definitely failed, rejected

**Reset Ticket**:
A short-lived, single-use proof issued after a correct password-reset OTP is verified, authorizing one password change.
_Avoid_: OTP, access token, reset OTP

**Generic Authentication Response**:
An outward response whose status and shape do not reveal whether an account exists or whether password-reset delivery succeeded.
_Avoid_: Success confirmation, delivery confirmation
