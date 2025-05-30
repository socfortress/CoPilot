import type {
	Artifact,
	CollectResult,
	CommandResult,
	MatchingParameter,
	QuarantineResult,
	Recommendation
} from "@/types/artifacts.d"
import type { OsTypesFull, OsTypesLower } from "@/types/common.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export interface ArtifactsQuery {
	os?: OsTypesLower
	hostname?: string
}

export interface CollectRequest {
	hostname: string
	velociraptor_id?: string
	artifact_name: string
	parameters?: {
		env?: {
			key: string
			value: string
		}[]
	}
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
	prompt: string | object
}

export default {
	getAll(filters?: ArtifactsQuery) {
		let url = "/artifacts"

		if (filters?.os) {
			url = `/artifacts/${filters.os}`
		}
		if (filters?.hostname) {
			url = `/artifacts/hostname/${filters.hostname}`
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
	},
	getParameters(artifactName: string, parameterPrefix: string) {
		return HttpClient.post<
			FlaskBaseResponse & {
				artifact_name: string
				parameter_prefix: string
				matching_parameters: MatchingParameter[]
				total_matches: number
			}
		>(`/artifacts/artifact/${artifactName}/parameters/${parameterPrefix}`)
	}
}
