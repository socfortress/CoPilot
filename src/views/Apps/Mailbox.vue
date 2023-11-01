<template>
	<div class="page page-wrapped flex flex-col page-without-footer">
		<div class="wrapper flex grow" :class="{ 'sidebar-open': sidebarOpen }">
			<div class="sidebar" ref="sidebar">
				<n-scrollbar style="max-height: 100%">
					<div class="section compose-btn-wrap">
						<n-button strong secondary type="primary" size="large" @click="newEmail()">
							New message
						</n-button>
					</div>
					<div class="section folders-list">
						<div
							v-for="folder of store.folders"
							:key="folder.title"
							@click="setFolder(folder.id)"
							class="folder flex items-center"
							:class="[`f-${folder.id}`, folder.id === store.activeFolder ? 'f-active' : '']"
						>
							<div class="f-icon">
								<Icon :size="18">
									<Iconify :icon="InboxIcon" v-if="folder.id === 'inbox'" />
									<Iconify :icon="SentIcon" v-if="folder.id === 'sent'" />
									<Iconify :icon="DraftIcon" v-if="folder.id === 'draft'" />
									<Iconify :icon="StarredIcon" v-if="folder.id === 'starred'" />
									<Iconify :icon="SpamIcon" v-if="folder.id === 'spam'" />
									<Iconify :icon="TrashIcon" v-if="folder.id === 'trash'" />
								</Icon>
							</div>
							<div class="f-title">
								{{ folder.title }}
							</div>
						</div>
					</div>
					<div class="section labels-list">
						<p class="mb-3 opacity-50">Labels:</p>
						<div class="list">
							<div
								v-for="label of store.labels"
								:key="label.title"
								@click="setLabel(label.id)"
								class="label flex items-center"
								:class="[`l-${label.id}`, label.id === store.activeLabel ? 'l-active' : '']"
							>
								<div class="l-icon flex">
									<Icon :size="14" :name="LabelIcon" :color="labelsColors[label.id]"></Icon>
								</div>
								<div class="l-title">
									{{ label.title }}
								</div>
							</div>
						</div>
					</div>
				</n-scrollbar>
			</div>
			<div class="main flex-grow flex flex-col">
				<div class="toolbar flex items-center">
					<div class="flex">
						<n-checkbox
							:checked="checkControl === 1"
							:indeterminate="checkControl === 2"
							@click="toggleCheckAll()"
							size="large"
						/>
					</div>
					<div class="flex grow items-center gap-3" v-if="checkControl">
						<n-tooltip>
							<template #trigger>
								<n-button text>
									<Icon :size="20" :name="TrashIcon"></Icon>
								</n-button>
							</template>
							<span>Delete</span>
						</n-tooltip>

						<n-tooltip>
							<template #trigger>
								<n-button text>
									<Icon :size="20" :name="LabelOutIcon"></Icon>
								</n-button>
							</template>
							<span>Add label</span>
						</n-tooltip>
						<n-tooltip>
							<template #trigger>
								<n-button text>
									<Icon :size="20" :name="FolderIcon"></Icon>
								</n-button>
							</template>
							<span>Move to folder</span>
						</n-tooltip>
						<n-tooltip>
							<template #trigger>
								<n-button text>
									<Icon :size="20" :name="StarredIcon"></Icon>
								</n-button>
							</template>
							<span>Star</span>
						</n-tooltip>
					</div>
					<div class="flex grow search-box" v-if="!checkControl">
						<n-input placeholder="Search..." clearable size="medium" v-model:value="search">
							<template #prefix>
								<Icon :name="SearchIcon" />
							</template>
						</n-input>
					</div>
					<div class="flex justify-center opacity-50" v-if="!checkControl">
						<n-button text>
							<Icon :size="18" :name="RefreshIcon"></Icon>
						</n-button>
					</div>
					<div class="menu-btn flex justify-center opacity-50" v-if="!checkControl">
						<n-button text @click="sidebarOpen = true">
							<Icon :size="24" :name="MenuIcon"></Icon>
						</n-button>
					</div>
					<div class="new-btn flex justify-center opacity-50" v-if="!checkControl">
						<n-button text @click="newEmail()">
							<Icon :size="20" :name="PenIcon"></Icon>
						</n-button>
					</div>
				</div>
				<div class="list grow" v-if="loadList">
					<n-scrollbar style="max-height: 100%">
						<EmailComponent
							v-for="email of emails"
							:key="email.id"
							:email="email"
							@select="selectedEmail = $event"
						/>
					</n-scrollbar>
				</div>
				<EmailView v-if="selectedEmail" :email="selectedEmail" @back="selectedEmail = null" />
				<ComposeView v-if="composeEmail" :email="composeEmail" @back="composeEmail = null" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NScrollbar, NCheckbox, NInput, NButton, NTooltip } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
