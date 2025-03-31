import type { OsTypesFull } from "@/types/common.d"
import type { Component } from "vue"
import process from "node:process"
import Icon from "@/components/common/Icon.vue"
import dayjs from "@/utils/dayjs"
import { isMobile as detectMobile } from "detect-touch-device"
import { md5 } from "js-md5"
import _trim from "lodash/trim"
import { h } from "vue"

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

export function isMobile() {
	return detectMobile
}

export function isUrlLike(text: string) {
	const urlPattern = /^https?:\/\//i
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
	if (test.includes("mac") || test.includes("darwin") || test.includes("apple")) {
		return "mdi:apple"
	}
	if (test.includes("win") || test.includes("microsoft")) {
		return "mdi:microsoft"
	}
	if (
		test.includes("linux") ||
		test.includes("unix") ||
		test.includes("x11") ||
		test.includes("debian") ||
		test.includes("centos")
	) {
		return "mdi:linux"
	}

	return "mdi:help-box"
}

export function getOS(): OsTypesFull {
	let os: OsTypesFull = "Unknown"
	if (navigator.userAgent.includes("Win")) os = "Windows"
	if (navigator.userAgent.includes("Mac")) os = "MacOS"
	if (navigator.userAgent.includes("X11")) os = "UNIX"
	if (navigator.userAgent.includes("Linux")) os = "Linux"

	return os
}

export function delay(t: number) {
	return new Promise(res => setTimeout(res, t))
}

export function hashMD5(text: number | string) {
	return md5(text.toString())
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

export function getAvatar(params: { seed: string; text?: string; size?: number; format?: "png" | "svg" }) {
	const format: "png" | "svg" = params.text ? "svg" : params.format || "svg"

	return `https://avatar.vercel.sh/${params.seed}.${format}?text=${params.text || ""}&size=${params.size || 32}`
}
