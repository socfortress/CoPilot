import { type FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "./httpClient"
import type { License, LicenseFeatures, LicenseKey } from "@/types/license"

export default {
	getLicense() {
		return HttpClient.get<FlaskBaseResponse & { license_key: LicenseKey }>(`/license/get_license`)
	},
	verifyLicense() {
		return HttpClient.get<FlaskBaseResponse & { license: License }>(`/license/verify_license`)
	},
	getLicenseFeatures() {
		return HttpClient.get<FlaskBaseResponse & { features: LicenseFeatures[] }>(`/license/get_license_features`)
	},
	replaceLicense(license_key: LicenseKey) {
		return HttpClient.post<FlaskBaseResponse>(`/license/replace_license_in_db`, {
			license_key
		})
	},
	extendLicense(period: number) {
		return HttpClient.post<FlaskBaseResponse>(
			`/license/extend_license`,
			{},
			{
				params: { period }
			}
		)
	}
}
