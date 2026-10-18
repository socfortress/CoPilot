/**
 * The password policy: the same rules as the API's `backend/app/auth/schema/password_policy.py` (#1265).
 *
 * This file is identical in `frontend/` and `customer-portal/` (`backend/tests/test_password_policy.py` checks),
 * and each copy is tested against the cases the backend uses (`__tests__/fixtures/password-policy-cases.json`),
 * so a form never accepts a password the API refuses, or the other way round. Any character is allowed; the
 * rules below are checked in order and the first that fails is reported. The Python module says why each exists.
 */

export const MIN_PASSWORD_CHARACTERS = 8
export const MAX_PASSWORD_BYTES = 72

export const PASSWORD_REQUIREMENTS =
	"8 to 72 characters, with an uppercase letter, a lowercase letter, a digit and a symbol"

export const PASSWORD_PROBLEMS = {
	control_character: "Password must not contain control or invisible characters",
	too_short: "Password must be at least 8 characters long",
	too_long: "Password must be at most 72 bytes long (an accented letter takes 2, an emoji 4)",
	no_lowercase: "Password must contain a lowercase letter",
	no_uppercase: "Password must contain an uppercase letter",
	no_digit: "Password must contain a digit",
	no_symbol: "Password must contain a symbol, such as ! @ # $ % _ - . or +"
} as const

export type PasswordProblem = keyof typeof PASSWORD_PROBLEMS

// Unicode general categories, as Python's unicodedata.category() names them.
const REFUSED = /[\p{Cc}\p{Cf}\p{Cs}]/u
const LOWERCASE = /\p{Ll}/u
const UPPERCASE = /\p{Lu}/u
const DIGIT = /\p{Nd}/u
const SYMBOL = /[\p{P}\p{S}]/u

/** The first rule the password breaks, or null. */
export function passwordProblemCode(password: string): PasswordProblem | null {
	if (REFUSED.test(password)) return "control_character"
	// Code points, like Python's len(): an emoji is one character, not two UTF-16 units.
	if (Array.from(password).length < MIN_PASSWORD_CHARACTERS) return "too_short"
	// bcrypt's limit is in bytes of UTF-8.
	if (new TextEncoder().encode(password).length > MAX_PASSWORD_BYTES) return "too_long"
	if (!LOWERCASE.test(password)) return "no_lowercase"
	if (!UPPERCASE.test(password)) return "no_uppercase"
	if (!DIGIT.test(password)) return "no_digit"
	if (!SYMBOL.test(password)) return "no_symbol"
	return null
}

/** The message for the first rule the password breaks, or null when it meets the policy. */
export function passwordProblem(password: string): string | null {
	const code = passwordProblemCode(password)
	return code ? PASSWORD_PROBLEMS[code] : null
}
