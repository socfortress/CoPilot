export interface Org {
	id: number
	name: string
}

export interface Dashboard {
	id: number
	uid: string
	title: string
	uri: string
	url: string
	slug: string
	type: string
	tags: string[]
	isStarred: boolean
	sortMeta: number
	folderId: number | null
	folderUid: null | string
	folderTitle: null | string
	folderUrl: null | string
}

export interface Panel {
	fieldConfig: null | {
		defaults: {
			color: string
			custom: string
			mappings: any[]
			thresholds: string
		}
		overrides: any[]
	}
	gridPos: null | {
		h: number
		w: number
		x: number
		y: number
	}
	id: number
	options: null | { legend: any; tooltip: any }
	title: string
	type: null | string
	collapsed: null | boolean
	panels: Panel[]
}

export interface PanelLink {
	panel_id: number
	panel_url: string
}