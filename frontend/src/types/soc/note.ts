export interface SocNote {
	note_details: NoteDetails
	note_id: number
	note_title: string
}

export interface NoteDetails {
	custom_attributes: { [key: string]: string | number }
	group_id: number
	group_title: string
	group_uuid: string
	note_content: string
	note_creationdate: string | Date
	note_id: number
	note_lastupdate: string | Date
	note_title: string
	note_uuid: string
}

export interface SocNewNote {
	custom_attributes: { [key: string]: string | number }
	note_content: string
	note_creationdate: string | Date
	note_id: number
	note_lastupdate: string | Date
	note_title: string
	note_uuid: string
}
