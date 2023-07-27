<template>
    <div class="page-mail flex" :class="{ 'email-selected': mailSelected }">
        <div class="mail-boxes flex column">
            <button class="compose-btn" @click="mailComposerVisible = true"><i class="mdi mdi-email-plus"></i></button>
            <div class="list-boxes scrollable only-y box grow">
                <div
                    class="item flex align-center"
                    :class="{ selected: mb.active }"
                    v-for="mb in mailboxes"
                    :key="mb.icon"
                >
                    <span class="icon"><i :class="'mdi mdi-' + mb.icon"></i></span>
                    <span class="label box grow">{{ mb.label }}</span>
                    <span class="badge" v-if="mb.label === 'Inbox'">7</span>
                </div>
            </div>
        </div>
        <div class="mail-list box grow flex column">
            <div class="search-box">
                <input placeholder="Search..." />
            </div>
            <el-scrollbar class="box grow">
                <div
                    class="item flex"
                    :class="{ selected: ml.id === selected }"
                    v-for="ml in mailList"
                    :key="ml.id"
                    @click="selectMail(ml.id)"
                >
                    <div class="left">
                        <div class="avatar">
                            <img :src="ml.photo" />
                        </div>
                        <div class="attachment">
                            <i class="mdi mdi-attachment" v-show="ml.attachment"></i>
                        </div>
                    </div>
                    <div class="right box grow">
                        <div class="user flex">
                            <div class="name box grow">{{ ml.name }}</div>
                            <div class="datetime">{{ ml.datetime }}</div>
                        </div>
                        <div class="subject">{{ ml.subject }}</div>
                        <!--<div class="body">{{ml.body}}</div>-->
                    </div>
                </div>
            </el-scrollbar>
        </div>
        <div class="mail-content box grow flex column">
            <div class="btn-back-box p-16" v-if="mailSelected">
                <button @click="selected = 0"><i class="mdi mdi-arrow-left"></i> BACK</button>
            </div>
            <div class="box grow scrollable scr-alt p-16" v-if="mailSelected">
                <div class="content-header flex">
                    <div class="avatar mr-16">
                        <img :src="mailSelected.photo" />
                    </div>
                    <div class="user-info box grow flex column justify-center">
                        <div>
                            <strong>{{ mailSelected.name }}</strong>
                        </div>
                        <div>to: jwick@email.com</div>
                    </div>
                    <div class="flex column justify-center right-col-large">
                        <div class="text-right">
                            {{ mailSelected.datetime }}
                        </div>
                        <div>
                            <div class="buttonset">
                                <button><i class="mdi mdi-reply"></i></button>
                                <button><i class="mdi mdi-reply-all"></i></button>
                                <button><i class="mdi mdi-forward"></i></button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="flex column justify-center right-col-small mt-20">
                    <div class="text-center">
                        {{ mailSelected.datetime }}
                    </div>
                    <div>
                        <div class="buttonset text-center">
                            <button><i class="mdi mdi-reply"></i></button>
                            <button><i class="mdi mdi-reply-all"></i></button>
                            <button><i class="mdi mdi-forward"></i></button>
                        </div>
                    </div>
                </div>

                <div class="subject">{{ mailSelected.subject }}</div>
                <div class="body">{{ mailSelected.body }}</div>
                <div class="attachments-list mt-30" v-if="mailSelected.attachment">
                    <div>
                        <strong><i class="mdi mdi-attachment fs-20"></i> Attachments (1)</strong>
                    </div>
                    <div class="attachment flex">
                        <div class="type">
                            <i class="mdi mdi-file-document fs-40"></i>
                        </div>
                        <div class="box grow detail">
                            <div>
                                <strong>Invoice</strong>
                                <br />
                                <small>142 KB</small>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="box grow p-16 flex center" v-if="!mailSelected">
                <div class="text-center o-020 fs-20">
                    <i class="mdi mdi-email fs-110"></i><br />
                    Select a message to read
                </div>
            </div>
        </div>

        <el-dialog title="New Message" v-model="mailComposerVisible" class="new-emai-dialog themed">
            <el-form label-width="120px" :label-position="'top'">
                <el-col>
                    <el-form-item label="From">
                        <el-input type="email" class="themed" />
                    </el-form-item>
                </el-col>
                <el-col>
                    <el-form-item label="To">
                        <el-input type="email" class="themed" />
                    </el-form-item>
                </el-col>
                <el-col>
                    <el-form-item label="Subject">
                        <el-input class="themed" />
                    </el-form-item>
                </el-col>
            </el-form>
            <div>
                <vue-pell-editor
                    :actions="editorOptions"
                    :content="editorContent"
                    :placeholder="editorPlaceholder"
                    v-model="editorContent"
                    :styleWithCss="false"
                    editorHeight="250px"
                />
            </div>
            <div>
                <el-button type="primary" plain class="themed">Send</el-button>
            </div>
        </el-dialog>
    </div>
