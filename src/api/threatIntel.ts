import { HttpClient } from "./httpClient"
import type { FlaskBaseResponse } from "@/types/flask.d"
import type { ThreatIntelResponse } from "@/types/threatIntel.d"

export default {
	create(iocValue: string) {
		const body = {
			ioc_value: iocValue
		}
		return HttpClient.post<FlaskBaseResponse & { data: ThreatIntelResponse }>(`/threat_intel/socfortress`, body)
	}
}