import { Icon as Iconify } from "@iconify/vue"

import { useMailboxStore } from "@/stores/apps/useMailboxStore"
import { ref, computed, type ComputedRef, onMounted } from "vue"
import { onClickOutside } from "@vueuse/core"
import { type Email } from "@/mock/mailbox"
import dayjs from "@/utils/dayjs"
import EmailComponent from "@/components/apps/Mailbox/Email.vue"
import EmailView from "@/components/apps/Mailbox/EmailView.vue"
import ComposeView from "@/components/apps/Mailbox/ComposeView.vue"
import { useThemeStore } from "@/stores/theme"
import { useHideLayoutFooter } from "@/composables/useHideLayoutFooter"

const InboxIcon = "carbon:email"
const SentIcon = "carbon:send"
const DraftIcon = "carbon:edit"
const StarredIcon = "carbon:star"
const SpamIcon = "ion:alert-circle-outline"
const TrashIcon = "carbon:trash-can"
const LabelIcon = "carbon:bookmark-filled"
const LabelOutIcon = "carbon:bookmark"
const MenuIcon = "ion:menu-sharp"
const SearchIcon = "carbon:search"
const FolderIcon = "carbon:folder-move-to"
const RefreshIcon = "ion:reload"
const PenIcon = "carbon:pen"

const store = useMailboxStore()
const sidebarOpen = ref(false)

const loadList = ref(false)
const search = ref("")
const selectedEmail = ref<Email | null>(null)
const composeEmail = ref<Partial<Email> | null>(null)

const sidebar = ref(null)
onClickOutside(sidebar, () => (sidebarOpen.value = false))

function setLabel(label: string) {
	selectedEmail.value = null
	store.setActiveLabel(label)
}

function setFolder(folder: string) {
	selectedEmail.value = null
	store.setActiveFolder(folder)
}

function toggleCheckAll() {
	const check = checkControl.value !== 1

	for (const email of emails.value) {
		if (email.selected !== check) {
			store.toggleCheck(email)
		}
	}
}

function newEmail() {
	sidebarOpen.value = false
	composeEmail.value = {
		email: "",
		subject: "",
		body: ""
	}
}

const emails = computed(() => {
	return store.emails
		.filter((e: Email) => e.folder === store.activeFolder)
		.filter((e: Email) => (store.activeLabel ? e.labels.map(l => l.id).includes(store.activeLabel) : true))
		.filter((e: Email) =>
			search.value ? (e.name + e.subject).toLowerCase().indexOf(search.value.toLowerCase()) !== -1 : true
		)
		.map((e: Email) => {
			e.dateText =
				dayjs(e.date).format("YYYY-MM-DD") === dayjs().format("YYYY-MM-DD")
					? dayjs(e.date).format("HH:mm")
					: dayjs(e.date).format("D MMM")
			return e
		})
		.sort((a: Email, b: Email) => b.date.getTime() - a.date.getTime())
})

