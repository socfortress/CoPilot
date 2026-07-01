import type { FlaskBaseResponse } from "@/types/flask"
import type { SidebarContextResponse } from "@/types/sidebar-context"
import { HttpClient } from "../http-client"

export default {
	getSidebarContext() {
		return HttpClient.get<FlaskBaseResponse & SidebarContextResponse>("/status/sidebar")
	}
}
