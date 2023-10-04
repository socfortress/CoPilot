import dayjs from "@/utils/dayjs"
import { faker } from "@faker-js/faker"

export interface Contact {
	id: string
	name: string
	jobTitle: string
	avatar: string
	online: boolean
	lastDate: Date
	lastDateText: string
	lastMessage: string
}

export interface MessagesGroup {
	id: string
	isMine: boolean
	userId: string
	userObj: Contact
	messages: {
		text: string
	}[]
	date: Date
}

export type Conversation = MessagesGroup[]

export interface Chat {
	id: string
	userId: string
	userObj: Contact
	conversation: Conversation
	lastDate: Date
}

export const getData = () => {
	const contacts: Contact[] = []
	const chat: Chat[] = []

	for (let i = 0; i < 15; i++) {
		contacts.push({
			id: faker.string.nanoid(),
			name: faker.person.fullName(),
			jobTitle: faker.person.jobTitle(),
			avatar: faker.image.avatarGitHub(),
			online: faker.datatype.boolean(),
			lastDate: dayjs().toDate(),
			lastDateText: "",
			lastMessage: ""
		})
	}

	const me: Contact = contacts.pop() as Contact

	for (const user of contacts) {
		const conversation = []

		for (let i = 0; i < 15; i++) {
			const isMine = faker.datatype.boolean()
			const userObj = isMine ? me : user
			const userId = userObj.id

			conversation.push({
				id: faker.string.nanoid(),
				isMine,
				userId,
				userObj,
				messages: faker.helpers
					.uniqueArray(faker.word.sample, faker.number.int({ min: 1, max: 3 }))
					.map(() => ({
						text: faker.lorem.sentence(faker.number.int({ min: 2, max: 10 })).slice(0, -1)
					})),
				date: faker.date.between({ from: dayjs().subtract(2, "w").toDate(), to: dayjs().toDate() })
			})
		}

		const conversationSorted = conversation.sort((a, b) => a.date.getTime() - b.date.getTime())
		const lastDate = conversationSorted[conversation.length - 1].date
		const lastMessage = conversationSorted[conversation.length - 1].messages[0].text

		chat.push({
			id: faker.string.nanoid(),
			userId: user.id,
			userObj: user,
			conversation: conversationSorted,
			lastDate
		})

		user.lastDate = lastDate
		user.lastDateText =
			dayjs(lastDate).format("YYYY-MM-DD") === dayjs().format("YYYY-MM-DD")
				? dayjs(lastDate).format("HH:mm")
				: dayjs(lastDate).format("D MMM")
		user.lastMessage = lastMessage
	}

	return {
		contacts: contacts.sort((a, b) => b.lastDate.getTime() - a.lastDate.getTime()),
		chat: chat.sort((a, b) => b.lastDate.getTime() - a.lastDate.getTime()),
		me
	}
}
