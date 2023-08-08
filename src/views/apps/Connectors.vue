<template>
    <div class="page-table scrollable only-y">
        <div class="page-header">
            <h1>Connectors</h1>
            <h4>Configure connections to your toolset.</h4>
            <el-breadcrumb separator="/">
                <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
                <el-breadcrumb-item>Connectors</el-breadcrumb-item>
            </el-breadcrumb>
        </div>

        <div class="table-box card-base card-shadow--medium scrollable only-x" v-loading="loading">
            <table class="styled striped">
                <thead>
                    <tr>
                        <th scope="col">Connector Name</th>
                        <th scope="col">Connector Description</th>
                        <th scope="col">Connector Supports</th>
                        <th scope="col">Connector Configured</th>
                        <th scope="col">Connector Verified</th>
                        <th scope="col">Connector Options</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="connector in connectors" :key="connector.id">
                        <!-- Display the connector details in the table -->
                        <td>{{ connector.connector_name }}</td>
                        <td>{{ connector.connector_description }}</td>
                        <td>{{ connector.connector_supports }}</td>
                        <td>
                            <el-button type="primary" v-if="connector.connector_configured">True</el-button>
                            <el-button type="info" v-else>False</el-button>
                        </td>
                        <!-- Show the connector verified which is in the `connector` table -->
                        <td>
                            <el-button type="success" v-if="connector.connector_verified">True</el-button>
                            <el-button type="danger" v-else>False</el-button>
                        </td>
                        <td>
                            <div class="btn-group" role="group">
                                <!--If the connector is not already configured then display the configure button -->
                                <el-button type="primary" round v-if="!connector.connector_configured" @click="openConfigDialog(connector)">
                                    Configure
                                </el-button>

                                <el-button type="warning" round v-else @click="openConfigDialog(connector)"> Update </el-button>
                                <!--<button type="button" class="btn btn-info btn-sm" @click="deleteConnector(connector)">Delete</button>-->
                            </div>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <el-dialog
            title="Connector configuration"
            v-model="showConfigDialog"
            :close-on-click-modal="true"
            :close-on-press-escape="true"
            width="600px"
        >
            <ConfigForm :connector="currentConnector" />
        </el-dialog>
    </div>
</template>

<script lang="ts">
import Api from "@/api"
import { defineComponent } from "vue"
import ConfigForm from "@/components/connectors/ConfigForm"
import { Connector } from "@/types/connectors"

export default defineComponent({
    data() {
        return {
            connectors: [] as Connector[],
            currentConnector: null,

            // Configure Modal
            isConfigureModalActive: false,
            isConfigureModalFileActive: false,

            // Update Modal
            isUpdateModalActive: false,

            loading: false,
            showConfigDialog: false,

            successMessage: "",
            errorMessage: "",
            connectorForm: {
                connector_url: "",
                username: "",
                password: "",
                connector_api_key: ""
            }
        }
    },
    methods: {
        openConfigDialog(connector) {
            this.currentConnector = connector
            this.showConfigDialog = true
        },

        getConnectors() {
            this.loading = true

            Api.connectors
                .getAll()
                .then(res => {
                    this.connectors = res.data.connectors
                })
                .catch(err => {
                    console.error(err)
                })
                .finally(() => {
                    this.loading = false
                })
        }
    },
    created() {
        this.getConnectors()
    },
    components: {
        ConfigForm
    }
})
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_variables";

.page-table {
    padding-left: 20px;
    padding-right: 15px;
    padding-bottom: 20px;
}
.table-box {
    overflow: auto;
}
</style>
