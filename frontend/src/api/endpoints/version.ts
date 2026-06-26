import type { FlaskBaseResponse } from "@/types/flask"
import type { VersionCheckResponse } from "@/types/version"
import { HttpClient } from "../http-client"

export default {
	checkVersion() {
		return HttpClient.get<FlaskBaseResponse & VersionCheckResponse>(`/version/check`)
	}
}
