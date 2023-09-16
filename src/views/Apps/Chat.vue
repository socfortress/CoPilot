<template>
	<div class="page page-wrapped flex flex-col page-without-footer">
		<div class="wrapper flex grow" :class="{ 'sidebar-open': sidebarOpen }">
			<div class="sidebar flex flex-col" ref="sidebar">
				<div class="sidebar-toolbar flex items-center">
					<n-input placeholder="Search..." clearable size="medium">
						<template #prefix>
							<n-icon :component="SearchIcon" />
						</template>
					</n-input>
				</div>
				<div class="sidebar-main grow">
					<n-scrollbar style="max-height: 100%">
						<div class="section contacts-list">
							<div
								v-for="user of store.contacts"
								:key="user.id"
								@click="setChat(user)"
								class="user flex items-center"
								:class="{ 'u-active': user.id === store.activeChat?.userId }"
							>
								<div class="u-avatar flex items-center" :class="{ 'u-online': user.online }">
									<n-avatar round size="large" :src="user.avatar" />
								</div>
								<div class="u-info flex flex-col grow">
									<div class="u-title flex justify-between items-center">
										<div class="u-name grow">
											{{ user.name }}
										</div>
										<div class="u-date">
											{{ user.lastDateText }}
										</div>
									</div>
									<div class="u-message">
										{{ user.lastMessage }}
									</div>
								</div>
							</div>
						</div>
					</n-scrollbar>
				</div>
			</div>
			<div class="main flex-grow flex flex-col" ref="main">
				<div class="main-toolbar flex items-center" v-if="store.activeChat">
					<div class="menu-btn flex justify-center opacity-50">
						<n-button text @click="sidebarOpen = true">
							<n-icon :size="24">
								<MenuIcon />
							</n-icon>
						</n-button>
					</div>

					<div class="user flex items-center grow">
						<div
							class="flex items-center u-avatar"
							:class="{ 'u-online': store.activeChat.userObj.online }"
						>
							<n-avatar round size="large" :src="store.activeChat.userObj.avatar" />
						</div>
						<div class="u-info flex flex-col">
							<div class="u-name">{{ store.activeChat.userObj.name }}</div>
							<div class="u-job">{{ store.activeChat.userObj.jobTitle }}</div>
						</div>
					</div>

					<div class="actions-btns flex items-center gap-4 opacity-50">
						<n-button text>
							<n-icon :size="20">
								<VideoIcon />
							</n-icon>
						</n-button>
						<n-button text>
							<n-icon :size="20">
								<PhoneIcon />
							</n-icon>
						</n-button>
					</div>
					<div class="new-btn flex justify-center opacity-50">
						<n-dropdown :options="menuOptions">
							<n-button text>
								<n-icon :size="24">
									<MenuHorizontalIcon />
								</n-icon>
							</n-button>
						</n-dropdown>
					</div>
				</div>
				<div class="chat-view grow" v-if="store.activeChat">
					<n-scrollbar style="max-height: 100%" ref="chatViewList">
						<div
							v-for="conversation of store.activeChat.conversation"
							:key="conversation.id"
							class="conversation flex"
							:class="{ mine: conversation.isMine }"
						>
							<div class="avatar">
								<n-avatar round size="large" :src="conversation.userObj.avatar" />
							</div>
							<div class="messages-group flex flex-col">
								<div class="message" v-for="message of conversation.messages" :key="message.text">
									{{ message.text }}
								</div>
								<div class="date">
									<n-time :time="conversation.date" format="d MMM @ HH:mm" />
								</div>
							</div>
						</div>
					</n-scrollbar>
				</div>
				<div class="message-editor flex" v-if="store.activeChat">
					<div class="text-input grow">
						<n-input
							placeholder="Message..."
							type="textarea"
							size="small"
							@blur="resetWindowScroll()"
							:autosize="{
								minRows: 1,
								maxRows: 5
							}"
						/>
					</div>
					<div class="actions-group flex items-center">
						<n-button text>
							<n-icon :size="20">
								<MicrophoneIcon />
							</n-icon>
						</n-button>
						<n-button text>
							<n-icon :size="20">
								<AttachmentIcon />
							</n-icon>
						</n-button>
						<n-button strong ghost circle type="primary">
							<n-icon :size="20">
								<SendIcon />
							</n-icon>
						</n-button>
					</div>
				</div>
				<div class="empty-view grow flex flex-col items-center justify-center" v-if="!store.activeChat">
					<n-icon :size="48">
						<ChatIcon />
					</n-icon>
					<div class="text-xl mt-4">Select a Contact</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NIcon, NScrollbar, NAvatar, NInput, NButton, NDropdown, NTime } from "naive-ui"
