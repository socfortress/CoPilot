<template>
	<div>
		<n-button :size="size || 'small'" ghost type="primary" :loading @click="analysis()">
			<template #icon>
				<Icon :name="AiIcon" />
			</template>
			<div class="flex items-center gap-2">
				<span>Enrich with VirusTotal</span>
			</div>
		</n-button>

		<n-modal
			v-model:show="showModal"
			preset="card"
			content-class="!p-0"
			:style="{ maxWidth: 'min(710px, 90vw)', minHeight: 'min(500px, 90vh)' }"
			:bordered="false"
			segmented
			title="Virus Total Enrichment"
		>
			<n-tabs v-if="virusTotalDataResponse" type="line" animated :tabs-padding="24">
				<n-tab-pane name="Overview" tab="Overview" display-directive="show">
					<div class="flex flex-col gap-4 p-7 pt-2">
						<div class="grid-auto-fit-200 grid gap-4">
							<CardKV>
								<template #key>type</template>
								<template #value>{{ virusTotalDataResponse.type }}</template>
							</CardKV>
							<CardKV>
								<template #key>id</template>
								<template #value>{{ virusTotalDataResponse.id }}</template>
							</CardKV>
						</div>
						<CardStatsBars
							title="Total votes"
							class="h-full cursor-pointer"
							:values="totalVotes"
							:show-total="false"
						></CardStatsBars>
						<CardStatsBars
							title="Last Analysis Stats"
							class="h-full cursor-pointer"
							:values="lastAnalysisStats"
							:show-total="false"
							show-zero-items
						></CardStatsBars>
						<div
							v-if="virusTotalDataResponse.attributes?.tags?.length"
							class="text-secondary flex flex-wrap gap-4 text-sm"
						>
							<span v-for="tag of virusTotalDataResponse.attributes.tags" :key="tag">#{{ tag }}</span>
						</div>
						<ul v-if="Object.keys(virusTotalDataResponse.links || {}).length">
							<li v-for="link of virusTotalDataResponse.links" :key="link">
								<a :href="link" target="_blank">{{ link }}</a>
							</li>
						</ul>
					</div>
				</n-tab-pane>
				<n-tab-pane name="Analysis Results" tab="Analysis Results" display-directive="show">
					<div class="p-7 pt-2">
						<div
							v-if="Object.keys(virusTotalDataResponse.attributes?.last_analysis_results || {}).length"
							class="flex flex-col gap-3"
						>
							<div
								v-if="virusTotalDataResponse.attributes.last_analysis_date"
								class="text-right font-mono text-sm"
							>
								last analysis date:
								<code>
									{{
										formatDate(
											virusTotalDataResponse.attributes.last_analysis_date,
											dFormats.datetime
										)
									}}
								</code>
							</div>
							<CardEntity
								v-for="(value, key) of virusTotalDataResponse.attributes.last_analysis_results"
								:key
								embedded
								class="@container"
							>
								<template #header>{{ key }}</template>
								<template #footer>
									<div class="@xs:!flex-row flex flex-col justify-between gap-4 text-sm">
										<n-statistic class="grow">
											<template #label>
												<span class="text-sm">method</span>
											</template>
											<span class="text-base">{{ value.method }}</span>
										</n-statistic>
										<n-statistic class="grow">
											<template #label>
												<span class="text-sm">category</span>
											</template>
											<span class="text-base">{{ value.category }}</span>
										</n-statistic>
										<n-statistic class="grow">
											<template #label>
												<span class="text-sm">result</span>
											</template>
											<span class="text-base">{{ value.result }}</span>
										</n-statistic>
									</div>
								</template>
							</CardEntity>
						</div>
						<n-empty v-else description="No items found" class="h-48 justify-center" />
					</div>
				</n-tab-pane>
				<n-tab-pane name="Details" tab="Details" display-directive="show">
					<div class="p-7 pt-4">
						<CodeSource :code="properties" :decode="true" />
					</div>
				</n-tab-pane>
				<n-tab-pane
					v-if="virusTotalDataResponse.attributes.whois"
					name="Whois"
					tab="Whois"
					display-directive="show"
				>
					<div class="p-7 pt-4">
						<div
							v-if="virusTotalDataResponse.attributes.whois_date"
							class="mb-4 text-right font-mono text-sm"
						>
							whois date:
							<code>
								{{ formatDate(virusTotalDataResponse.attributes.whois_date, dFormats.datetime) }}
							</code>
						</div>
						<n-input
							:value="virusTotalDataResponse.attributes.whois"
							type="textarea"
							readonly
							placeholder="Empty"
							size="large"
							:autosize="{
								minRows: 3,
								maxRows: 18
							}"
						/>
					</div>
				</n-tab-pane>
				<n-tab-pane name="HTTPS Certificate" tab="HTTPS Certificate" display-directive="show">
					<div class="flex flex-col gap-3 p-7 pt-2">
						<div
							v-if="virusTotalDataResponse.attributes.last_https_certificate_date"
							class="text-right font-mono text-sm"
						>
							last https certificate date:
							<code>
								{{
									formatDate(
										virusTotalDataResponse.attributes.last_https_certificate_date,
										dFormats.datetime
									)
								}}
							</code>
						</div>

						<CardKV value-class="!p-0 overflow-x-auto overflow-y-hidden">
							<template #key>cert_signature</template>
							<template #value>
								<n-table
									v-if="
										Object.keys(
											virusTotalDataResponse.attributes?.last_https_certificate.cert_signature
										).length
									"
									:bordered="false"
									single-line
								>
									<tbody>
										<tr
											v-for="(value, key) of virusTotalDataResponse.attributes
												.last_https_certificate.cert_signature"
											:key
										>
											<td class="whitespace-nowrap text-sm">{{ key }}</td>
											<td class="whitespace-nowrap text-sm font-semibold">{{ value }}</td>
										</tr>
									</tbody>
								</n-table>
							</template>
						</CardKV>

						<CardKV value-class="!p-0 overflow-x-auto overflow-y-hidden">
							<template #key>authority_key_identifier</template>
							<template #value>
								<n-table
									v-if="
										Object.keys(
											virusTotalDataResponse.attributes?.last_https_certificate?.extensions
												?.authority_key_identifier || {}
										).length
									"
									:bordered="false"
									single-line
								>
									<tbody>
										<tr
											v-for="(value, key) of virusTotalDataResponse.attributes
												.last_https_certificate.extensions.authority_key_identifier"
											:key
										>
											<td class="whitespace-nowrap text-sm">{{ key }}</td>
											<td class="whitespace-nowrap text-sm font-semibold">{{ value }}</td>
										</tr>
									</tbody>
								</n-table>
							</template>
						</CardKV>

						<CardKV>
							<template #key>subject_key_identifier</template>
							<template #value>
								{{
									virusTotalDataResponse.attributes.last_https_certificate?.extensions
										?.subject_key_identifier || "-"
								}}
							</template>
						</CardKV>

						<CardKV>
							<template #key>subject_alternative_name</template>
							<template #value>
								<span
									v-if="
										!virusTotalDataResponse.attributes.last_https_certificate?.extensions
											?.subject_alternative_name?.length
									"
								>
									-
								</span>
								<div v-else class="flex flex-wrap gap-2">
									<Badge
										v-for="value of virusTotalDataResponse.attributes.last_https_certificate
											?.extensions?.subject_alternative_name"
										:key="value"
									>
										<template #value>
											{{ value }}
										</template>
									</Badge>
								</div>
							</template>
						</CardKV>

						<CardKV>
							<template #key>certificate_policies</template>
							<template #value>
								<span
									v-if="
										!virusTotalDataResponse.attributes.last_https_certificate?.extensions
											?.certificate_policies?.length
									"
								>
									-
								</span>
								<div v-else class="flex flex-wrap gap-2">
									<Badge
										v-for="value of virusTotalDataResponse.attributes.last_https_certificate
											?.extensions?.certificate_policies"
										:key="value"
									>
										<template #value>
											{{ value }}
										</template>
									</Badge>
								</div>
							</template>
						</CardKV>

						<CardKV>
							<template #key>key_usage</template>
							<template #value>
								<span
									v-if="
										!virusTotalDataResponse.attributes.last_https_certificate?.extensions?.key_usage
											?.length
									"
								>
									-
								</span>
								<div v-else class="flex flex-wrap gap-2">
									<Badge
										v-for="value of virusTotalDataResponse.attributes.last_https_certificate
											?.extensions?.key_usage"
										:key="value"
									>
										<template #value>
											{{ value }}
										</template>
									</Badge>
								</div>
							</template>
						</CardKV>

						<CardKV>
							<template #key>extended_key_usage</template>
							<template #value>
								<span
									v-if="
										!virusTotalDataResponse.attributes.last_https_certificate?.extensions
											?.extended_key_usage?.length
									"
								>
									-
								</span>
								<div v-else class="flex flex-wrap gap-2">
									<Badge
										v-for="value of virusTotalDataResponse.attributes.last_https_certificate
											?.extensions?.extended_key_usage"
										:key="value"
									>
										<template #value>
											{{ value }}
										</template>
									</Badge>
								</div>
							</template>
						</CardKV>

						<CardKV>
							<template #key>crl_distribution_points</template>
							<template #value>
								<span
									v-if="
										!virusTotalDataResponse.attributes.last_https_certificate?.extensions
											?.crl_distribution_points?.length
									"
								>
									-
								</span>
								<ul v-else class="flex flex-wrap gap-2">
									<li
										v-for="value of virusTotalDataResponse.attributes.last_https_certificate
											?.extensions?.crl_distribution_points"
										:key="value"
									>
										<a :href="value" target="_blank" rel="nofollow noopener noreferrer">
											{{ value }}
										</a>
									</li>
								</ul>
							</template>
						</CardKV>

						<CardKV value-class="!p-0 overflow-x-auto overflow-y-hidden">
							<template #key>ca_information_access</template>
							<template #value>
								<n-table
									v-if="
										Object.keys(
											virusTotalDataResponse.attributes?.last_https_certificate?.extensions
												?.ca_information_access || {}
										).length
									"
									:bordered="false"
									single-line
								>
									<tbody>
										<tr
											v-for="(value, key) of virusTotalDataResponse.attributes
												.last_https_certificate.extensions.ca_information_access"
											:key
										>
											<td class="whitespace-nowrap text-sm">{{ key }}</td>
											<td class="whitespace-nowrap text-sm font-semibold">
												<a :href="value" target="_blank" rel="nofollow noopener noreferrer">
													{{ value }}
												</a>
											</td>
										</tr>
									</tbody>
								</n-table>
							</template>
						</CardKV>

						<div class="flex gap-3">
							<CardKV class="grow">
								<template #key>CA</template>
								<template #value>
									{{ virusTotalDataResponse.attributes.last_https_certificate.extensions.CA }}
								</template>
							</CardKV>
							<CardKV class="grow">
								<template #key>size</template>
								<template #value>
									{{ virusTotalDataResponse.attributes.last_https_certificate.size }}
								</template>
							</CardKV>
							<CardKV class="grow">
								<template #key>version</template>
								<template #value>
									{{ virusTotalDataResponse.attributes.last_https_certificate.version }}
								</template>
							</CardKV>
						</div>

						<CardKV value-class="!p-0 overflow-x-auto overflow-y-hidden">
							<template #key>validity</template>
							<template #value>
								<n-table
									v-if="
										Object.keys(
											virusTotalDataResponse.attributes?.last_https_certificate?.validity || {}
										).length
									"
									:bordered="false"
									single-line
								>
									<tbody>
										<tr
											v-for="(value, key) of virusTotalDataResponse.attributes
												.last_https_certificate.validity"
											:key
										>
											<td class="whitespace-nowrap text-sm">{{ key }}</td>
											<td class="whitespace-nowrap text-sm font-semibold">{{ value }}</td>
										</tr>
									</tbody>
								</n-table>
							</template>
						</CardKV>

						<CardKV>
							<template #key>public_key</template>
							<template #value>
								<CodeSource
									:code="virusTotalDataResponse.attributes.last_https_certificate.public_key"
									:decode="true"
								/>
							</template>
						</CardKV>

						<CardKV value-class="!p-0 overflow-x-auto overflow-y-hidden">
							<template #value>
								<n-table :bordered="false" single-line>
									<tbody>
										<tr>
											<td class="whitespace-nowrap text-sm">thumbprint_sha256</td>
											<td class="whitespace-nowrap text-sm font-semibold">
												{{
													virusTotalDataResponse.attributes.last_https_certificate
														.thumbprint_sha256
												}}
											</td>
										</tr>
										<tr>
											<td class="whitespace-nowrap text-sm">thumbprint</td>
											<td class="whitespace-nowrap text-sm font-semibold">
												{{
													virusTotalDataResponse.attributes.last_https_certificate.thumbprint
												}}
											</td>
										</tr>
										<tr>
											<td class="whitespace-nowrap text-sm">serial_number</td>
											<td class="whitespace-nowrap text-sm font-semibold">
												{{
													virusTotalDataResponse.attributes.last_https_certificate
														.serial_number
												}}
											</td>
										</tr>
									</tbody>
								</n-table>
							</template>
						</CardKV>

						<CardKV value-class="!p-0 overflow-x-auto overflow-y-hidden">
							<template #key>issuer</template>
							<template #value>
								<n-table
									v-if="
										Object.keys(
											virusTotalDataResponse.attributes?.last_https_certificate?.issuer || {}
										).length
									"
									:bordered="false"
									single-line
								>
									<tbody>
										<tr
											v-for="(value, key) of virusTotalDataResponse.attributes
												.last_https_certificate.issuer"
											:key
										>
											<td class="whitespace-nowrap text-sm">{{ key }}</td>
											<td class="whitespace-nowrap text-sm font-semibold">{{ value }}</td>
										</tr>
									</tbody>
								</n-table>
							</template>
						</CardKV>

						<CardKV value-class="!p-0 overflow-x-auto overflow-y-hidden">
							<template #key>subject</template>
							<template #value>
								<n-table
									v-if="
										Object.keys(
											virusTotalDataResponse.attributes?.last_https_certificate?.subject || {}
										).length
									"
									:bordered="false"
									single-line
								>
									<tbody>
										<tr
											v-for="(value, key) of virusTotalDataResponse.attributes
												.last_https_certificate.subject"
											:key
										>
											<td class="whitespace-nowrap text-sm">{{ key }}</td>
											<td class="whitespace-nowrap text-sm font-semibold">{{ value }}</td>
										</tr>
									</tbody>
								</n-table>
							</template>
						</CardKV>
					</div>
				</n-tab-pane>
			</n-tabs>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Size } from "naive-ui/es/button/src/interface"
