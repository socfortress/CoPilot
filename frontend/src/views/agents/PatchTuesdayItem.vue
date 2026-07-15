<template>
	<div class="page flex flex-col gap-4">
		<DetailPageHeader :back-route="routePatchTuesdayItem()">
			<template #title>
				<span class="truncate font-mono text-lg font-semibold">{{ cve }}</span>
			</template>
			<template #meta>
				<span v-if="item" class="text-secondary text-sm">{{ item.affected.product }}</span>
				<span class="text-secondary font-mono text-sm">{{ cycle }}</span>
			</template>
		</DetailPageHeader>

		<n-spin v-if="cycle && cve" :show="loading" class="min-h-40">
			<PatchTuesdayDetail v-if="item" :item />
			<n-empty v-else-if="!loading" description="CVE not found in this cycle" class="h-32 justify-center" />
		</n-spin>
		<n-empty v-else description="Invalid CVE" class="h-48 justify-center" />
	</div>
</template>

<script setup lang="ts">
import type { PatchTuesdayItem } from "@/types/patch-tuesday"
import { NEmpty, NSpin } from "naive-ui"
import { computed } from "vue"
import { useRoute } from "vue-router"
import patchTuesdayApi from "@/api/endpoints/patch-tuesday"
import DetailPageHeader from "@/components/common/DetailPageHeader.vue"
import PatchTuesdayDetail from "@/components/patchTuesday/PatchTuesdayDetail.vue"
import { useEntityDetails } from "@/composables/useEntityDetails"
import { useNavigation, useRouteParam } from "@/composables/useNavigation"

const route = useRoute()
const { routePatchTuesdayItem } = useNavigation()

const cycle = useRouteParam("cycle")
const cve = useRouteParam("cve")
// product disambiguates a CVE that affects several products in the same cycle
const product = computed(() => (route.query.product ? String(route.query.product) : undefined))

// no by-id endpoint: search the CVE within its cycle, filtered to this product
const { loading, entity: item } = useEntityDetails<PatchTuesdayItem, string>({
	entity: () => null,
	id: () => (cycle.value && cve.value ? `${cycle.value}|${cve.value}|${product.value ?? ""}` : null),
	fetch: (_id, signal) =>
		patchTuesdayApi
			.searchCVEs(
				{ cve_ids: [cve.value as string], cycle: cycle.value as string, product: product.value },
				signal
			)
			.then(res => ({
				entity: res.data.success ? (res.data.items?.[0] ?? null) : null,
				message: res.data.message
			})),
	notFoundMessage: "CVE not found in this cycle",
	errorMessage: "An error occurred. Please try again later."
})
</script>
