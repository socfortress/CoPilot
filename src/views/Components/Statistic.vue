<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Statistic</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/statistic"
					target="_blank"
					alt="docs"
					rel="nofollow noopener noreferrer"
				>
					<Icon :name="ExternalIcon" :size="16" />
					docs
				</a>
			</div>
		</div>

		<div class="components-list">
			<CardCodeExample title="Basic" class="max-w-lg">
				<n-row>
					<n-col :span="12">
						<n-statistic label="Statistic" :value="99">
							<template #prefix>
								<Icon :name="Save" />
							</template>
							<template #suffix>/ 100</template>
						</n-statistic>
					</n-col>
					<n-col :span="12">
						<n-statistic label="Active Users">1,234,123</n-statistic>
					</n-col>
				</n-row>
				<template #code="{ html }">
					{{ html(`
					<n-row>
						<n-col :span="12">
							<n-statistic label="Statistic" :value="99">
								<template #prefix>
									<n-icon>
										<Save />
									</n-icon>
								</template>
								<template #suffix>/ 100</template>
							</n-statistic>
						</n-col>
						<n-col :span="12">
							<n-statistic label="Active Users">1,234,123</n-statistic>
						</n-col>
					</n-row>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NRow, NCol, NStatistic } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
const Save = "carbon:save"
</script>
