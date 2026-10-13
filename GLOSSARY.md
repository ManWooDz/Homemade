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

## Account Profile

**Application Language**:
The account holder's chosen Thai or English language for Homemade's interface, including controls and application messages. It does not change the original language of recipes, catalog content or text entered by the user.
_Avoid_: Recipe language, automatic recipe translation

**Profile Picture**:
An image uploaded by the account holder to represent their account in Homemade. It belongs to the account rather than a particular browser or device.
_Avoid_: Ingredient image, device-only avatar

**Display Name**:
The name an account holder chooses to see on their Homemade profile. Different account holders may use the same name; it is separate from their login email and need not be a legal name.
_Avoid_: Login username, unique account name, legal name