const checkControl: ComputedRef<0 | 1 | 2> = computed(() => {
	const emlCount = emails.value.length
	const selCount = emails.value.filter((e: Email) => e.selected).length

	if (!emlCount) {
		return 0
	}
	if (selCount === emlCount) {
		return 1
	}
	if (selCount) {
		return 2
	}
	return 0
})

const secondaryColors = computed(() => useThemeStore().secondaryColors)

const labelsColors = {
	personal: secondaryColors.value["secondary1"],
	office: secondaryColors.value["secondary2"],
	important: secondaryColors.value["secondary3"],
	shop: secondaryColors.value["secondary4"]
} as unknown as { [key: string]: string }

onMounted(() => {
	setTimeout(() => {
		loadList.value = true
	}, 100)
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
		background-color: var(--bg-color);
		border-radius: var(--border-radius);
		border: 1px solid var(--border-color);

		.sidebar {
			min-width: 230px;

			.compose-btn-wrap {
				width: 100%;
				height: var(--mb-toolbar-height);
				padding: 0px 22px;
				display: flex;
				align-items: center;
				justify-content: center;

				:deep() {
					.n-button {
						width: 100%;
						display: flex;
						align-items: center;
						background-color: var(--primary-010-color);
						.n-button__content {
							gap: 14px;
						}
					}
				}
			}

			.folders-list {
				margin-bottom: 20px;
				.folder {
					padding: 10px 22px;
					gap: 14px;
					height: 52px;
					cursor: pointer;
					transition: all 0.25s ease-out;
					opacity: 0.8;
					position: relative;

					.f-icon {
						display: flex;
					}
					.f-title {
						font-size: 14px;
					}

					&:hover {
						background-color: var(--hover-005-color);
					}

					&.f-active {
						opacity: 1;

						.f-title {
							font-weight: bold;
						}

						&::before {
							content: "";
							width: 4px;
							height: 20px;
							background-color: var(--primary-color);
							position: absolute;
							top: 50%;
							transform: translateY(-50%);
							left: 0;
							border-top-right-radius: var(--border-radius-small);
							border-bottom-right-radius: var(--border-radius-small);
						}
					}
				}
			}

			.labels-list {
				padding: 16px 22px;

				.list {
					.label {
						cursor: pointer;
						gap: 8px;
						margin-bottom: 6px;
						.l-icon {
							width: 10px;
							height: 10px;
							background-color: var(--color, --primary-color);
							border-radius: 50%;
						}
						.l-title {
							font-size: 14px;
							opacity: 0.9;
							padding-top: 3px;
							line-height: 1.2;
						}

						&:hover {
							.l-title {
								opacity: 1;
							}
						}
						&.l-active {
							.l-title {
								opacity: 1;
								font-weight: bold;
							}
						}
					}
				}
			}
		}

		.main {
			position: relative;
			container-type: inline-size;

			.toolbar {
				border-block-end: var(--border-small-050);
				min-height: var(--mb-toolbar-height);
				padding: 0 30px;
				gap: 18px;

				.menu-btn,
				.new-btn {
					display: none;
				}

				.search-box {
					margin: 0px 12px;
					.n-input {
						background-color: var(--bg-secondary-color);

						:deep() {
							.n-input__border,
							.n-input__state-border {
								display: none;
							}
						}
					}
				}
			}

			.list {
				overflow: hidden;
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
				background-color: var(--bg-body);
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
				.toolbar {
					padding: 0 20px;
					gap: 14px;

					.menu-btn,
					.new-btn {
						display: flex;
					}

					.search-box {
						margin: 0px 6px;
					}
				}
			}

			&.sidebar-open {
				&::before {
					transform: translateX(0);
					opacity: 0.4;
					transition:
						opacity 0.25s ease-in-out,
						transform 0s linear 0s;
				}

				.sidebar {
					transform: translateX(0);
					box-shadow: 0px 0px 80px 0px rgba(0, 0, 0, 0.1);
					border-radius: var(--border-radius);
				}
			}
		}
	}
}
</style>
