import dayjs from "dayjs"
import customParseFormat from "dayjs/plugin/customParseFormat"
import duration from "dayjs/plugin/duration"
import relativeTime from "dayjs/plugin/relativeTime"
import timezone from "dayjs/plugin/timezone"
import utc from "dayjs/plugin/utc"
// The portal's languages (#1310): dates read in the user's language.
import "dayjs/locale/cs"
import "dayjs/locale/de"
import "dayjs/locale/en"
import "dayjs/locale/es"
import "dayjs/locale/fr"
import "dayjs/locale/it"
import "dayjs/locale/nl"

/*
import isSameOrAfter from "dayjs/plugin/isSameOrAfter"
dayjs.extend(isSameOrAfter)
*/
dayjs.extend(utc)
dayjs.extend(relativeTime)
dayjs.extend(duration)
dayjs.extend(customParseFormat)
dayjs.extend(timezone)
dayjs.tz.setDefault(dayjs.tz.guess())

export default dayjs
