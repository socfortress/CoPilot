<template>
	<n-tabs type="line" animated>
		<n-tab-pane name="graylog" tab="Graylog Content Packs" display-directive="show">
			<StackProvisioningList />
		</n-tab-pane>
		<n-tab-pane name="influxdb" tab="InfluxDB Checks" display-directive="show">
			<InfluxDbChecksList />
		</n-tab-pane>
	</n-tabs>
</template>

<script setup lang="ts">
import { NTabPane, NTabs } from "naive-ui"
import InfluxDbChecksList from "./influxdb/InfluxDbChecksList.vue"
import StackProvisioningList from "./StackProvisioningList.vue"
</script>
