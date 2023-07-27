<template>
    <el-scrollbar class="page-calendar">
        <FullCalendar ref="fullCalendar" :options="calendarOptions" class="calendar-wrap card-base card-shadow--medium" />

        <el-dialog title="Add event" v-model="dialogFormVisible">
            <el-form :model="form" ref="form" label-position="top">
                <el-col :span="13">
                    <el-form-item
                        label="Title"
                        prop="title"
                        :rules="[{ required: true, message: 'Please input event title', trigger: 'blur' }]"
                    >
                        <el-input v-model.trim="form.title"></el-input>
                    </el-form-item>
                </el-col>
                <el-col class="text-center" :span="1">&nbsp;</el-col>
                <el-col :span="5">
                    <el-form-item label="All day">
                        <el-switch v-model="form.allDay"></el-switch>
                    </el-form-item>
                </el-col>
                <el-col :span="5">
                    <el-form-item label="Color">
                        <el-color-picker v-model="form.color" :predefine="predefineColors"></el-color-picker>
                    </el-form-item>
                </el-col>
                <el-form-item label="Description">
                    <el-input type="textarea" autosize v-model="form.description"></el-input>
                </el-form-item>
                <el-form-item
                    label="Start"
                    prop="startDate"
                    :rules="[{ required: true, message: 'Please input a valid date', trigger: 'blur' }]"
                >
                    <el-col :span="11">
                        <el-date-picker type="date" placeholder="Pick a date" v-model="form.startDate" style="width: 100%"></el-date-picker>
                    </el-col>
                    <el-col v-if="!form.allDay" class="text-center" :span="2">-</el-col>
                    <el-col v-if="!form.allDay" :span="11">
                        <el-time-picker
                            type="fixed-time"
                            placeholder="Pick a time"
                            v-model="form.startTime"
                            style="width: 100%"
                            format="HH:mm"
                        ></el-time-picker>
                    </el-col>
                </el-form-item>
                <el-form-item label="End">
                    <el-col :span="11">
                        <el-date-picker type="date" placeholder="Pick a date" v-model="form.endDate" style="width: 100%"></el-date-picker>
                    </el-col>
                    <el-col v-if="!form.allDay" class="text-center" :span="2">-</el-col>
                    <el-col v-if="!form.allDay" :span="11">
                        <el-time-picker
                            type="fixed-time"
                            placeholder="Pick a time"
                            v-model="form.endTime"
                            style="width: 100%"
                            format="HH:mm"
                        ></el-time-picker>
                    </el-col>
                </el-form-item>
            </el-form>
            <span slot="footer" class="dialog-footer">
                <el-button @click="closeEventDialog">Cancel</el-button>
                <el-button type="primary" @click="setEvent">Save</el-button>
            </span>
        </el-dialog>
    </el-scrollbar>
</template>

