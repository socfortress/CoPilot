export interface PortainerStack {
	Id: number
	Name: string
	/** This indicates the kind of stack that Portainer is managing */
	Type: PortainerStackType
	EndpointId: number
	SwarmId: string
	EntryPoint: string
	Env: string[]
	ResourceControl: PortainerStackResourceControl | null
	Status: PortainerStackStatus
	ProjectPath: string
	CreationDate: number
	CreatedBy: string
	UpdateDate: number
	UpdatedBy: string
	AdditionalFiles: string | null
	AutoUpdate: string | null
	Option: string | null
	GitConfig: string | null
	FromAppTemplate: boolean
	Namespace: string
	IsComposeFormat: boolean
}

export enum PortainerStackStatus {
	Online = 1,
	Offline = 2
}

export enum PortainerStackType {
	DockerSwarmStack = 1,
	/** using docker-compose */
	StandaloneDockerStack = 2,
	KubernetesStack = 3
}

export interface PortainerStackResourceControl {
	Id: number
	ResourceId: string
	SubResourceIds: string[]
	/** This is an integer that tells Portainer which type of resource the ResourceControl object is protecting. ResourceControl can be applied to containers, stacks, secrets, configs, and so forth. */
	Type: PortainerStackResourceControlType
	UserAccesses: string[]
	TeamAccesses: string[]
	Public: boolean
	AdministratorsOnly: boolean
	System: boolean
}

export enum PortainerStackResourceControlType {
	Container = 1,
	Service = 2,
	Volume = 3,
	Network = 4,
	Secret = 5,
	Stack = 6,
	Config = 7
}
