<template>
	<div class="compose-view flex flex-col">
		<div class="compose-view-toolbar flex items-center">
			<n-button text @click="goBack()">
				<Icon :size="24" :name="ArrowLeftIcon"></Icon>
			</n-button>
			<span class="compose-view-title">Compose message</span>
		</div>
		<div class="compose-view-content grow flex flex-col">
			<n-form label-placement="left" size="small" label-width="auto">
				<n-form-item label="To:">
					<n-input-group>
						<n-auto-complete
							v-model:value="emailForm.email"
							:input-props="{
								autocomplete: 'disabled'
							}"
							:options="autoCompleteOptions"
							placeholder="Email"
						/>
						<n-button type="tertiary">CC</n-button>
						<n-button type="tertiary">BCC</n-button>
					</n-input-group>
				</n-form-item>
				<n-form-item label="Subject:">
					<n-input placeholder="Message subject..." />
				</n-form-item>
			</n-form>
			<div class="compose-view-attachments flex justify-end">
				<n-button ghost>
					<Icon :size="16" class="mr-2" :name="DocumentAddIcon"></Icon>

					Add attachment
				</n-button>
			</div>
			<div class="compose-view-body grow flex flex-col">
				<QuillEditor v-if="mounted" theme="snow" toolbar="minimal" @blur="resetScroll()" />
			</div>
			<div class="compose-view-footer flex justify-end">
				<n-button-group>
					<n-button type="primary" ghost>
						<template #icon>
							<Icon :name="SentIcon"></Icon>
						</template>
						Send
					</n-button>
					<n-dropdown
						trigger="click"
						:options="[
							{
								label: 'Save as draft',
								key: 'Save as draft'
							},
							{
								label: 'Postponed sending',
								key: 'Postponed sending'
							}
						]"
					>
						<n-button type="primary" ghost>
							<template #icon>
								<Icon :name="ChevronDownIcon"></Icon>
							</template>
						</n-button>
					</n-dropdown>
				</n-button-group>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { NInput, NAutoComplete, NInputGroup, NForm, NFormItem, NButton, NButtonGroup, NDropdown } from "naive-ui"
import Icon from "@/components/common/Icon.vue"

const SentIcon = "carbon:send"
const ArrowLeftIcon = "carbon:arrow-left"
const ChevronDownIcon = "carbon:chevron-down"
const DocumentAddIcon = "carbon:document-add"
import { computed, toRefs, ref, defineAsyncComponent, type Component, onMounted } from "vue"
import { type Email } from "@/mock/mailbox"
import "@/assets/scss/quill-override.scss"

defineOptions({
	name: "ComposeView"
})

const props = defineProps<{
	email: Partial<Email>
}>()
const { email: emailForm } = toRefs(props)

const emit = defineEmits<{
	(e: "back"): void
}>()

const mounted = ref(false)

const QuillEditor = defineAsyncComponent<Component>(() => {
	return (async () => {
		const { QuillEditor } = await import("@vueup/vue-quill")
		return QuillEditor
	})()
})

function goBack() {
	emit("back")
}

const autoCompleteOptions = computed(() => {
	return ["@gmail.com", "@live.com", "@qq.com", "@me.com"].map(suffix => {
		const prefix = emailForm.value?.email?.split("@")[0]
		return {
			label: prefix + suffix,
			value: prefix + suffix
		}
	})
})

function resetScroll() {
	window.scrollTo(0, 0)
}

onMounted(() => {
	mounted.value = true
})
</script>

<style lang="scss" scoped>
.compose-view {
	--mb-toolbar-height: 70px;

	position: absolute;
	top: 0;
	left: 0;
	right: 0;
	bottom: 0;
	width: 100%;
	height: 100%;
	background-color: var(--bg-color);
	animation: email-view 0.25s forwards ease-out;
	overflow: hidden;

	.compose-view-toolbar {
		border-block-end: var(--border-small-050);
		min-height: var(--mb-toolbar-height);
		padding: 0 30px;
		gap: 18px;

		.compose-view-title {
			font-size: 16px;
		}

		.actions-btns {
			gap: 18px;
		}

		.menu-btns {
			display: none;
		}

		.reply-btns {
			margin-right: 15px;
		}

		@container (max-width:600px) {
			.nav-btns {
				span {
					display: none;
				}
			}
		}
		@container (max-width:500px) {
			.actions-btns {
				display: none;
			}
			.menu-btns {
				display: flex;
			}
		}
	}

	.compose-view-content {
		.n-form {
			padding: 20px 30px;

			:deep(.n-form-item-feedback-wrapper) {
				min-height: 10px;
			}
		}

		.compose-view-attachments {
			padding: 0px 30px;
		}

		.compose-view-body {
			overflow: hidden;
			height: 0;
			padding: 20px 30px;
		}

		.compose-view-footer {
			padding: 20px 30px;
			padding-top: 0;
		}
	}

	@keyframes email-view {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	@media (max-width: 700px) {
		--mb-toolbar-height: 62px;
	}
}
</style>
