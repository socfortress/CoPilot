import type { AnnouncementsResponse } from "@/types/announcements"
import type { FlaskBaseResponse } from "@/types/flask"
import { HttpClient } from "../http-client"

export default {
	/** Not page-scoped: the toolbar asks once per session, whatever page it is on. */
	getAnnouncements() {
		return HttpClient.get<FlaskBaseResponse & AnnouncementsResponse>(`/announcements`, { keepOnNavigation: true })
	}
}
