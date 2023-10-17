<template>
	<div class="page">
		<div class="page-header">
			<div class="title">Tabs</div>
			<div class="links">
				<a
					href="https://www.naiveui.com/en-US/light/components/tabs"
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
				<n-space vertical>
					<n-radio-group v-model:value="placement">
						<n-radio label="top" value="top" />
						<n-radio label="bottom" value="bottom" />
						<n-radio label="left" value="left" />
						<n-radio label="right" value="right" />
					</n-radio-group>
					<n-radio-group v-model:value="type">
						<n-radio label="card" value="card" />
						<n-radio label="bar" value="bar" />
						<n-radio label="line" value="line" />
					</n-radio-group>
					<n-tabs
						:key="type + placement"
						:type="type"
						animated
						:placement="placement"
						:style="placement === 'left' || placement === 'right' ? { height: '240px' } : undefined"
					>
						<n-tab-pane name="oasis" tab="Oasis"> Wonderwall </n-tab-pane>
						<n-tab-pane name="the beatles" tab="the Beatles"> Hey Jude </n-tab-pane>
						<n-tab-pane name="jay chou" tab="Jay Chou"> Qilixiang </n-tab-pane>
						<n-tab-pane name="oasis1" tab="Oasis1"> Wonderwall </n-tab-pane>
						<n-tab-pane name="the beatles1" tab="the Beatles1"> Hey Jude </n-tab-pane>
						<n-tab-pane name="jay chou1" tab="Jay Chou1"> Qilixiang </n-tab-pane>
						<n-tab-pane name="oasis2" tab="Oasis2"> Wonderwall </n-tab-pane>
						<n-tab-pane name="the beatles2" tab="the Beatles2"> Hey Jude </n-tab-pane>
						<n-tab-pane name="jay chou2" tab="Jay Chou2"> Qilixiang </n-tab-pane>
						<n-tab-pane name="oasis3" tab="Oasis3"> Wonderwall </n-tab-pane>
						<n-tab-pane name="the beatles3" tab="the Beatles3"> Hey Jude </n-tab-pane>
						<n-tab-pane name="jay chou3" tab="Jay Chou3"> Qilixiang </n-tab-pane>
						<n-tab-pane name="oasis4" tab="Oasis4"> Wonderwall </n-tab-pane>
						<n-tab-pane name="the beatles4" tab="the Beatles4"> Hey Jude </n-tab-pane>
						<n-tab-pane name="jay chou4" tab="Jay Chou4"> Qilixiang </n-tab-pane>
						<n-tab-pane name="oasis5" tab="Oasis5"> Wonderwall </n-tab-pane>
						<n-tab-pane name="the beatles5" tab="the Beatles5"> Hey Jude </n-tab-pane>
						<n-tab-pane name="jay chou5" tab="Jay Chou5"> Qilixiang </n-tab-pane>
					</n-tabs>
				</n-space>
				<template #code="{ html, js }">
					{{ html(`
					<n-space vertical>
						<n-radio-group v-model:value="placement">
							<n-radio label="top" value="top" />
							<n-radio label="bottom" value="bottom" />
							<n-radio label="left" value="left" />
							<n-radio label="right" value="right" />
						</n-radio-group>
						<n-radio-group v-model:value="type">
							<n-radio label="card" value="card" />
							<n-radio label="bar" value="bar" />
							<n-radio label="line" value="line" />
						</n-radio-group>
						<n-tabs
							:key="type + placement"
							:type="type"
							animated
							:placement="placement"
							:style="placement === 'left' || placement === 'right' ? { height: '240px' } : undefined"
						>
							<n-tab-pane name="oasis" tab="Oasis"> Wonderwall </n-tab-pane>
							<n-tab-pane name="the beatles" tab="the Beatles"> Hey Jude </n-tab-pane>
							<n-tab-pane name="jay chou" tab="Jay Chou"> Qilixiang </n-tab-pane>
							<n-tab-pane name="oasis1" tab="Oasis1"> Wonderwall </n-tab-pane>
							<n-tab-pane name="the beatles1" tab="the Beatles1"> Hey Jude </n-tab-pane>
							<n-tab-pane name="jay chou1" tab="Jay Chou1"> Qilixiang </n-tab-pane>
							<n-tab-pane name="oasis2" tab="Oasis2"> Wonderwall </n-tab-pane>
							<n-tab-pane name="the beatles2" tab="the Beatles2"> Hey Jude </n-tab-pane>
							<n-tab-pane name="jay chou2" tab="Jay Chou2"> Qilixiang </n-tab-pane>
							<n-tab-pane name="oasis3" tab="Oasis3"> Wonderwall </n-tab-pane>
							<n-tab-pane name="the beatles3" tab="the Beatles3"> Hey Jude </n-tab-pane>
							<n-tab-pane name="jay chou3" tab="Jay Chou3"> Qilixiang </n-tab-pane>
							<n-tab-pane name="oasis4" tab="Oasis4"> Wonderwall </n-tab-pane>
							<n-tab-pane name="the beatles4" tab="the Beatles4"> Hey Jude </n-tab-pane>
							<n-tab-pane name="jay chou4" tab="Jay Chou4"> Qilixiang </n-tab-pane>
							<n-tab-pane name="oasis5" tab="Oasis5"> Wonderwall </n-tab-pane>
							<n-tab-pane name="the beatles5" tab="the Beatles5"> Hey Jude </n-tab-pane>
							<n-tab-pane name="jay chou5" tab="Jay Chou5"> Qilixiang </n-tab-pane>
						</n-tabs>
					</n-space>
					`) }}

					{{
						js(`
						import { ref } from "vue"
						import type { TabsProps } from "naive-ui"

						const placement = ref<NonNullable<TabsProps["placement"]>>("top")
						const type = ref<TabsProps["type"]>("line")
						`)
					}}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Segment">
				<n-tabs type="segment" animated>
					<n-tab-pane name="oasis" tab="Oasis"> Wonderwall </n-tab-pane>
					<n-tab-pane name="the beatles" tab="the Beatles"> Hey Jude </n-tab-pane>
					<n-tab-pane name="jay chou" tab="Jay Chou"> Qilixiang </n-tab-pane>
				</n-tabs>
				<template #code="{ html }">
					{{ html(`
					<n-tabs type="segment" animated>
						<n-tab-pane name="oasis" tab="Oasis"> Wonderwall </n-tab-pane>
						<n-tab-pane name="the beatles" tab="the Beatles"> Hey Jude </n-tab-pane>
						<n-tab-pane name="jay chou" tab="Jay Chou"> Qilixiang </n-tab-pane>
					</n-tabs>
					`) }}
				</template>
			</CardCodeExample>

			<CardCodeExample title="Addable">
				<template #description> Add some tabs. Only work with <n-text code>'card'</n-text> type. </template>
				<n-tabs
					v-model:value="valueRef"
					type="card"
					:addable="addableRef"
					:closable="closableRef"
					tab-style="min-width: 80px;"
					@close="handleClose"
					@add="handleAdd"
				>
					<n-tab-pane v-for="panel in panelsRef" :key="panel" :name="panel">
						{{ panel }}
					</n-tab-pane>
					<template #prefix> Prefix </template>
					<template #suffix> Suffix </template>
				</n-tabs>
				<template #code="{ html, js }">
					{{ html(`
					<n-tabs
						v-model:value="value"
						type="card"
						:addable="addable"
						:closable="closable"
						tab-style="min-width: 80px;"
						@close="handleClose"
						@add="handleAdd"
					>
						<n-tab-pane v-for="panel in panels" :key="panel" :name="panel"> \{\{ panel \}\} </n-tab-pane>
						<template #prefix> Prefix </template>
						<template #suffix> Suffix </template>
					</n-tabs>
					`) }}

					{{
						js(`
						const valueRef = ref(1)
						const panelsRef = ref([1, 2, 3, 4, 5])
						const addableRef = computed(() => {
							return {
								disabled: panelsRef.value.length >= 10
							}
						})
						const closableRef = computed(() => {
							return panelsRef.value.length > 1
						})

						function handleAdd() {
							const newValue = Math.max(...panelsRef.value) + 1
							panelsRef.value.push(newValue)
							valueRef.value = newValue
						}
						function handleClose(name: number) {
							const { value: panels } = panelsRef
							const nameIndex = panels.findIndex(panelName => panelName === name)
							if (!~nameIndex) return
							panels.splice(nameIndex, 1)
							if (name === valueRef.value) {
								valueRef.value = panels[Math.min(nameIndex, panels.length - 1)]
							}
						}
						`)
					}}
				</template>
			</CardCodeExample>
		</div>
	</div>
</template>

<script lang="ts" setup>
import {   NSpace, NRadioGroup, NRadio, NTabs, NTabPane, NText } from "naive-ui"
import Icon from "@/components/common/Icon.vue"
const ExternalIcon = "tabler:external-link"

import { computed, ref } from "vue"
import type { TabsProps } from "naive-ui"

const placement = ref<NonNullable<TabsProps["placement"]>>("top")
const type = ref<TabsProps["type"]>("line")

const valueRef = ref(1)
const panelsRef = ref([1, 2, 3, 4, 5])
const addableRef = computed(() => {
	return {
		disabled: panelsRef.value.length >= 10
	}
})
const closableRef = computed(() => {
	return panelsRef.value.length > 1
})

function handleAdd() {
	const newValue = Math.max(...panelsRef.value) + 1
	panelsRef.value.push(newValue)
	valueRef.value = newValue
}
function handleClose(name: number) {
	const { value: panels } = panelsRef
	const nameIndex = panels.findIndex(panelName => panelName === name)
	if (!~nameIndex) return
	panels.splice(nameIndex, 1)
	if (name === valueRef.value) {
		valueRef.value = panels[Math.min(nameIndex, panels.length - 1)]
	}
}
</script>
