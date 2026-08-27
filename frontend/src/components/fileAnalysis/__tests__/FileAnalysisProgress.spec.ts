import type { FileAnalysisJob } from "@/types/file-analysis"
import { mount } from "@vue/test-utils"
import { describe, expect, it } from "vitest"
import FileAnalysisProgress from "../FileAnalysisProgress.vue"

// The mock fixture is always "done", so this panel never renders on the review
// page. These cover the states an analyst actually waits through.
function job(over: Partial<FileAnalysisJob> = {}): FileAnalysisJob {
	return {
		job_id: "j1",
		sha256: "a".repeat(64),
		filename: "sample.docm",
		customer_code: "00001",
		source: "upload",
		status: "running",
		static_status: "running",
		sandbox_enabled: false,
		hardened: true,
		...over
	}
}

function mountPanel(props: { job: FileAnalysisJob | null; reputationPending?: boolean }) {
	return mount(FileAnalysisProgress, {
		props,
		global: { stubs: { Icon: true, "n-spin": true } }
	})
}

describe("fileAnalysisProgress", () => {
	it("names the running stage in the headline", () => {
		const w = mountPanel({ job: job({ static_status: "running" }) })
		expect(w.text()).toContain("Static inspection in progress")
	})

	it("hides the detonation step when no sandbox is configured", () => {
		const w = mountPanel({ job: job({ sandbox_enabled: false }) })
		expect(w.text()).not.toContain("Detonation")
	})

	it("shows detonation as the running stage once the static tier is done", () => {
		const w = mountPanel({
			job: job({ static_status: "done", sandbox_enabled: true, dynamic_status: "running" })
		})
		expect(w.text()).toContain("Detonation in progress")
		expect(w.text()).toContain("takes a few minutes")
	})

	it("reports a failed static tier instead of an endless wait", () => {
		const w = mountPanel({ job: job({ static_status: "failed" }) })
		expect(w.text()).toContain("could not parse")
		expect(w.text()).not.toContain("Static inspection in progress")
	})

	it("keeps reputation running while a submitted scan has not come back", () => {
		const w = mountPanel({ job: job({ static_status: "done" }), reputationPending: true })
		expect(w.text()).toContain("Waiting on the VirusTotal scan")
		expect(w.text()).toContain("Reputation in progress")
	})
})
