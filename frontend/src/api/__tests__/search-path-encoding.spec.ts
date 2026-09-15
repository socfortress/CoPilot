/**
 * Search terms that reach the backend through a URL *path* segment (#1133).
 *
 * Typing `C:\` into the Ctrl+K palette used to log the user out. The alerts
 * provider interpolated the query straight into `/alerts/title/<query>`; the
 * browser rewrote the backslash into a slash, the backend answered with a 307 to
 * an absolute `http://` URL, the browser followed it without the Authorization
 * header, and the resulting 401 was read as an expired session. Encoding the
 * segment keeps the query a single segment — the request never needs to be
 * redirected at all.
 *
 * Each test asserts on the URL the adapter received, which is what the browser
 * would parse: a regression would show up here before it could reach nginx.
 */

import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios"
import axios from "axios"
import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/stores/auth", () => ({
	useAuthStore: () => ({ userToken: null, refreshToken: vi.fn() })
}))

const { HttpClient } = await import("../http-client")
const alerts = (await import("../endpoints/incidentManagement/alerts")).default
const cases = (await import("../endpoints/incidentManagement/cases")).default
const artifacts = (await import("../endpoints/artifacts")).default

/** Answers every request with an empty 200 and records the URI axios built. */
function recordingAdapter(seen: string[]): AxiosAdapter {
	return (config: InternalAxiosRequestConfig) => {
		seen.push(axios.getUri(config))
		return Promise.resolve({ data: {}, status: 200, statusText: "OK", headers: {}, config })
	}
}

describe("search terms interpolated into a path segment are percent-encoded", () => {
	const seen: string[] = []

	beforeEach(() => {
		setActivePinia(createPinia())
		seen.length = 0
		HttpClient.defaults.adapter = recordingAdapter(seen)
	})

	it("keeps a backslash in an alert title search inside one path segment", async () => {
		await alerts.getAlertsList({ filter: { title: "C:\\" }, page: 1, pageSize: 5 })

		expect(seen[0]).toContain("/incidents/db_operations/alerts/title/C%3A%5C?")
		// The browser would have turned a raw backslash into a second slash.
		expect(seen[0]).not.toContain("title/C:")
	})

	it("encodes every alert path filter, not only the title", async () => {
		await alerts.getAlertsList({ filter: { assetName: "host/with space" } })
		await alerts.getAlertsList({ filter: { assignedTo: "user@x.y" } })
		await alerts.getAlertsList({ filter: { source: "office 365" } })
		await alerts.getAlertsList({ filter: { tag: ["a/b", "c d"] } })

		expect(seen[0]).toContain("/alerts/asset/host%2Fwith%20space?")
		expect(seen[1]).toContain("/alerts/assigned-to/user%40x.y?")
		expect(seen[2]).toContain("/alerts/source/office%20365?")
		// Tags stay comma-joined for the backend; only each tag is encoded.
		expect(seen[3]).toContain("/alert/tag/a%2Fb,c%20d?")
	})

	it("encodes the free-text case and artifact path filters", async () => {
		await cases.getCasesList({ hostname: "srv\\01" })
		await cases.getCasesList({ assignedTo: "a b" })
		await artifacts.getAll({ hostname: "srv\\01" })
		await artifacts.getByName("Windows.Sys.Users/x")

		expect(seen[0]).toContain("/agents/srv%5C01/cases")
		expect(seen[1]).toContain("/case/assigned-to/a%20b")
		expect(seen[2]).toContain("/artifacts/hostname/srv%5C01")
		expect(seen[3]).toContain("/artifacts/artifact/Windows.Sys.Users%2Fx")
	})
})
