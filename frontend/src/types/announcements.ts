/** SOCFortress announcements ("What's new"), as `GET /announcements` sends them. */
export type AnnouncementCategory = "product" | "release" | "advisory" | "event" | "promotion"

export interface AnnouncementCta {
	label: string
	/** Always https: the backend drops an item with any other link. */
	url: string
}

export interface Announcement {
	id: string
	category: AnnouncementCategory
	title: string
	summary: string
	body_markdown: string
	image_url: string | null
	image_alt: string
	cta: AnnouncementCta | null
	/** ISO 8601 with an offset. */
	published_at: string
	expires_at: string | null
	/** Shown in the sign-in modal when the user hasn't seen it yet. */
	popup: boolean
}

export interface AnnouncementsResponse {
	/** False when the deployment turned announcements off: no "What's new" entry at all. */
	enabled: boolean
	announcements: Announcement[]
}
