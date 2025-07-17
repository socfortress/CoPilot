import type { ExampleQuestion, MCPServer, QueryResult } from "@/types/copilotMCP.d"
import type { FlaskBaseResponse } from "@/types/flask.d"
import { HttpClient } from "../httpClient"

export interface QueryPayload {
	input: string
	mcp_server: string
	verbose?: boolean
}

export default {
	getAvailableServers() {
		return HttpClient.get<FlaskBaseResponse & { servers: MCPServer[]; total_servers: number }>(
			`/copilot_mcp/servers`
		)
	},
	getServerDetails(server: string) {
		return HttpClient.get<
			FlaskBaseResponse & {
				servers: MCPServer[]
				available_categories: string[]
				total_example_questions: number
			}
		>(`/copilot_mcp/servers/${server}`)
	},
	query(payload: QueryPayload) {
		return HttpClient.post<FlaskBaseResponse & QueryResult>(`/copilot_mcp/query`, payload)
	},
	getExampleQuestions(server: string) {
		return HttpClient.get<
			FlaskBaseResponse & { mcp_server: string; questions: ExampleQuestion[]; total_questions: number }
		>(`/copilot_mcp/example-questions`, {
			params: {
				mcp_server: server
			}
		})
	}
}
