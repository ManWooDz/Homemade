import test from "node:test";
import assert from "node:assert/strict";
import process from "node:process";
import { bangkokDate, daysUntilExpiry } from "../src/utils/expiry.js";

test("Bangkok midnight and calendar boundaries do not depend on the device timezone", () => {
    const before = new Date("2026-10-15T16:59:59Z");
    const after = new Date("2026-10-15T17:00:00Z");
    for (const zone of ["UTC", "America/Los_Angeles", "Asia/Tokyo"]) {
        process.env.TZ = zone;
        assert.equal(bangkokDate(before), "2026-10-15");
        assert.equal(bangkokDate(after), "2026-10-16");
        assert.equal(daysUntilExpiry("2026-10-16", before), 1);
        assert.equal(daysUntilExpiry("2026-10-16", after), 0);
        assert.equal(daysUntilExpiry("2026-10-15", after), -1);
    }
});
test("missing and malformed dates remain unknown; valid leap days retain calendar arithmetic", () => {
    for (const value of [null, "", "bad", "2026-02-30", "2026-99-99"]) assert.equal(daysUntilExpiry(value), null);
    assert.equal(daysUntilExpiry("2028-02-29", new Date("2028-02-28T03:00:00Z")), 1);
    assert.equal(daysUntilExpiry("2026-10-18", new Date("2026-10-15T03:00:00Z")), 3);
});
