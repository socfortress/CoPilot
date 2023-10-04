import dayjs from "@/utils/dayjs"
import { faker } from "@faker-js/faker"

export const labels = [
	{
		id: "personal",
		title: "Personal"
	},
	{
		id: "office",
		title: "Office"
	},
	{
		id: "important",
		title: "Important"
	},
	{
		id: "shop",
		title: "Shop"
	}
]

export const folders = [
	{
		id: "inbox",
		title: "Inbox"
	},
	{
		id: "sent",
		title: "Sent"
	},
	{
		id: "draft",
		title: "Draft"
	},
	{
		id: "starred",
		title: "Starred"
	},
	{
		id: "spam",
		title: "Spam"
	},
	{
		id: "trash",
		title: "Trash"
	}
]

export interface Email {
	id: string
	date: Date
	dateText?: string
	subject: string
	body: string
	seen: boolean
	starred: boolean
	folder: string
	labels: {
		id: string
		title: string
	}[]
	name: string
	email: string
	avatar: string
	attachments: { name: string; size: string }[]
	selected: boolean
}

export const getEmails = (): Email[] => {
	const emails = []

	for (let i = 0; i < 150; i++) {
		const folder = faker.helpers.arrayElements(folders, 1)[0].id
		const body = []
		const bodyParagraphs = faker.number.int({ min: 2, max: 4 })
		for (let i = 0; i < bodyParagraphs; i++) {
			body.push(faker.lorem.sentence(faker.number.int({ min: 50, max: 100 })))
		}

		emails.push({
			id: faker.string.nanoid(),
			date: faker.date.between({ from: dayjs().subtract(2, "w").toDate(), to: dayjs().toDate() }),
			subject: faker.lorem.sentence(faker.number.int({ min: 3, max: 7 })).slice(0, -1),
			body: body.join("<br/><br/>"),
			seen: faker.datatype.boolean(),
			starred: faker.datatype.boolean() || folder === "starred",
			folder,
			labels: faker.helpers.arrayElements(labels, { min: 0, max: 2 }),
			name: faker.person.fullName(),
			email: faker.internet.email(),
			avatar: faker.image.avatarGitHub(),
			attachments: faker.helpers.uniqueArray(faker.word.sample, faker.number.int({ min: 0, max: 2 })).map(() => ({
				name: faker.system.commonFileName(),
				size: faker.number.int({ min: 50, max: 999 }) + "KB"
			})),
			selected: false
		})
	}
	return emails
}
