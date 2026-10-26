<template>
	<div class="flex flex-col gap-4">
		<div class="flex flex-col gap-1">
			<h3 class="text-lg font-bold">Portal Languages</h3>
			<p class="text-secondary text-sm">
				Choose the languages this customer's portal users can pick from. English is always available and is
				the default.
			</p>
		</div>

		<n-spin :show="loading">
			<div class="flex flex-col gap-4">
				<n-card size="small">
					<div class="flex flex-col gap-3" data-testid="language-settings-list">
						<label
							v-for="code of PORTAL_LANGUAGES"
							:key="code"
							class="flex items-center gap-3"
							:data-testid="`language-settings-${code}`"
						>
							<n-checkbox
								:checked="selected.includes(code)"
								:disabled="code === DEFAULT_PORTAL_LANGUAGE || !isAdmin || saving"
								@update:checked="toggle(code, $event)"
							/>
							<span class="flex min-w-0 flex-wrap items-baseline gap-x-2">
								<span class="font-semibold">{{ PORTAL_LANGUAGE_NAMES[code].english }}</span>
								<span v-if="code !== DEFAULT_PORTAL_LANGUAGE" class="text-secondary text-sm" :lang="code">
									{{ PORTAL_LANGUAGE_NAMES[code].native }}
								</span>
								<n-tag
									v-if="code === DEFAULT_PORTAL_LANGUAGE"
									size="small"
									:bordered="false"
									data-testid="language-settings-default"
								>
									Always on · default
								</n-tag>
							</span>
						</label>
					</div>
				</n-card>

				<div v-if="isAdmin" class="flex flex-wrap items-center justify-end gap-3">
					<span v-if="dirty" class="text-secondary text-xs" data-testid="language-settings-unsaved">
						Unsaved changes
					</span>
					<n-button :disabled="!dirty || saving" data-testid="language-settings-reset" @click="reset">
						Reset
					</n-button>
					<n-button
						type="primary"
						:disabled="!dirty"
						:loading="saving"
						data-testid="language-settings-save"
						@click="save"
					>
						Save
					</n-button>
				</div>

				<n-alert
					v-else
					type="info"
					:bordered="false"
					class="text-xs"
					data-testid="language-settings-readonly"
				>
					Only administrators can change this setting.
				</n-alert>

				<div class="flex flex-col gap-3 text-sm" data-testid="language-settings-help">
					<p class="text-default">
						Portal users choose their language from their avatar menu or their Profile, and the portal keeps
						their choice. Until they choose, the portal follows their browser when its language is available,
						and English otherwise.
					</p>
					<p class="text-default">
						A user who belongs to several customers can pick any language enabled for at least one of them.
						Turning a language off moves its users back to English at their next page load.
					</p>
					<p class="text-default">
						The portal's own texts are translated. Alerts, cases, comments, reports and emails stay as they
						were written.
					</p>
				</div>

				<div
					v-if="settings?.updated_at"
					class="text-secondary text-xs"
					data-testid="language-settings-updated"
				>
					Last changed {{ formatDate(settings.updated_at, dFormats.datetime, { tz: true }) }}
				</div>
			</div>
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { PortalLanguage } from "./portalLanguages"
import type { ApiError } from "@/types/common"
import type { CustomerPortalLanguageSettings } from "@/types/customer-portal"
import { NAlert, NButton, NCard, NCheckbox, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import { useAuthStore } from "@/stores/auth"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"
import {
	DEFAULT_PORTAL_LANGUAGE,
	normalizeLanguages,
	PORTAL_LANGUAGE_NAMES,
	PORTAL_LANGUAGES,
	sameLanguages
} from "./portalLanguages"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const isAdmin = computed(() => useAuthStore().isAdmin)

const loading = ref(false)
const saving = ref(false)
const settings = ref<CustomerPortalLanguageSettings | null>(null)
const selected = ref<PortalLanguage[]>([DEFAULT_PORTAL_LANGUAGE])

const stored = computed(() => normalizeLanguages(settings.value?.languages ?? []))
const dirty = computed(() => !sameLanguages(selected.value, stored.value))

const FALLBACK_ERROR = "An error occurred. Please try again later."

function apply(value: CustomerPortalLanguageSettings) {
	settings.value = value
	selected.value = normalizeLanguages(value.languages)
}

function toggle(code: PortalLanguage, checked: boolean) {
	if (code === DEFAULT_PORTAL_LANGUAGE) return
	const others = selected.value.filter(c => c !== code)
	selected.value = normalizeLanguages(checked ? [...others, code] : others)
}

function reset() {
	selected.value = stored.value
}

async function getSettings() {
	loading.value = true
	try {
		const res = await Api.customerPortal.getCustomerLanguageSettings(customerCode)
		if (res.data.success) {
			apply(res.data.settings)
		} else {
			message.warning(res.data?.message || FALLBACK_ERROR)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || FALLBACK_ERROR)
	} finally {
		loading.value = false
	}
}

async function save() {
	saving.value = true
	try {
		const res = await Api.customerPortal.setCustomerLanguageSettings(customerCode, {
			languages: normalizeLanguages(selected.value)
		})
		if (res.data.success) {
			apply(res.data.settings)
			message.success("Portal languages saved for this customer")
		} else {
			message.warning(res.data?.message || FALLBACK_ERROR)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || FALLBACK_ERROR)
	} finally {
		saving.value = false
	}
}

onBeforeMount(() => {
	getSettings()
})
</script>
