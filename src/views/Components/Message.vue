<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Message</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/message"
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
			<CardCodeExample title="Basic" class="max-w-2xl">
				<n-space>
					<n-button @click="info">Info(Hover will keep alive)</n-button>
					<n-button @click="error">Error</n-button>
					<n-button @click="warning">Warning</n-button>
					<n-button @click="success">Success</n-button>
					<n-button @click="loading">Loading</n-button>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space>
						<n-button @click="info">Info(Hover will keep alive)</n-button>
						<n-button @click="error">Error</n-button>
						<n-button @click="warning">Warning</n-button>
						<n-button @click="success">Success</n-button>
						<n-button @click="loading">Loading</n-button>
					</n-space>
					`) }}

					{{
						js(`
						const message = useMessage()

						function info() {
							message.info("I don't know why nobody told you how to unfold your love", {
								keepAliveOnHover: true,
								closable: true
							})
						}
						function error() {
							message.error("Once upon a time you dressed so fine", { closable: true })
						}
						function warning() {
							message.warning("How many roads must a man walk down", { closable: true })
						}
						function success() {
							message.success("'Cause you walked hand in hand With another man in my place")
						}
						function loading() {
							message.loading("If I were you, I will realize that I love you more than any other guy")
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import { NSpace, NButton, useMessage } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

const message = useMessage()

function info() {
	message.info("I don't know why nobody told you how to unfold your love", {
		keepAliveOnHover: true,
		closable: true
	})
}
function error() {
	message.error("Once upon a time you dressed so fine", { closable: true })
}
function warning() {
	message.warning("How many roads must a man walk down", { closable: true })
}
function success() {
	message.success("'Cause you walked hand in hand With another man in my place")
}
function loading() {
	message.loading("If I were you, I will realize that I love you more than any other guy")
}
</script>
