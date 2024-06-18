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
			mappings: object[]
			thresholds: string
		}
		overrides: object[]
	}
	gridPos: null | {
		h: number
		w: number
		x: number
		y: number
	}
	id: number
	options: null | { legend: object; tooltip: object }
	title: string
	type: null | string
	collapsed: null | boolean
	panels: Panel[]
}

export interface PanelLink {
	panel_id: number
	panel_url: string
}

export interface PanelImage {
	base64_image: string
	url: string
}
