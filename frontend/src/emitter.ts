import mitt, { type Emitter as Mitt, type EventType } from "mitt"

type Events = {
	"action:add-customer": void
}

export const emitter = mitt<Events>()
export type Emitter<T extends Record<EventType, unknown>> = Mitt<T>