</template>

<script>
import dayjs from "dayjs"
import Chance from "chance"
const chance = new Chance()
import VuePellEditor from "@/components/VuePellEditor.vue"

import { defineComponent } from "@vue/runtime-core"

export default defineComponent({
    name: "Mail",
    data() {
        let mailList = []
        const year = new Date().getFullYear()

        for (let i = 1; i <= 50; i++) {
            let timestamp = dayjs(chance.date({ year: year })).format("x")

            mailList.push({
                name: chance.name(),
                photo: "/static/images/users/user-" + chance.integer({ min: 0, max: 30 }) + ".jpg",
                subject: chance.sentence(),
                body: chance.paragraph(),
                attachment: chance.bool(),
                starred: chance.bool(),
                snoozed: chance.bool(),
                snoozed: chance.bool(),
                timestamp: timestamp,
                datetime: dayjs(timestamp, "x").format("DD MMM"),
                id: i
            })
        }

        return {
            mailList,
            mailComposerVisible: false,
            selected: 1,
            mailboxes: [
                {
                    icon: "inbox",
                    label: "Inbox",
                    active: true
                },
                {
                    icon: "star",
                    label: "Starred",
                    active: false
                },
                {
                    icon: "clock",
                    label: "Snoozed",
                    active: false
                },
                {
                    icon: "send",
                    label: "Sent",
                    active: false
                },
                {
                    icon: "file",
                    label: "Draft",
                    active: false
                },
                {
                    icon: "delete",
                    label: "Trash",
                    active: false
                },
                {
                    icon: "alert-octagon",
                    label: "Spam",
                    active: false
                }
            ],
            editorOptions: [
                "bold",
                "underline",
                {
                    name: "italic",
                    result: () => window.pell.exec("italic")
                },
                {
                    name: "custom",
                    icon: "<b><u><i>C</i></u></b>",
                    title: "Custom Action",
                    result: () => console.log("YOLO")
                },
                {
                    name: "image",
                    result: () => {
                        const url = window.prompt("Enter the image URL")
                        if (url) window.pell.exec("insertImage", ensureHTTP(url))
                    }
                },
                {
                    name: "link",
                    result: () => {
                        const url = window.prompt("Enter the link URL")
                        if (url) window.pell.exec("createLink", ensureHTTP(url))
                    }
                }
            ],
            editorPlaceholder: "Write something amazing...",
            editorContent: "<div>Predefined Content</div>"
        }
    },
    computed: {
        mailSelected() {
            return this.mailList.find(({ id }) => id === this.selected)
        }
    },
    methods: {
        selectMail(id) {
            this.selected = id
        }
    },
    components: { VuePellEditor }
})
</script>

<style lang="scss" scoped>
@import "@/assets/scss/_variables";

