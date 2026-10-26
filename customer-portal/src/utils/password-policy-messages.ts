import type { PasswordProblem } from "@/utils/password-policy"
import { i18nGlobal } from "@/lang"
import { passwordProblemCode } from "@/utils/password-policy"

/**
 * The password policy's texts in the user's language (#1310).
 *
 * `password-policy.ts` must stay byte-identical to the analyst frontend's copy (the backend's
 * `test_password_policy.py` compares them), so its English constants stay there and a form shows
 * these instead: the same rules, the same order, translated when they are read.
 */

const PROBLEM_KEYS = {
	control_character: "common.passwordPolicy.problems.controlCharacter",
	too_short: "common.passwordPolicy.problems.tooShort",
	too_long: "common.passwordPolicy.problems.tooLong",
	no_lowercase: "common.passwordPolicy.problems.noLowercase",
	no_uppercase: "common.passwordPolicy.problems.noUppercase",
	no_digit: "common.passwordPolicy.problems.noDigit",
	no_symbol: "common.passwordPolicy.problems.noSymbol"
} as const satisfies Record<PasswordProblem, string>

/** "8 to 72 characters, with an uppercase letter, …", translated. */
export function passwordRequirements(): string {
	return i18nGlobal.t("common.passwordPolicy.requirements")
}

/** The message for a rule the password breaks, translated. */
export function passwordProblemMessage(problem: PasswordProblem): string {
	return i18nGlobal.t(PROBLEM_KEYS[problem])
}

/** The translated message for the first rule the password breaks, or null when it meets the policy. */
export function translatedPasswordProblem(password: string): string | null {
	const code = passwordProblemCode(password)
	return code ? passwordProblemMessage(code) : null
}
