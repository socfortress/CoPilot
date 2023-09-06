import dayjs from "dayjs"

export function isAgentOnline(last_seen) {
    const lastSeenDate = dayjs(last_seen)
    if (!lastSeenDate.isValid()) return false

    return lastSeenDate.isAfter(dayjs().subtract(1, "h"))
}
