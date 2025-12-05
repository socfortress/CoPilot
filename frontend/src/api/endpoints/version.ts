import type { FlaskBaseResponse } from "@/types/flask.d"
import type { VersionCheckResponse } from "@/types/version.d"
import { HttpClient } from "../httpClient"

export default {
	checkVersion() {
		return HttpClient.get<FlaskBaseResponse & VersionCheckResponse>(`/version/check`)
	}
}
