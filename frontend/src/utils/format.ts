import bytes from "bytes"
import _toNumber from "lodash/toNumber"
import dayjs from "@/utils/dayjs"

export function formatBytes(val: string | number) {
	return bytes(_toNumber(val))
}

export function formatDate(date: Date | string | number, format: string, opts?: { utc?: boolean; tz?: boolean }) {
	let parsedDate = date
	if (typeof date === "number" && date.toString().length >= 15) {
		parsedDate = date / 1000
	}

	let datejs = opts?.tz ? dayjs.utc(parsedDate) : dayjs(parsedDate)
	if (!datejs.isValid()) return date

	if (opts?.tz) {
		datejs = datejs.tz(dayjs.tz.guess())
	} else if (opts?.utc) {
		datejs = datejs.utc()
	}

	return datejs.format(format)
}
