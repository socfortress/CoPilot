import mitt, { type Emitter as Mitt, type EventType } from "mitt"
export const emitter = mitt()
export type Emitter<T extends Record<EventType, unknown>> = Mitt<T>