.page-mail {
    position: relative;
    height: calc(100% - 20px);

    .mail-boxes {
        position: absolute;
        top: 0px;
        left: 0px;
        bottom: 0px;
        z-index: 99;
        width: 60px;
        transition: all 0.25s;
        background: white;
        border-top-left-radius: 4px;
        border-bottom-left-radius: 4px;
        overflow: hidden;

        .compose-btn {
            background: $text-color-accent;
            color: white;
            border: none;
            outline: none;
            margin: 0;
            height: 50px;
            font-size: 30px;
            cursor: pointer;
        }

        .list-boxes {
            padding: 8px 0;
        }

        .item {
            width: 100%;
            white-space: nowrap;
            overflow: hidden;
            padding: 8px 16px;
            box-sizing: border-box;
            color: transparentize($text-color-primary, 0.5);
            cursor: pointer;

            .icon {
                font-size: 30px;
            }
            .label {
                opacity: 0;
                padding: 0;
                padding-left: 15px;
                transition: all 0.5s;
            }
            .badge {
                //background: $text-color-primary;
                padding: 0 7px;
                opacity: 0;
                transition: all 0.5s;
            }

            &.selected {
                background: transparentize($background-color, 0.9);
                color: transparentize($text-color-accent, 0);
            }

            &:hover {
                opacity: 0.5;
            }
        }

        &:hover {
            width: 220px;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;

            .item {
                text-overflow: ellipsis;

                .label {
                    opacity: 1;
                }
                .badge {
                    opacity: 1;
                }
            }
        }
    }
    .mail-list {
        margin-left: 60px;

        .search-box {
            height: 50px;
            width: 100%;
            max-width: 100%;
            background: transparentize($text-color-primary, 0.9);

            input {
                box-sizing: border-box;
                border: none;
                width: 100%;
                height: 100%;
                background: transparent;
                padding: 16px;
                font-size: 18px;
                outline: none;
            }
        }

        .item {
            width: 100%;
            background: transparentize($text-color-primary, 0.9);
            border-bottom: 1px solid transparentize($text-color-primary, 0.9);
            cursor: pointer;

            &.selected {
                background: transparentize($text-color-primary, 0.8);
            }

            &:last-child {
                border: none;
            }

            .left {
                text-align: center;
                padding: 16px;
                box-sizing: border-box;
                width: 72px;

                .avatar {
                    img {
                        width: 40px;
                    }
                }
                .attachment {
                    font-size: 30px;
                }
            }

            .right {
                padding: 16px;
                padding-left: 0px;
                padding-top: 12px;

                .user {
                    opacity: 0.8;
                    margin-bottom: 10px;

                    .name {
                        overflow: hidden;
                        text-overflow: ellipsis;
                        white-space: nowrap;
                    }
                }
                .subject {
                    font-weight: bold;
                    font-size: 18px;
                    margin-bottom: 10px;
                }
                .body {
                    font-size: 14px;
                    opacity: 0.8;
                }
            }
        }
    }
    .mail-content {
        background: white;
        border-top-right-radius: 4px;
        border-bottom-right-radius: 4px;

        .btn-back-box {
            display: none;

            button {
                background: transparent;
                cursor: pointer;
                color: transparentize($text-color-primary, 0.4);
                border: none;
                outline: none;
                font-weight: bold;
                font-size: 14px;
            }
        }

        .content-header {
            .avatar {
                img {
                    width: 60px;
                    display: block;
                }
            }
        }

        .right-col-small {
            display: none;
        }

        .buttonset {
            margin-top: 10px;

            button {
                border: none;
                cursor: pointer;
                padding: 3px 10px;
                background: $background-color;
                border: 2px solid $background-color;
                color: $text-color-primary;
                font-size: 16px;
                outline: none;

                &:hover {
                    background: $text-color-primary;
                    color: $background-color;
                }
            }
        }

        .subject {
            background: transparentize($text-color-accent, 0.8);
            font-weight: bold;
            font-size: 20px;
            padding: 16px;
            margin: 16px 0;
        }

        .attachments-list {
            .attachment {
                background: $text-color-accent;
                border: 2px solid $text-color-accent;
                color: white;
                float: left;
                margin-top: 10px;
                margin-right: 10px;
                cursor: pointer;

                .type {
                    width: 60px;
                    height: 60px;
                    line-height: 60px;
                    text-align: center;
                }

                .detail {
                    padding: 6px 15px;
                    padding-left: 0px;
                }

                &:hover {
                    background: white;
                    color: $text-color-accent;
                }
            }
        }
    }
}

@media (max-width: 768px) {
    .page-mail {
        .mail-boxes {
            //top: 15px;
            left: 10px;
            //bottom: 15px;

            &:hover {
                box-shadow: 3px 0px 10px -3px $text-color-accent;
            }
        }

        .mail-list {
            margin-left: 70px;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
            overflow: hidden;

            .item {
                .right {
                    .user {
                        font-size: 12px;
                    }
                    .subject {
                        font-size: 14px;
                    }
                    .body {
                        font-size: 10px;
                    }
                }
            }
        }

        .mail-content {
            display: none;
            margin-left: 70px;
            //mettere bordi arrotondati
            //border-t

            .btn-back-box {
                display: inherit;
            }
        }

        &.email-selected {
            .mail-list {
                display: none;
            }

            .mail-content {
                display: inherit;
            }
        }
    }
}

@media (max-width: 480px) {
    .page-mail {
        .mail-content {
            .right-col-large {
                display: none;
            }
            .right-col-small {
                display: block;
            }
        }
    }
}
</style>

<style lang="scss">
.new-emai-dialog {
    overflow: hidden;
    width: 90%;
    max-width: 660px;

    .el-form {
        overflow: hidden;
    }
}
</style>
