import type { AlertSourceContent, WazuhRuleExclude } from "@/types/alerts.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../../httpClient"

export default {
	wazuhManagerRuleExclude(source: AlertSourceContent) {
		return HttpClient.post<FlaskBaseResponse & WazuhRuleExclude>(`/wazuh_manager/rule/exclude`, {
			integration: "wazuh-rule-exclusion",
			prompt: source
		})
	}
}
