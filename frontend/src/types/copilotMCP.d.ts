export interface MCPServer {
	name: string
	value: string
	description: string
	capabilities: string[]
}

export interface QueryResult {
	result: string
	structured_result: QueryStructuredResult
	execution_time: number
}

export interface QueryStructuredResult {
	response: string
	thinking_process: string
}

export interface ExampleQuestion {
	question: string
	description: string
	category: string
}
