<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Page Header</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/page-header"
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
			<CardCodeExample title="Basic">
				<n-page-header subtitle="A podcast to improve designs" @back="handleBack">
					<n-grid :cols="5">
						<n-gi>
							<n-statistic label="Episodes" value="125" />
						</n-gi>
						<n-gi>
							<n-statistic label="Guests" value="22" />
						</n-gi>
						<n-gi>
							<n-statistic label="Apologies" value="36" />
						</n-gi>
						<n-gi>
							<n-statistic label="Topics" value="83" />
						</n-gi>
						<n-gi>
							<n-statistic label="Reference Links" value="2,346" />
						</n-gi>
					</n-grid>
					<template #title>
						<a href="#" style="text-decoration: none; color: inherit">Super Podcast</a>
					</template>
					<template #header>
						<n-breadcrumb>
							<n-breadcrumb-item>Podcast</n-breadcrumb-item>
							<n-breadcrumb-item>Best Collection</n-breadcrumb-item>
							<n-breadcrumb-item>Ultimate Best Collection</n-breadcrumb-item>
							<n-breadcrumb-item>Super Podcast</n-breadcrumb-item>
						</n-breadcrumb>
					</template>
					<template #avatar>
						<n-avatar src="https://picsum.photos/seed/6Dz4vOn/160/160" />
					</template>
					<template #extra>
						<n-space>
							<n-button>Refresh</n-button>
							<n-dropdown :options="options" placement="bottom-start">
								<n-button :bordered="false" style="padding: 0 4px">···</n-button>
							</n-dropdown>
						</n-space>
					</template>
					<template #footer>As of April 3, 2021</template>
				</n-page-header>
				<template #code="{ html, js }">
					{{ html(`
					<n-page-header subtitle="A podcast to improve designs" @back="handleBack">
						<n-grid :cols="5">
							<n-gi>
								<n-statistic label="Episodes" value="125" />
							</n-gi>
							<n-gi>
								<n-statistic label="Guests" value="22" />
							</n-gi>
							<n-gi>
								<n-statistic label="Apologies" value="36" />
							</n-gi>
							<n-gi>
								<n-statistic label="Topics" value="83" />
							</n-gi>
							<n-gi>
								<n-statistic label="Reference Links" value="2,346" />
							</n-gi>
						</n-grid>
						<template #title>
							<a href="#" style="text-decoration: none; color: inherit">Super Podcast</a>
						</template>
						<template #header>
							<n-breadcrumb>
								<n-breadcrumb-item>Podcast</n-breadcrumb-item>
								<n-breadcrumb-item>Best Collection</n-breadcrumb-item>
								<n-breadcrumb-item>Ultimate Best Collection</n-breadcrumb-item>
								<n-breadcrumb-item>Super Podcast</n-breadcrumb-item>
							</n-breadcrumb>
						</template>
						<template #avatar>
							<n-avatar src="https://picsum.photos/seed/6Dz4vOn/160/160" />
						</template>
						<template #extra>
							<n-space>
								<n-button>Refresh</n-button>
								<n-dropdown :options="options" placement="bottom-start">
									<n-button :bordered="false" style="padding: 0 4px">···</n-button>
								</n-dropdown>
							</n-space>
						</template>
						<template #footer>As of April 3, 2021</template>
					</n-page-header>
					`) }}
					{{
						js(`
						const message = useMessage()
						function handleBack() {
							message.info("[onBack]")
						}
						const options = [
							{
								label: "More episodes",
								key: "1"
							},
							{
								label: "More episodes",
								key: "2"
							},
							{
								label: "More episodes",
								key: "3"
							}
						]
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import {
	NPageHeader,
	NGrid,
	NGi,
	useMessage,
	NStatistic,
	NBreadcrumb,
	NBreadcrumbItem,
	NAvatar,
	NSpace,
	NButton,
	NDropdown
} from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const message = useMessage()
function handleBack() {
	message.info("[onBack]")
}
const options = [
	{
		label: "More episodes",
		key: "1"
	},
	{
		label: "More episodes",
		key: "2"
	},
	{
		label: "More episodes",
		key: "3"
	}
]
</script>
