import dayjs from "dayjs"
import timezone from "dayjs/plugin/timezone"
import locale_en from "dayjs/locale/en.js"
import customParseFormat from "dayjs/plugin/customParseFormat"
/*
import isSameOrAfter from "dayjs/plugin/isSameOrAfter"
import utc from "dayjs/plugin/utc"
import duration from "dayjs/plugin/duration"
import relativeTime from "dayjs/plugin/relativeTime"
dayjs.extend(isSameOrAfter)
dayjs.extend(utc)
dayjs.extend(relativeTime)
dayjs.extend(duration)
*/
dayjs.extend(customParseFormat)
dayjs.extend(timezone)
dayjs.locale(locale_en)
dayjs.tz.setDefault(dayjs.tz.guess())

export default dayjs