import ChatIcon from "@vicons/carbon/Chat"
import TrashIcon from "@vicons/carbon/TrashCan"
import MenuIcon from "@vicons/ionicons5/MenuSharp"
import MenuHorizontalIcon from "@vicons/carbon/OverflowMenuHorizontal"
import SearchIcon from "@vicons/carbon/Search"
import VideoIcon from "@vicons/carbon/Video"
import PhoneIcon from "@vicons/carbon/Phone"
import InfoIcon from "@vicons/carbon/Information"
import MuteIcon from "@vicons/fluent/AlertOff16Regular"
import BlockUserIcon from "@vicons/tabler/UserOff"
import MicrophoneIcon from "@vicons/carbon/Microphone"
import AttachmentIcon from "@vicons/carbon/Attachment"
import SendIcon from "@vicons/carbon/Send"
import { ref, type VNode, type RendererNode, type RendererElement } from "vue"
import { onClickOutside, useResizeObserver } from "@vueuse/core"
import { renderIcon } from "@/utils"
import "@vueup/vue-quill/dist/vue-quill.snow.css"
import { useChatStore } from "@/stores/apps/useChatStore"
import { type Contact } from "@/mock/chat"
import { onMounted } from "vue"
import { useHideLayoutFooter } from "@/composables/useHideLayoutFooter"

interface MenuItem {
	label: string
	key: string
	icon: () => VNode<RendererNode, RendererElement, { [key: string]: any }>
}

const store = useChatStore()
const sidebarOpen = ref(false)
const sidebar = ref(null)
const main = ref(null)
const chatViewList = ref<typeof NScrollbar | null>(null)
const menuOptions = ref<MenuItem[]>([])

onClickOutside(sidebar, () => (sidebarOpen.value = false))

useResizeObserver(main, entries => {
	const entry = entries[0]
	const { width } = entry.contentRect

	const baseAct: MenuItem[] = [
		{
			label: "Block",
			key: "Block",
			icon: renderIcon(BlockUserIcon)
		},
		{
			label: "Mute",
			key: "Mute",
			icon: renderIcon(MuteIcon)
		},
		{
			label: "Info",
			key: "Info",
			icon: renderIcon(InfoIcon)
		},
		{
			label: "Delete",
			key: "Delete",
			icon: renderIcon(TrashIcon)
		}
	]

	const fullAct: MenuItem[] = [
		{
			label: "Video",
			key: "Video",
			icon: renderIcon(VideoIcon)
		},
		{
			label: "Call",
			key: "Call",
			icon: renderIcon(PhoneIcon)
		}
	]

	if (width < 400) {
		menuOptions.value = [...fullAct, ...baseAct]
	} else {
		menuOptions.value = baseAct
	}
})

function setChat(user: Contact) {
	sidebarOpen.value = false
	store.setActiveChat(user)
	resetChatScroll()
}

function resetChatScroll() {
	setTimeout(() => {
		chatViewList.value?.scrollTo(100000)
	}, 50)
}
function resetWindowScroll() {
	window.scrollTo(0, 0)
}

onMounted(() => {
	resetChatScroll()
})

// :has() CSS relational pseudo-class not yet supported by Firefox
// (https://caniuse.com/css-has)
// at the moment this worker around permit to hide Layout Footer
useHideLayoutFooter()
</script>

<style lang="scss" scoped>
@import "@/assets/scss/mixin.scss";

