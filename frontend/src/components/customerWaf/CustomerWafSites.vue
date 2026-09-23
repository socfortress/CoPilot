<template>
	<CustomerWafError v-if="error" :error />
	<div v-else-if="loading" class="grid-auto-fit-250 grid gap-3">
		<n-skeleton v-for="n of 4" :key="n" :height="112" :sharp="false" class="rounded-lg" />
	</div>
	<n-empty v-else-if="!sites.length" description="This WAF protects no sites yet" class="min-h-52 justify-center" />
	<div v-else class="grid-auto-fit-250 grid gap-3">
		<section
			v-for="s of sites"
			:key="s.id"
			class="border-default flex flex-col overflow-hidden rounded-lg border"
			:class="{ 'opacity-60': !s.is_enabled }"
		>
			<header class="bg-secondary border-default flex items-center justify-between gap-2 border-b px-3 py-2">
				<span class="truncate font-semibold">{{ s.name }}</span>
				<n-tag size="small" round :bordered="false" :type="s.detection_mode ? 'warning' : 'success'">
					<template #icon><Icon :name="s.detection_mode ? DetectIcon : ShieldIcon" :size="12" /></template>
					{{ s.detection_mode ? "detect only" : "blocking" }}
				</n-tag>
			</header>
			<div class="flex flex-col gap-1.5 p-3 text-xs">
				<div class="flex items-center gap-2">
					<Icon :name="GlobeIcon" :size="13" class="text-secondary" />
					<span class="truncate font-mono">{{ s.hostname || "any hostname" }}</span>
				</div>
				<div class="flex items-center gap-2">
					<Icon :name="UpstreamIcon" :size="13" class="text-secondary" />
					<span class="text-secondary truncate font-mono">{{ s.upstream_url }}</span>
				</div>
				<div v-if="!s.is_enabled" class="text-secondary">Disabled on the WAF</div>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CustomerWafInstance, CustomerWafSite } from "@/types/customer-waf"
import { NEmpty, NSkeleton, NTag } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import CustomerWafError from "./CustomerWafError.vue"

const { customerCode, instance } = defineProps<{ customerCode: string; instance: CustomerWafInstance }>()

const ShieldIcon = "carbon:security"
const DetectIcon = "carbon:view"
const GlobeIcon = "carbon:earth"
const UpstreamIcon = "carbon:arrow-right"

const loading = ref(false)
const error = ref<ApiError | null>(null)
const sites = ref<CustomerWafSite[]>([])

onBeforeMount(() => {
	loading.value = true
	Api.customerWaf
		.getSites(customerCode, instance.id)
		.then(res => {
			sites.value = res.data.sites
		})
		.catch((err: ApiError) => {
			error.value = err
		})
		.finally(() => {
			loading.value = false
		})
})
</script>
