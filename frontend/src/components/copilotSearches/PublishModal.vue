<template>
	<n-modal
		:show
		preset="card"
		segmented
		:style="{ width: 'min(640px, 94vw)', maxHeight: '90vh' }"
		@update:show="onShow"
	>
		<template #header>
			<div class="flex items-center gap-2">
				<Icon :name="PublishIcon" :size="20" />
				<span class="font-semibold">Publish rule</span>
				<n-tag size="tiny" round :bordered="false" type="info">to client GitHub</n-tag>
			</div>
		</template>

		<!-- success state -->
		<div v-if="result?.success" class="flex flex-col gap-4">
			<n-alert type="success" :bordered="false" :title="`Rule ${result.action} in ${result.repo}`">
				<div class="flex flex-col gap-1 text-sm">
					<span>
						<code>{{ result.path }}</code>
						on
						<code>{{ result.branch }}</code>
					</span>
					<a v-if="result.commit_url" :href="result.commit_url" target="_blank" rel="noopener noreferrer">
						View commit ↗
					</a>
					<a v-if="result.html_url" :href="result.html_url" target="_blank" rel="noopener noreferrer">
						View file ↗
					</a>
				</div>
			</n-alert>
			<span class="text-secondary text-sm">
				It becomes a
				<b>Custom</b>
				card once the rules cache is refreshed.
			</span>
			<div class="flex justify-end gap-2">
				<n-button secondary :loading="refreshing" @click="refreshCache">
					<template #icon><Icon :name="RefreshIcon" :size="16" /></template>
					Refresh rules now
				</n-button>
				<n-button type="primary" @click="close">Done</n-button>
			</div>
		</div>

		<!-- form state -->
		<div v-else class="flex flex-col gap-4">
			<n-alert v-if="!valid" type="warning" :bordered="false" size="small">
				Fix the validation errors before publishing — publishing is disabled until the rule is valid.
			</n-alert>

			<n-alert v-if="!loadingRepos && !repoOptions.length" type="info" :bordered="false" size="small">
				No customer has a custom repository configured yet. Set one up under
				<b>Custom repos</b>
				first (and add a GitHub token with
				<code>contents:write</code>
				to publish).
			</n-alert>

			<div class="flex flex-col gap-1">
				<span class="text-secondary text-xs font-medium">Target — customer's repository</span>
				<n-select
					v-model:value="customerCode"
					:options="repoOptions"
					:loading="loadingRepos"
					filterable
					placeholder="Select a configured repository"
				/>
				<span v-if="selectedRepo && !selectedRepo.has_token" class="text-xs text-amber-500">
					This repo has no write token — add a PAT with
					<code>contents:write</code>
					under Custom repos to publish.
				</span>
			</div>

			<div class="flex flex-col gap-1">
				<span class="text-secondary text-xs font-medium">Path in repo</span>
				<n-input v-model:value="path" placeholder="detections/custom/rule.yaml" />
			</div>

			<div class="flex flex-col gap-1">
				<span class="text-secondary text-xs font-medium">
					Commit message
					<span class="opacity-60">(optional)</span>
				</span>
				<n-input v-model:value="commitMessage" :placeholder="defaultMessage" />
			</div>

			<n-alert v-if="errorMsg" type="error" :bordered="false" size="small">{{ errorMsg }}</n-alert>

			<div class="flex justify-end gap-2">
				<n-button quaternary @click="close">Cancel</n-button>
				<n-button type="primary" :loading="publishing" :disabled="!canPublish" @click="publish">
					<template #icon><Icon :name="PublishIcon" :size="16" /></template>
					Publish
				</n-button>
			</div>
		</div>
	</n-modal>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomRepoConfig, PublishRuleResponse } from "@/types/copilot-searches"
import { NAlert, NButton, NInput, NModal, NSelect, NTag, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	show: boolean
	yaml: string
	valid: boolean
}>()
const emit = defineEmits<{ (e: "update:show", value: boolean): void }>()

const PublishIcon = "carbon:cloud-upload"
const RefreshIcon = "carbon:renew"

const message = useMessage()

const repos = ref<CustomRepoConfig[]>([])
const loadingRepos = ref(false)
const customerCode = ref<string | null>(null)
const path = ref("")
const commitMessage = ref("")
const publishing = ref(false)
const refreshing = ref(false)
const errorMsg = ref<string | null>(null)
const result = ref<PublishRuleResponse | null>(null)

const RULE_NAME_RE = /^name:\s*(\S.*)$/m
const WRAP_QUOTES_RE = /^["']|["']$/g
const ruleName = computed(() => (props.yaml.match(RULE_NAME_RE)?.[1]?.trim() || "rule").replace(WRAP_QUOTES_RE, ""))
function slug(s: string): string {
	return (
		s
			.toLowerCase()
			.replace(/[^a-z0-9]+/g, "-")
			.replace(/^-|-$/g, "") || "rule"
	)
}
const defaultPath = computed(() => `detections/custom/${slug(ruleName.value)}.yaml`)
const defaultMessage = computed(() => `Add/Update detection rule: ${ruleName.value}`)

const repoOptions = computed(() =>
	repos.value.map(r => ({ label: `${r.repo} (${r.customer_code})`, value: r.customer_code }))
)
const selectedRepo = computed(() => repos.value.find(r => r.customer_code === customerCode.value) || null)
const canPublish = computed(() => props.valid && !!customerCode.value && !!path.value.trim() && !publishing.value)

async function loadRepos() {
	loadingRepos.value = true
	try {
		const res = await Api.copilotSearches.listCustomRepos()
		repos.value = res.data.repos || []
		if (repos.value.length === 1) customerCode.value = repos.value[0].customer_code
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to load custom repositories")
	} finally {
		loadingRepos.value = false
	}
}

async function publish() {
	if (!canPublish.value || !customerCode.value) return
	publishing.value = true
	errorMsg.value = null
	try {
		const res = await Api.copilotSearches.publishRule({
			yaml: props.yaml,
			customer_code: customerCode.value,
			message: commitMessage.value || undefined,
			path: path.value.trim() || undefined
		})
		if (res.data.success) {
			result.value = res.data
		} else {
			errorMsg.value = res.data.error || res.data.message || "Publish failed."
		}
	} catch (err) {
		errorMsg.value = getApiErrorMessage(err as ApiError) || "Publish request failed."
	} finally {
		publishing.value = false
	}
}

async function refreshCache() {
	refreshing.value = true
	try {
		const res = await Api.copilotSearches.refreshCache()
		message.success(`Rules refreshed — ${res.data.rules_loaded ?? "?"} loaded.`)
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Refresh failed")
	} finally {
		refreshing.value = false
	}
}

function onShow(value: boolean) {
	emit("update:show", value)
}
function close() {
	emit("update:show", false)
}

watch(
	() => props.show,
	shown => {
		if (shown) {
			result.value = null
			errorMsg.value = null
			path.value = defaultPath.value
			commitMessage.value = ""
			loadRepos()
		}
	}
)
</script>
