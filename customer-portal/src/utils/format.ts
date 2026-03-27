import bytes from "bytes"
import { md5 } from "js-md5"
import _split from "lodash/split"
import _toNumber from "lodash/toNumber"
import dayjs from "@/utils/dayjs"
import { isTimestamp } from "@/utils/index"

const COMMA_REGEX = /,/g

export function formatBytes(val: string | number) {
	return bytes(_toNumber(val))
}
// Transform File Instance in base64 string
export function file2Base64(blob: Blob): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader()
		reader.readAsDataURL(blob)
		reader.onload = () => resolve(reader.result as string)
		reader.onerror = error => reject(error)
	})
}

export function hashMD5(text: number | string) {
	return md5(text.toString())
}

export function formatDate(date: Date | string | number, format: string) {
	const parsedDate = isTimestamp(date, true) ?? date

	const dateJs = dayjs(parsedDate)

	if (!dateJs.isValid()) return date

	if (format === "x") {
		return dateJs.valueOf()
	}

	return dateJs.format(format)
}

export function getNameInitials(name: string, cap?: number) {
	let initials = name.slice(0, 2)

	if (name.includes(" ")) {
		initials = name
			.split(" ")
			.map(chunk => chunk[0])
			.join()
	}

	return (cap ? initials.slice(0, cap) : initials).toUpperCase()
}

/**
 * Converts a value to a boolean.
 * Returns true if the value is "1" or "true", otherwise false.
 *
 * @param {string | boolean | number | null} [val] - The value to convert to boolean
 * @returns {boolean} The resulting boolean value
 *
 * @example
 * toBoolean("1") // true
 * toBoolean("true") // true
 * toBoolean("0") // false
 * toBoolean(null) // false
 */
export function toBoolean(val?: string | boolean | number | null): boolean {
	const cast = (val || 0).toString()
	if (cast === "1") return true
	if (cast === "true") return true

	return false
}

/**
 * Converts a string or number to a decimal number.
 * Replaces commas with dots and properly handles decimal separators.
 *
 * @param {string | number} input - The value to convert to a number
 * @returns {number} The converted number
 *
 * @example
 * toNumber("123,45") // 123.45
 * toNumber("123.45") // 123.45
 * toNumber(123) // 123
 */
export function toNumber(input: string | number): number {
	return _toNumber(_split(`${input}`.replace(COMMA_REGEX, "."), ".", 2).join("."))
}