<script>
import dayjs from "dayjs"
import "@fullcalendar/core/vdom"
import FullCalendar from "@fullcalendar/vue3"
import dayGridPlugin from "@fullcalendar/daygrid"
import timeGridPlugin from "@fullcalendar/timegrid"
import listPlugin from "@fullcalendar/list"
import interactionPlugin from "@fullcalendar/interaction"
import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "Calendar",
    data() {
        const __Y = dayjs().format("YYYY")
        const __M = dayjs().format("MM")

        return {
            calendarOptions: {
                customButtons: {
                    addEvent: {
                        text: "✚",
                        click: this.addEventDialog
                    }
                },
                locale: "en",
                headerToolbar: {
                    left: "prev,next today",
                    center: "title",
                    right: "dayGridMonth,timeGridWeek,timeGridDay,listWeek addEvent"
                },
                height: "auto",
                firstDay: 1,
                allDaySlot: true,
                slotEventOverlap: true,
                selectable: true,
                selectMirror: true,
                eventTimeFormat: {
                    // like '14:30'
                    hour: "2-digit",
                    minute: "2-digit",
                    meridiem: false
                },
                navLinks: true, // can click day/week names to navigate views
                editable: true,
                dayMaxEvents: true, // allow "more" link when too many events
                plugins: [dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin],
                events: [
                    { title: "All Day Event", start: __Y + "-" + __M + "-01" },
                    { title: "Long Event", start: __Y + "-" + __M + "-07", end: __Y + "-" + __M + "-10" },
                    { id: 999, title: "Repeating Event", start: __Y + "-" + __M + "-09T16:00:00" },
                    { id: 999, title: "Repeating Event", start: __Y + "-" + __M + "-16T16:00:00" },
                    { title: "Conference", start: __Y + "-" + __M + "-11", end: __Y + "-" + __M + "-13" },
                    {
                        title: "Meeting",
                        start: __Y + "-" + __M + "-12T10:30:00",
                        end: __Y + "-" + __M + "-12T12:30:00"
                    },
                    { title: "Lunch", start: __Y + "-" + __M + "-12T12:00:00" },
                    { title: "Meeting", start: __Y + "-" + __M + "-12T14:30:00" },
                    { title: "Happy Hour", start: __Y + "-" + __M + "-12T17:30:00" },
                    { title: "Dinner", start: __Y + "-" + __M + "-12T20:00:00" },
                    { title: "Birthday Party", start: __Y + "-" + __M + "-13T07:00:00" },
                    { title: "Click for Google", url: "http://google.com/", start: __Y + "-" + __M + "-28" }
                ],
                dateClick: this.dayClick,
                eventClick: this.eventClick,
                select: this.select
            },
            dialogFormVisible: false,
            form: {
                title: "",
                description: "",
                allDay: false,
                startDate: "",
                startTime: "",
                endDate: "",
                endTime: "",
                color: "#4a596a"
            },
            predefineColors: ["#ff4500", "#ff8c00", "#ffd700", "#90ee90", "#00ced1", "#1e90ff", "#4a596a", "#c71585"]
        }
    },
    methods: {
        closeEventDialog() {
            this.$refs.form.resetFields()
            this.dialogFormVisible = false
            this.form = {
                title: "",
                description: "",
                allDay: false,
                startDate: "",
                startTime: "",
                endDate: "",
                endTime: "",
                color: "#4a596a"
            }
        },
        setEvent() {
            this.$refs.form.validate(valid => {
                if (valid) {
                    let start = dayjs(this.form.startDate)
                    if (this.form.startTime) {
                        start.add(dayjs(this.form.startTime).format("HH"), "hours")
                        start.add(dayjs(this.form.startTime).format("mm"), "minutes")
                    }

                    let event = {
                        id: new Date().getTime(),
                        title: this.form.title,
                        description: this.form.description,
                        start: start,
                        allDay: this.form.allDay
                    }

                    if (this.form.color) event.color = this.form.color
                    if (this.form.endDate) {
                        let end = dayjs(this.form.endDate)
                        if (this.form.endTime) {
                            end.add(dayjs(this.form.endTime).format("HH"), "hours")
                            end.add(dayjs(this.form.endTime).format("mm"), "minutes")
                        } else {
                            end.add(24, "hours")
                        }

                        event.end = end
                    }

                    this.$refs.fullCalendar("renderEvent", event, true)

                    this.closeEventDialog()
                } else {
                    return false
                }
            })
        },
        addEventDialog() {
            this.dialogFormVisible = true
        },
        dayClick(arg) {
            this.form.startDate = arg.date
            this.dialogFormVisible = true
        },
        eventClick(arg) {
            this.form = {
                title: arg.event.title,
                description: arg.event.description,
                allDay: arg.event.allDay,
                startDate: arg.event.start,
                startTime: arg.event.start,
                endDate: arg.event.end,
                endTime: arg.event.end,
                color: arg.event.color || "#4a596a"
            }
            this.dialogFormVisible = true
        },
        select(arg) {
            this.form.startDate = arg.start
            this.form.endDate = arg.end
            this.dialogFormVisible = true
        }
    },
    components: {
        FullCalendar
    }
})
</script>

<style lang="scss">
/*
@import "../../assets/scss/_variables";
//@import '~@fullcalendar/core/main.css';
@import "~@fullcalendar/daygrid/main.css";
@import "~@fullcalendar/timegrid/main.css";
@import "~@fullcalendar/list/main.css";

/*.page-calendar {
	.calendar-wrap {
		//background: white;
	}
}*/
</style>