.page {
	--mb-toolbar-height: 70px;

	.wrapper {
		position: relative;
		height: 100%;
		overflow: hidden;
		border-radius: var(--border-radius);
		border: 1px solid var(--border-color);

		.sidebar {
			background-color: var(--bg-sidebar);
			min-width: 250px;
			width: 40%;
			max-width: 350px;
			overflow: hidden;

			.sidebar-toolbar {
				border-block-end: var(--border-small-050);
				min-height: var(--mb-toolbar-height);
				padding: 0 30px;

				:deep() {
					.n-input__border,
					.n-input__state-border {
						display: none;
					}
				}
			}

			.sidebar-main {
				overflow: hidden;
				.contacts-list {
					.user {
						cursor: pointer;
						padding: 0 30px;
						gap: 14px;
						width: 100%;
						overflow: hidden;
						height: 70px;
						font-size: 14px;
						transition: all 0.25s ease-out;
						border-block-end: var(--border-small-050);

						.u-avatar {
							border-radius: 50%;
							border: 2px solid rgba(var(--fg-color-rgb), 0.2);
							position: relative;

							&::after {
								content: "";
								width: 12px;
								height: 12px;
								display: block;
								position: absolute;
								right: 0;
								bottom: 0;
								background-color: #b8b8b8;
								border: 2px solid rgba(var(--fg-color-rgb), 0.2);
								border-radius: 50%;
							}
							&.u-online {
								&::after {
									background-color: var(--primary-color);
								}
							}
						}

						.u-info {
							overflow: hidden;
							.u-title {
								overflow: hidden;
								gap: 10px;
								.u-name {
									overflow: hidden;
									font-weight: bold;
									white-space: nowrap;
									text-overflow: ellipsis;
									font-size: 16px;
								}
								.u-date {
									opacity: 0.8;
								}
							}
							.u-message {
								overflow: hidden;
								white-space: nowrap;
								text-overflow: ellipsis;
							}
						}

						&:hover {
							background-color: rgba(var(--fg-color-rgb), 0.05);
						}

						&.u-active {
							background-color: rgba(var(--primary-color-rgb), 0.05);
							color: rgba(var(--primary-color-rgb), 0.9);
						}
					}
				}
			}
		}

		.main {
			background-color: var(--bg-color);
			position: relative;
			container-type: inline-size;

			.main-toolbar {
				border-block-end: var(--border-small-050);
				min-height: var(--mb-toolbar-height);
				padding: 0 30px;
				gap: 18px;

				.user {
					gap: 14px;
					line-height: 1.3;
					overflow: hidden;

					.u-info {
						overflow: hidden;
						white-space: nowrap;
						.u-name {
							overflow: hidden;
							font-weight: bold;
							white-space: nowrap;
							text-overflow: ellipsis;
							font-size: 16px;
						}
						.u-job {
							white-space: nowrap;
							overflow: hidden;
							text-overflow: ellipsis;
							opacity: 0.8;
						}
					}

					.u-avatar {
						border-radius: 50%;
						border: 2px solid rgba(var(--fg-color-rgb), 0.2);
						position: relative;

						&::after {
							content: "";
							width: 12px;
							height: 12px;
							display: block;
							position: absolute;
							right: 0;
							bottom: 0;
							background-color: #b8b8b8;
							border: 2px solid rgba(var(--fg-color-rgb), 0.2);
							border-radius: 50%;
						}
						&.u-online {
							&::after {
								background-color: var(--primary-color);
							}
						}
					}
				}

				.menu-btn {
					display: none;
				}

				@container (max-width: 400px) {
					.actions-btns {
						display: none;
					}
				}
			}

			.chat-view {
				overflow: hidden;

				.conversation {
					padding: 20px 30px;
					gap: 14px;
					opacity: 0;
					animation: conversation-fade 0.3s forwards;

					@for $i from 0 through 40 {
						&:nth-last-child(#{$i}) {
							animation-delay: $i * 0.1s;
						}
					}

					@keyframes conversation-fade {
						from {
							opacity: 0;
							transform: translateY(10px);
						}
						to {
							opacity: 1;
						}
					}

					.messages-group {
						width: fit-content;
						max-width: 60%;
						.message {
							background-color: var(--bg-sidebar);
							margin-bottom: 5px;
							padding: 5px 10px;
							border-radius: var(--border-radius);
							width: fit-content;
							font-size: 14px;
						}

						.date {
							opacity: 0.8;
							font-size: 12px;
							padding: 0 3px;
						}
					}

					&.mine {
						flex-direction: row-reverse;

						.messages-group {
							align-items: end;

							.message {
								background-color: var(--primary-color);
								color: var(--bg-color);
							}
						}
					}
				}

				@container (max-width: 500px) {
					.conversation {
						.messages-group {
							max-width: 90%;
						}
					}
				}
			}

			.message-editor {
				border-block-start: var(--border-small-050);
				padding: 20px 30px;
				gap: 20px;

				.text-input {
					.n-input--textarea {
						background-color: transparent;

						:deep() {
							.n-input__border,
							.n-input__state-border {
								display: none;
							}
						}
					}
				}

				.actions-group {
					gap: 20px;
				}
			}
		}
	}

	@media (max-width: 700px) {
		--mb-toolbar-height: 62px;

		@include page-full-view;

		.wrapper {
			height: 100%;
			overflow: hidden;
			border-radius: 0;
			border: none;

			&::before {
				content: "";
				width: 100vw;
				display: block;
				background-color: rgba(var(--bg-body-rgb), 0.4);
				position: absolute;
				top: 0;
				left: 0;
				bottom: 0;
				transform: translateX(-100%);
				opacity: 0;
				transition:
					opacity 0.25s ease-in-out,
					transform 0s linear 0.3s;
				z-index: 1;
			}

			.sidebar {
				position: absolute;
				top: 0;
				left: 0;
				bottom: 0;
				transform: translateX(-100%);
				transition: transform 0.25s ease-in-out;
				z-index: 1;
				border-radius: var(--border-radius);

				&::before {
					content: "";
					width: 100%;
					height: 100%;
					display: block;
					background-color: var(--bg-color);
					z-index: -1;
					position: absolute;
				}
			}
			.main {
				.main-toolbar {
					padding: 0 20px;
					gap: 14px;

					.menu-btn {
						display: flex;
					}
				}
			}

			&.sidebar-open {
				&::before {
					transform: translateX(0);
					opacity: 1;
					transition:
						opacity 0.25s ease-in-out,
						transform 0s linear 0s;
				}

				.sidebar {
					transform: translateX(0);
					box-shadow: 0px 0px 80px 0px rgba(0, 0, 0, 0.1);
				}
			}
		}
	}
}
</style>
