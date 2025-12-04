export interface VersionCheckResponse {
    success: boolean
    message: string
    current_version: string
    latest_version: string | null
    is_outdated: boolean
    release_url?: string
    release_notes?: string
    published_at?: string
}
