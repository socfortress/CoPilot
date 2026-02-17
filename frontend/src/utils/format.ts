import bytes from "bytes"
import _toNumber from "lodash/toNumber"
import dayjs from "@/utils/dayjs"

export function formatBytes(val: string | number) {
	return bytes(_toNumber(val))
}

export function formatDate(date: Date | string | number, format: string) {
	let parsedDate = date
	if (typeof date === "number" && date.toString().length >= 15) {
		parsedDate = date / 1000
	}
	const datejs = dayjs(parsedDate)
	if (!datejs.isValid()) return date

	return datejs.format(format)
}
