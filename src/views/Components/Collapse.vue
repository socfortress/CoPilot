<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Collapse</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/collapse"
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
				<n-collapse>
					<n-collapse-item title="right" name="1">
						<div>good</div>
					</n-collapse-item>
					<n-collapse-item title="right" name="2">
						<div>nice</div>
					</n-collapse-item>
					<n-collapse-item title="right" name="3">
						<div>very good</div>
					</n-collapse-item>
				</n-collapse>
				<template #code="{ html }">
					{{ html(`
					<n-collapse>
						<n-collapse-item title="right" name="1">
							<div>good</div>
						</n-collapse-item>
						<n-collapse-item title="right" name="2">
							<div>nice</div>
						</n-collapse-item>
						<n-collapse-item title="right" name="3">
							<div>very good</div>
						</n-collapse-item>
					</n-collapse>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Arrow placement">
				<template #description>
					Use
					<n-text code>arrow-placement</n-text>
					to set the placement of arrow.
				</template>
				<n-collapse arrow-placement="right">
					<n-collapse-item title="right" name="1">
						<div>good</div>
					</n-collapse-item>
					<n-collapse-item title="right" name="2">
						<div>nice</div>
					</n-collapse-item>
					<n-collapse-item title="right" name="3">
						<div>very good</div>
					</n-collapse-item>
				</n-collapse>
				<template #code="{ html }">
					{{ html(`
					<n-collapse arrow-placement="right">
						<n-collapse-item title="right" name="1">
							<div>good</div>
						</n-collapse-item>
						<n-collapse-item title="right" name="2">
							<div>nice</div>
						</n-collapse-item>
						<n-collapse-item title="right" name="3">
							<div>very good</div>
						</n-collapse-item>
					</n-collapse>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Customize icon">
				<n-collapse>
					<template #header-extra>
						<Icon :name="CashIcon" />
					</template>
					<template #arrow>
						<Icon :name="CashIcon" />
					</template>
					<n-collapse-item title="Bronze" name="1">
						<div>good</div>
					</n-collapse-item>
					<n-collapse-item title="Silver" name="2">
						<div>nice</div>
					</n-collapse-item>
					<n-collapse-item title="Gold" name="3">
						<div>very good</div>
					</n-collapse-item>
				</n-collapse>
				<template #code="{ html }">
					{{ html(`
					<n-collapse>
						<template #header-extra>
							<n-icon><cash-icon /></n-icon>
						</template>
						<template #arrow>
							<n-icon>
								<cash-icon />
							</n-icon>
						</template>
						<n-collapse-item title="Bronze" name="1">
							<div>good</div>
						</n-collapse-item>
						<n-collapse-item title="Silver" name="2">
							<div>nice</div>
						</n-collapse-item>
						<n-collapse-item title="Gold" name="3">
							<div>very good</div>
						</n-collapse-item>
					</n-collapse>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Extra info in header">
				<template #description>Put some info on the right side of the item.</template>
				<n-collapse>
					<n-collapse-item title="right" name="1">
						good
						<template #header-extra>good</template>
					</n-collapse-item>
					<n-collapse-item title="right" name="2">
						nice
						<template #header-extra>nice</template>
					</n-collapse-item>
					<n-collapse-item title="right" name="3">
						very good
						<template #header-extra>very good</template>
					</n-collapse-item>
				</n-collapse>
				<template #code="{ html }">
					{{ html(`
					<n-collapse>
						<n-collapse-item title="right" name="1">
							good
							<template #header-extra>good</template>
						</n-collapse-item>
						<n-collapse-item title="right" name="2">
							nice
							<template #header-extra>nice</template>
						</n-collapse-item>
						<n-collapse-item title="right" name="3">
							very good
							<template #header-extra>very good</template>
						</n-collapse-item>
					</n-collapse>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NCollapse, NCollapseItem, NText } from "naive-ui"
const CashIcon = "ion:cash-outline"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"
</script>
