import { HttpClient } from "./httpClient"
import type { FlaskBaseResponse } from "@/types/flask.d"
import type { Artifact, CollectResult, CommandResult, QuarantineResult, Recommendation } from "@/types/artifacts.d"
import type { AlertContext } from "@/types/soc/alert"
import type { OsTypesFull, OsTypesLower } from "@/types/common"

export interface ArtifactsQuery {
	os?: OsTypesLower
	hostname?: string
}

export interface CollectRequest {
	hostname: string
	velociraptor_id?: string
	artifact_name: string
}

export interface CommandRequest {
	hostname: string
	velociraptor_id?: string
	command: string
	artifact_name: "Windows.System.PowerShell" | "Windows.System.CmdShell" | "Linux.Sys.BashShell"
}

export interface QuarantineRequest {
	hostname: string
	velociraptor_id?: string
	action: "quarantine" | "remove_quarantine"
	artifact_name: "Windows.Remediation.Quarantine" | "Linux.Remediation.Quarantine"
}

export interface ArtifactRecommendationRequest {
	os: OsTypesFull
	prompt: AlertContext
}

export default {
	getAll(filters?: ArtifactsQuery) {
		let url = "/artifacts"

		if (filters?.os) {
			url = "/artifacts/" + filters.os
		}
		if (filters?.hostname) {
			url = "/artifacts/hostname/" + filters.hostname
		}

		return HttpClient.get<FlaskBaseResponse & { artifacts: Artifact[] }>(url)
	},
	collect(payload: CollectRequest) {
		return HttpClient.post<FlaskBaseResponse & { results: CollectResult[] }>(`/artifacts/collect`, payload)
	},
	command(payload: CommandRequest) {
		return HttpClient.post<FlaskBaseResponse & { results: CommandResult[] }>(`/artifacts/command`, payload)
	},
	quarantine(payload: QuarantineRequest) {
		return HttpClient.post<FlaskBaseResponse & { results: QuarantineResult[] }>(`/artifacts/quarantine`, payload)
	},
	getArtifactRecommendation(payload: ArtifactRecommendationRequest) {
		return HttpClient.post<FlaskBaseResponse & { recommendations: Recommendation[] }>(
			`/artifacts/velociraptor-artifact-recommendation`,
			payload
		)
	}
}
