import type { MessageSchema } from "../../config"
import { collectMessages } from "../collect"

// Every area's file in this folder, by file name; the same keys as English (see ../en/index.ts).
export default collectMessages(import.meta.glob("./*.json", { eager: true, import: "default" })) as MessageSchema
