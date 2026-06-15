import type {
	AuthenticationResponseJSON,
	PublicKeyCredentialCreationOptionsJSON,
	PublicKeyCredentialRequestOptionsJSON,
	RegistrationResponseJSON
} from "@simplewebauthn/browser"
import { browserSupportsWebAuthn, startAuthentication, startRegistration } from "@simplewebauthn/browser"
import Api from "@/api"

function stripRegisterOptions(options: Record<string, unknown>): PublicKeyCredentialCreationOptionsJSON {
	const { challengeToken: _token, deviceName: _name, ...webauthnOptions } = options
	return webauthnOptions as unknown as PublicKeyCredentialCreationOptionsJSON
}

function stripLoginOptions(options: Record<string, unknown>): PublicKeyCredentialRequestOptionsJSON {
	const { challengeToken: _token, ...webauthnOptions } = options
	return webauthnOptions as unknown as PublicKeyCredentialRequestOptionsJSON
}

const IGNORED_UA_BRANDS = new Set(["not.a/brand", "not)a;brand", "chromium"])

function normalizeLabel(value: string): string {
	return value.trim().toLowerCase().replace(/\s+/g, " ")
}

function detectBrowserName(userAgent: string): string {
	if (/edg\//i.test(userAgent)) return "edge"
	if (/firefox\//i.test(userAgent)) return "firefox"
	if (/chrome\//i.test(userAgent) && !/edg\//i.test(userAgent)) return "chrome"
	if (/safari\//i.test(userAgent) && !/chrome\//i.test(userAgent)) return "safari"
	return "browser"
}

function detectPlatformName(userAgent: string): string {
	if (/iphone|ipad|ipod/i.test(userAgent)) return "ios"
	if (/android/i.test(userAgent)) return "android"
	if (/mac/i.test(userAgent)) return "macos"
	if (/win/i.test(userAgent)) return "windows"
	if (/linux/i.test(userAgent)) return "linux"
	return normalizeLabel(navigator.platform || "unknown")
}

interface NavigatorUAData {
	brands: Array<{ brand: string; version: string }>
	platform: string
}

export function getDefaultPasskeyDeviceName(): string {
	const uaData = (navigator as Navigator & { userAgentData?: NavigatorUAData }).userAgentData

	if (uaData) {
		const browserBrand = uaData.brands.find(
			({ brand }: { brand: string }) => !IGNORED_UA_BRANDS.has(brand.toLowerCase())
		)?.brand
		const browser = browserBrand
			? normalizeLabel(browserBrand).replace(/^google /, "")
			: detectBrowserName(navigator.userAgent)
		const platform = uaData.platform ? normalizeLabel(uaData.platform) : detectPlatformName(navigator.userAgent)
		return `${browser} ${platform}`
	}

	return `${detectBrowserName(navigator.userAgent)} ${detectPlatformName(navigator.userAgent)}`
}

export function isPasskeyOriginSupported(): boolean {
	return window.location.hostname !== "127.0.0.1"
}

export function getPasskeyLocalhostUrl(): string {
	const { protocol, port, pathname, search, hash } = window.location
	const portSuffix = port ? `:${port}` : ""
	return `${protocol}//localhost${portSuffix}${pathname}${search}${hash}`
}

export function getPasskeyOriginError(): string | null {
	if (!isPasskeyOriginSupported()) {
		return `Le passkey non funzionano su 127.0.0.1. Apri ${getPasskeyLocalhostUrl()} nel browser.`
	}
	return null
}

export function usePasskeySupport() {
	return {
		isSupported: browserSupportsWebAuthn(),
		originSupported: isPasskeyOriginSupported(),
		localhostUrl: getPasskeyLocalhostUrl()
	}
}

function assertPasskeyOrigin() {
	const error = getPasskeyOriginError()
	if (error) {
		throw new Error(error)
	}
}

export async function registerPasskey(deviceName = "Passkey") {
	assertPasskeyOrigin()
	const optionsRes = await Api.passkey.registerOptions({ device_name: deviceName })
	const { challengeToken, deviceName: savedName, ...rawOptions } = optionsRes.data
	const credential = await startRegistration({
		optionsJSON: stripRegisterOptions(rawOptions as Record<string, unknown>)
	})

	await Api.passkey.registerVerify({
		challenge_token: challengeToken,
		credential: credential as RegistrationResponseJSON,
		device_name: savedName || deviceName
	})
}

export async function loginWithPasskey(username?: string) {
	assertPasskeyOrigin()
	const optionsRes = await Api.passkey.loginOptions(username ? { username } : {})
	const { challengeToken, ...rawOptions } = optionsRes.data
	const credential = await startAuthentication({
		optionsJSON: stripLoginOptions(rawOptions as Record<string, unknown>)
	})

	const verifyRes = await Api.passkey.loginVerify({
		challenge_token: challengeToken,
		credential: credential as AuthenticationResponseJSON
	})

	return verifyRes.data
}
