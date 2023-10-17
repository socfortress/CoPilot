<template>
	<div class="page">
		<div class="page-header">
			<div class="title">List</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/list"
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
				<n-list>
					<template #header>header</template>
					<template #footer>footer</template>
					<n-list-item>
						<template #prefix>
							<n-button>Prefix</n-button>
						</template>
						<template #suffix>
							<n-button>Suffix</n-button>
						</template>
						<n-thing title="Thing" title-extra="extra" description="description">
							Biu
							<br />
							Biu
							<br />
							Biu
							<br />
						</n-thing>
					</n-list-item>
					<n-list-item>
						<n-thing title="Thing" title-extra="extra" description="description" />
					</n-list-item>
				</n-list>
				<template #code="{ html }">
					{{ html(`
					<n-list>
						<template #header>header</template>
						<template #footer>footer</template>
						<n-list-item>
							<template #prefix>
								<n-button>Prefix</n-button>
							</template>
							<template #suffix>
								<n-button>Suffix</n-button>
							</template>
							<n-thing title="Thing" title-extra="extra" description="description">
								Biu
								<br />
								Biu
								<br />
								Biu
								<br />
							</n-thing>
						</n-list-item>
						<n-list-item>
							<n-thing title="Thing" title-extra="extra" description="description" />
						</n-list-item>
					</n-list>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NList, NListItem, NThing, NButton } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
