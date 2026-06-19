export interface MCPServer {
	name: string
	value: string
	description: string
	capabilities: string[]
}

export interface QueryResult {
	result: string | QueryStructuredResult
	structured_result: QueryStructuredResult | null
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
