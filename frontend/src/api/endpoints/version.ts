import type { FlaskBaseResponse } from "@/types/flask"
import type { VersionCheckResponse } from "@/types/version"
import { HttpClient } from "../httpClient"

export default {
	checkVersion() {
		return HttpClient.get<FlaskBaseResponse & VersionCheckResponse>(`/version/check`)
	}
}
