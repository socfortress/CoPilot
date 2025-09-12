import type { FlaskBaseResponse } from "@/types/flask.d"
import type { WazuhGroup, WazuhGroupConfigurationUpdate, WazuhGroupFile, WazuhGroupFileDetails } from "@/types/wazuh/groups.d"
import { HttpClient } from "../../httpClient"

// Interface for groups query parameters
export interface GroupsQueryParams {
	/** Show results in human-readable format */
	pretty?: boolean
	/** Disable timeout response */
	wait_for_complete?: boolean
	/** List of group IDs (separated by comma) */
	groups_list?: string[]
	/** First element to return in the collection */
	offset?: number
	/** Maximum number of elements to return */
	limit?: number
	/** Sort the collection by a field or fields */
	sort?: string | null
	/** Look for elements containing the specified string */
	search?: string | null
	/** Select algorithm to generate the returned checksums */
	hash?: string | null
	/** Query to filter results by */
	q?: string | null
	/** Select which fields to return */
	select?: string[] | null
	/** Look for distinct values */
	distinct?: boolean
}

// Interface for group files query parameters
export interface GroupFilesQueryParams {
	/** Show results in human-readable format */
	pretty?: boolean
	/** Disable timeout response */
	wait_for_complete?: boolean
	/** First element to return in the collection */
	offset?: number
	/** Maximum number of elements to return */
	limit?: number
	/** Sort the collection by a field or fields */
	sort?: string | null
	/** Look for elements containing the specified string */
	search?: string | null
	/** Select algorithm to generate the returned checksums */
	hash?: string | null
	/** Query to filter results by */
	q?: string | null
	/** Select which fields to return */
	select?: string[] | null
	/** Look for distinct values */
	distinct?: boolean
}

// Interface for group file query parameters
export interface GroupFileQueryParams {
	/** Show results in human-readable format */
	pretty?: boolean
	/** Disable timeout response */
	wait_for_complete?: boolean
	/** Type of file */
	type?: string[] | null
	/** Format response in plain text */
	raw?: boolean
}

export default {
	getGroups(query: GroupsQueryParams, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { results: WazuhGroup[]; total_items: number }>(
			`/wazuh_manager/groups`,
			{
				params: query,
				signal
			}
		)
	},
	getGroupFiles(groupId: string, query: GroupFilesQueryParams, signal?: AbortSignal) {
		return HttpClient.get<FlaskBaseResponse & { results: WazuhGroupFile[]; total_items: number }>(
			`/wazuh_manager/groups/${groupId}/files`,
			{
				params: query,
				signal
			}
		)
	},
	getGroupFile(groupId: string, filename: string, query?: GroupFileQueryParams) {
		return HttpClient.get<FlaskBaseResponse & WazuhGroupFileDetails>(
			`/wazuh_manager/groups/${groupId}/files/${filename}`,
			{
				params: {
					raw: true,
					pretty: false,
					wait_for_complete: false,
					...query
				}
			}
		)
	},
	updateGroupConfiguration(groupId: string, configContent: string) {
		return HttpClient.put<FlaskBaseResponse & WazuhGroupConfigurationUpdate>(
			`/wazuh_manager/groups/${groupId}/configuration`,
			configContent,
			{
				headers: {
					'Content-Type': 'application/xml'
				}
			}
		)
	}
}
