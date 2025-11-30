import { httpClient } from "@/utils/httpClient"

export interface CaseDataStoreFile {
	id: number
	case_id: number
	bucket_name: string
	object_key: string
	file_name: string
	content_type: string | null
	file_size: number | null
	upload_time: string
	file_hash: string
}

export interface CaseDataStoreResponse {
	case_data_store: CaseDataStoreFile[]
	success: boolean
	message: string
}

export class CaseDataStoreAPI {
	/**
	 * Get files associated with a specific case
	 */
	static async getCaseFiles(caseId: number): Promise<CaseDataStoreResponse> {
		const response = await httpClient.get(`/incidents/db_operations/case/data-store/${caseId}`)
		return response.data
	}

	/**
	 * Download a specific file from a case
	 * Returns the blob data for download
	 */
	static async downloadCaseFile(caseId: number, fileName: string): Promise<Blob> {
		const response = await httpClient.get(
			`/incidents/db_operations/case/data-store/download/${caseId}/${fileName}`,
			{
				responseType: "blob"
			}
		)
		return response.data
	}

	/**
	 * Upload a file to a case data store
	 */
	static async uploadCaseFile(caseId: number, file: File): Promise<CaseDataStoreResponse> {
		const formData = new FormData()
		formData.append("file", file)

		const response = await httpClient.post(
			`/incidents/db_operations/case/data-store/upload?case_id=${caseId}`,
			formData,
			{
				headers: {
					"Content-Type": "multipart/form-data"
				}
			}
		)
		return response.data
	}

	/**
	 * Trigger file download in browser
	 */
	static downloadFileBlob(blob: Blob, fileName: string): void {
		const url = window.URL.createObjectURL(blob)
		const link = document.createElement("a")
		link.href = url
		link.setAttribute("download", fileName)
		document.body.appendChild(link)
		link.click()
		link.remove()
		window.URL.revokeObjectURL(url)
	}

	/**
	 * Format file size for display
	 */
	static formatFileSize(bytes: number | null): string {
		if (!bytes) return "Unknown size"

		const sizes = ["Bytes", "KB", "MB", "GB"]
		if (bytes === 0) return "0 Bytes"

		const i = Math.floor(Math.log(bytes) / Math.log(1024))
		return Math.round((bytes / Math.pow(1024, i)) * 100) / 100 + " " + sizes[i]
	}
}

export default CaseDataStoreAPI
