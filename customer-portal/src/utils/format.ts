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

/**
 * `tz: true` parses the value as UTC before converting it to the viewer's timezone. That is what
 * makes offset-less timestamps — which several event sources emit — read as UTC instead of as local
 * time; without it they render as the raw UTC clock and appear shifted by the viewer's offset.
 * `utc: true` renders in UTC instead. Mirrors `formatDate` in the analyst frontend.
 */
export function formatDate(date: Date | string | number, format: string, opts?: { utc?: boolean; tz?: boolean }) {
	const parsedDate = isTimestamp(date, true) ?? date

	let dateJs = opts?.tz ? dayjs.utc(parsedDate) : dayjs(parsedDate)

	if (!dateJs.isValid()) return date

	if (opts?.tz) {
		dateJs = dateJs.tz(dayjs.tz.guess())
	} else if (opts?.utc) {
		dateJs = dateJs.utc()
	}

	if (format === "x") {
		return dateJs.valueOf()
	}

	return dateJs.format(format)
}

export function formatTimeAgo(date: Date | string | number, format: string) {
	const timestamp = formatDate(date, "x") as number

	try {
		const now = new Date()
		const diffInMs = now.getTime() - timestamp

		const days = diffInMs / (1000 * 60 * 60 * 24)

		if (days < 30) {
			return dayjs(timestamp).fromNow()
		} else {
			return formatDate(timestamp, format)
		}
	} catch {
		return "Invalid date"
	}
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
