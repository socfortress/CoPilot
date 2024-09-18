import mitt, { type EventType, type Emitter as Mitt } from "mitt"

interface Events {
	"action:add-customer": void
}

export const emitter = mitt<Omit<Events, "">>()
export type Emitter<T extends Record<EventType, unknown>> = Mitt<T>
