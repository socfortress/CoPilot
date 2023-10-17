<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Alert</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/alert"
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
				<n-space vertical :size="12">
					<n-alert title="Default Text" type="default">
						<template #icon>
							<Icon :name="Airplane" />
						</template>
						Gee it's good to be back home
					</n-alert>
					<n-alert title="Info Text" type="info">Gee it's good to be back home</n-alert>
					<n-alert title="Success Text" type="success" closable>
						Leave it till tomorrow to unpack my case
					</n-alert>
					<n-alert title="Warning Text" type="warning" closable>Honey disconnect the phone</n-alert>
					<n-alert title="Error Text" type="error" closable>I'm back in the U.S.S.R.</n-alert>
				</n-space>
				<template #code="{ html }">
					{{ html(`
					<n-space vertical :size="12">
						<n-alert title="Default Text" type="default">
							<template #icon>
								<n-icon>
									<Airplane />
								</n-icon>
							</template>
							Gee it's good to be back home
						</n-alert>
						<n-alert title="Info Text" type="info">Gee it's good to be back home</n-alert>
						<n-alert title="Success Text" type="success" closable>
							Leave it till tomorrow to unpack my case
						</n-alert>
						<n-alert title="Warning Text" type="warning" closable>Honey disconnect the phone</n-alert>
						<n-alert title="Error Text" type="error" closable>I'm back in the U.S.S.R.</n-alert>
					</n-space>
					`) }}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NAlert } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const Airplane = "ion:airplane"
</script>