import type { ItemProps } from "@/components/common/cards/CardStatsBars.vue"
import type { VirusTotalData } from "@/types/threatIntel.d"
import _pick from "lodash/pick"
import { NButton, NEmpty, NInput, NModal, NStatistic, NTable, NTabPane, NTabs, useMessage } from "naive-ui"
import { computed, defineAsyncComponent, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"

const { iocValue, size } = defineProps<{
	iocValue: string
	size?: Size
}>()

const Badge = defineAsyncComponent(() => import("@/components/common/Badge.vue"))
const CardKV = defineAsyncComponent(() => import("@/components/common/cards/CardKV.vue"))
const CardEntity = defineAsyncComponent(() => import("@/components/common/cards/CardEntity.vue"))
const CardStatsBars = defineAsyncComponent(() => import("@/components/common/cards/CardStatsBars.vue"))
const CodeSource = defineAsyncComponent(() => import("@/components/common/CodeSource.vue"))

const AiIcon = "mage:stars-c"
const showModal = ref<boolean>(false)
const loading = ref<boolean>(false)
const dFormats = useSettingsStore().dateFormat
const message = useMessage()
const virusTotalDataResponse = ref<VirusTotalData | null>(null)
const totalVotes = computed<ItemProps[]>(() =>
	Object.entries(virusTotalDataResponse.value?.attributes.total_votes || {})
		.map(([key, value]) => ({
			value,
			label: key,
			status: getStatusByCategory(key)
		}))
		.sort((a, b) => a.value - b.value)
)
const lastAnalysisStats = computed<ItemProps[]>(() =>
	Object.entries(virusTotalDataResponse.value?.attributes.last_analysis_stats || {})
		.map(([key, value]) => ({
			value,
			label: key,
			status: getStatusByCategory(key)
		}))
		.sort((a, b) => a.value - b.value)
)
const properties = computed(() => {
	return _pick(virusTotalDataResponse.value?.attributes || {}, [
		"regional_internet_registry",
		"continent",
		"last_modification_date",
		"crowdsourced_context",
		"asn",
		"reputation",
		"jarm",
		"country",
		"as_owner",
		"network"
	])
})

function getStatusByCategory(category: string) {
	let status: "success" | "warning" | "error" | "muted" | "primary" = "muted"

	switch (category) {
		case "harmless":
			status = "success"
			break
		case "malicious":
			status = "error"
			break
		case "suspicious":
			status = "warning"
			break
		case "undetected":
		case "timeout":
			status = "muted"
			break
	}
	return status
}

function openResponse() {
	showModal.value = true
}

function analysis() {
	loading.value = true

	Api.threatIntel
		.virusTotalEnrichment(iocValue)
		.then(res => {
			if (res.data.success) {
				virusTotalDataResponse.value = res.data.data.data
				openResponse()
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}
</script>
