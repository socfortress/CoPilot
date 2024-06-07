import Icon from "@/components/common/Icon.vue"
import { type Component, h } from "vue"
import { isMobile as detectMobile } from "detect-touch-device"
import { md5 } from "js-md5"
import dayjs from "@/utils/dayjs"
import type { OsTypesFull } from "@/types/common"
import _trim from "lodash/trim"

// Transform File Instance in base64 string
export function file2Base64(blob: Blob): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader()
		reader.readAsDataURL(blob)
		reader.onload = () => resolve(reader.result as string)
		reader.onerror = error => reject(error)
	})
}
export function isEnvDev() {
	return process.env.NODE_ENV === "development"
}
export function isEnvTest() {
	return process.env.NODE_ENV === "test"
}
export function isEnvProd() {
	return process.env.NODE_ENV === "production"
}

export const isMobile = () => {
	return detectMobile
}

export const isUrlLike = (text: string) => {
	const urlPattern = new RegExp("^(https?:\\/\\/)", "i")
	return urlPattern.test(text)
}

export function renderIcon(icon: Component | string) {
	if (typeof icon === "string") {
		return () => h(Icon, { name: icon })
	} else {
		return () => h(Icon, null, { default: () => h(icon) })
	}
}

export function iconFromOs(os: string): string {
	const test = os.toLowerCase()
	if (test.indexOf("mac") !== -1 || test.indexOf("darwin") !== -1 || test.indexOf("apple") !== -1) {
		return "mdi:apple"
	}
	if (test.indexOf("win") !== -1 || test.indexOf("microsoft") !== -1) {
		return "mdi:microsoft"
	}
	if (
		test.indexOf("linux") !== -1 ||
		test.indexOf("unix") !== -1 ||
		test.indexOf("x11") !== -1 ||
		test.indexOf("debian") !== -1 ||
		test.indexOf("centos") !== -1
	) {
		return "mdi:linux"
	}

	return "mdi:help-box"
}

export function getOS(): OsTypesFull {
	let os: OsTypesFull = "Unknown"
	if (navigator.userAgent.indexOf("Win") != -1) os = "Windows"
	if (navigator.userAgent.indexOf("Mac") != -1) os = "MacOS"
	if (navigator.userAgent.indexOf("X11") != -1) os = "UNIX"
	if (navigator.userAgent.indexOf("Linux") != -1) os = "Linux"

	return os
}

export const delay = (t: number) => {
	return new Promise(res => setTimeout(res, t))
}

export const hashMD5 = (text: number | string) => {
	return md5(text.toString())
}

export function formatDate(date: Date | string | number, format: string) {
	let parsedDate = date
	if (typeof date === "number" && date.toString().length === 10) {
		parsedDate = date * 1000
	}
	const datejs = dayjs(parsedDate)
	if (!datejs.isValid()) return date

	return datejs.format(format)
}

export function price(
	amount: number,
	options: { currency?: "USD" | "EUR"; splitDecimal?: boolean } = { currency: "USD", splitDecimal: true }
) {
	let symbol = ""
	switch (options.currency) {
		case "USD":
			symbol = "$"
			break
		case "EUR":
			symbol = "€"
			break
	}

	const price = options.splitDecimal ? (amount / 100).toFixed(2) : amount

	return `${symbol}${price}`
}

export function getBaseUrl() {
	return _trim(import.meta.env.VITE_API_URL, "/")
}
