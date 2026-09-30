// The backend's status:"error" message is shown to the user only when it is
// user-facing Thai copy. English/dev/raw-exception text ("API Key is missing",
// a bare KeyError, ...) must fall back to the generic heading only.
const THAI_CHAR = /[฀-๿]/;

export function toUserFacingGenerateError(message) {
    if (typeof message !== "string" || !THAI_CHAR.test(message)) return null;
    return message;
}
