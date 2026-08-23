import test from "node:test";
import assert from "node:assert/strict";

import {
  isValidEmail,
  isValidPassword,
  passwordsMatch,
} from "../src/utils/authValidation.js";

test("isValidEmail accepts a normal address", () => {
  assert.equal(isValidEmail("user@example.com"), true);
});

test("isValidEmail rejects missing @ or domain", () => {
  assert.equal(isValidEmail("userexample.com"), false);
  assert.equal(isValidEmail("user@example"), false);
  assert.equal(isValidEmail(""), false);
});

test("isValidEmail trims surrounding whitespace before checking", () => {
  assert.equal(isValidEmail("  user@example.com  "), true);
});

test("isValidPassword requires at least 8 characters", () => {
  assert.equal(isValidPassword("short"), false);
  assert.equal(isValidPassword("longenough"), true);
});

test("passwordsMatch compares two values exactly", () => {
  assert.equal(passwordsMatch("abc12345", "abc12345"), true);
  assert.equal(passwordsMatch("abc12345", "different"), false);
});
