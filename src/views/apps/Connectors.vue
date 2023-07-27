<template>
  <div class="page-table scrollable only-y" id="affix-container">
      <div class="page-header">
          <h1>Connectors</h1>
          <h4>Configure connections to your toolset.</h4>
          <el-breadcrumb separator="/">
              <el-breadcrumb-item :to="{ path: '/' }"><i class="mdi mdi-home-outline"></i></el-breadcrumb-item>
              <el-breadcrumb-item>Components</el-breadcrumb-item>
              <el-breadcrumb-item>Tables</el-breadcrumb-item>
              <el-breadcrumb-item>Table</el-breadcrumb-item>
          </el-breadcrumb>
      </div>

      <div class="table-box card-base card-shadow--medium scrollable only-x">
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
                          <el-button type="primary" v-if="connector.connector_configured == true">True</el-button>
                          <el-button type="info" v-else>False</el-button>
                      </td>
                      <!-- Show the connector verified which is in the `connector` table -->
                      <td>
                          <el-button type="success" v-if="connector.connector_verified == true">True</el-button>
                          <el-button type="danger" v-else>False</el-button>
                      </td>
                      <td>
                          <div class="btn-group" role="group">
                              <!--If the connector is not already configured then display the configure button -->
                              <el-button
                                  type="primary"
                                  round
                                  v-if="
                                      (connector.connector_configured == false ||
                                          connector.connector_configured == null) &&
                                      connector.connector_name.toLowerCase() !== 'velociraptor'
                                  "
                                  @click="openConfigureModal(connector)"
                              >
                                  Configure
                              </el-button>

                              <!--If the connector is not already configured and the connector_name IS `velociraptor`, then display the configure button -->
                              <el-button
                                  type="primary"
                                  round
                                  v-if="
                                      (connector.connector_configured == false ||
                                          connector.connector_configured == null) &&
                                      connector.connector_name.toLowerCase() === 'velociraptor'
                                  "
                                  @click="openConfigureModalFile(connector)"
                              >
                                  Configure
                              </el-button>
                              <!-- If the connector is already configured and the connector_name is not `shuffle` or `dfir-iris` to lower, then display the update button -->
                              <el-button
                                  type="warning"
                                  round
                                  v-if="
                                      connector.connector_configured == true &&
                                      // connector.connector_name.toLowerCase() !==
                                      //   'shuffle' &&
                                      // connector.connector_name.toLowerCase() !==
                                      //   'dfir-iris' &&
                                      connector.connector_name.toLowerCase() !== 'velociraptor'
                                  "
                                  @click="openUpdateModal(connector)"
                              >
                                  Update
                              </el-button>
                              <!-- Update Velociraptor -->
                              <el-button
                                  type="warning"
                                  round
                                  v-if="
                                      connector.connector_configured == true &&
                                      // connector.connector_name.toLowerCase() !==
                                      //   'shuffle' &&
                                      // connector.connector_name.toLowerCase() !==
                                      //   'dfir-iris' &&
                                      connector.connector_name.toLowerCase() === 'velociraptor'
                                  "
                                  @click="openConfigureModalFile(connector)"
                              >
                                  Update
                              </el-button>
                              <!-- If the connector is already configured and the connector_name IS `shuffle` or `dfir-iris` to lower, then display the update button -->
                              <!-- <el-button type="warning" round
                            v-if="
                              connector.connector_configured == true &&
                              (connector.connector_name.toLowerCase() ===
                                'shuffle' ||
                                connector.connector_name.toLowerCase() ===
                                  'dfir-iris')
                            "
                            @click="openUpdateModal(connector)"
                          >
                            Update
                          </el-button> -->

                              <!--<button type="button" class="btn btn-info btn-sm" @click="updateConnector(connector)">Update</button>-->
                              <!--<button type="button" class="btn btn-info btn-sm" @click="deleteConnector(connector)">Delete</button>-->
                          </div>
                      </td>
                  </tr>
              </tbody>
          </table>
      </div>

      <!-- Configure Modal Username and Password API Key -->
      <div v-bind:class="{ 'modal-window': true, 'is-active': isConfigureModalActive }">
          <div class="modal-background" @click="openConfigureModal = false"></div>
          <div>
              <el-form
                  :model="connectorForm"
                  status-icon
                  :rules="rules2"
                  ref="connectorForm"
                  label-width="120px"
                  class="demo-ruleForm"
              >
                  <div class="modal-card">
                      <header class="modal-card-head">
                          <h2 class="modal-card-title">
                              Configure {{ currentConnector ? currentConnector.connector_name : "" }}
                          </h2>
                          <img
                              :src="`/src/assets/images/${
                                  currentConnector
                                      ? currentConnector.connector_name.toLowerCase() + '.svg'
                                      : 'default-logo.svg'
                              }`"
                              alt="Logo"
                              class="modal-logo"
                          />
                      </header>
                      <section class="modal-card-body">
                          <div class="field">
                              <label class="label">Connector URL</label>
                              <div class="control">
                                  <input class="input" type="text" v-model="connectorForm.connector_url" required />
                              </div>
                          </div>

                          <!-- API Key input for dfir-iris and shuffle -->
                          <div
                              class="field"
                              v-if="
                                  ['dfir-iris', 'shuffle'].includes(
                                      currentConnector ? currentConnector.connector_name.toLowerCase() : ''
                                  )
                              "
                          >
                              <label class="label">API Key</label>
                              <div class="control">
                                  <input
                                      class="input"
                                      type="text"
                                      v-model="connectorForm.connector_api_key"
                                      required
                                  />
                              </div>
                          </div>

                          <!-- Username and Password inputs for other connectors -->
                          <template v-else>
                              <div class="field">
                                  <label class="label">Username</label>
                                  <div class="control">
                                      <input class="input" type="text" v-model="connectorForm.username" required />
                                  </div>
                              </div>
                              <div class="field">
                                  <label class="label">Password</label>
                                  <div class="control">
                                      <input
                                          class="input"
                                          type="password"
                                          v-model="connectorForm.password"
                                          required
                                      />
                                  </div>
                              </div>
                          </template>

                          <div class="field">
                              <div class="control">
                                  <button class="button is-primary" type="submit" @click.prevent="configureConnector">
                                      Save
                                  </button>
                                  <button class="button" type="button" @click="closeDialogUserandPass">Cancel</button>
                              </div>
                          </div>
                      </section>
                  </div>
              </el-form>
          </div>
      </div>

      <!-- Configure Modal File -->
      <div v-bind:class="{ 'modal-window': true, 'is-active': isConfigureModalFileActive }">
          <div class="modal-background" @click="openConfigureModalFile = false"></div>
          <div>
              <el-form
                  :model="connectorForm"
                  status-icon
                  :rules="rules2"
                  ref="connectorForm"
                  label-width="120px"
                  class="demo-ruleForm"
              >
                  <div class="modal-card">
                      <header class="modal-card-head">
                          <h2 class="modal-card-title">
                              Configure File {{ currentConnector ? currentConnector.connector_name : "" }}
                          </h2>
                          <img
                              :src="`/src/assets/images/${
                                  currentConnector
                                      ? currentConnector.connector_name.toLowerCase() + '.svg'
                                      : 'default-logo.svg'
                              }`"
                              alt="Logo"
                              class="modal-logo"
                          />
                      </header>
                      <section class="modal-card-body">
                          <!-- Add the el-upload component here -->
                          <el-upload
                              class="upload-demo"
                              action="http://localhost:5000/connectors/upload"
                              :on-preview="handlePreview"
                              :on-remove="handleRemove"
                              :before-remove="beforeRemove"
                              :on-success="handleSuccess"
                              multiple
                              drag
                              :limit="3"
                              :on-exceed="handleExceed"
                              :file-list="fileList"
                          >
                              <i class="el-icon-upload"></i>
                              <div class="el-upload__text">Drop file here or <em>click to upload</em></div>
                              <div class="el-upload__tip" slot="tip">jpg/png files with a size less than 500kb</div>
                          </el-upload>
                          <!-- Add the cancel and submit buttons -->
                          <div class="field">
                              <div class="control">
                                  <button class="button" type="button" @click="closeConfigureModuleFile">
                                      Cancel
                                  </button>
                              </div>
                          </div>
                          <!-- Rest of your existing code... -->
                      </section>
                  </div>
              </el-form>
          </div>
      </div>

      <!-- Update Modal Username and Password-->
      <div v-bind:class="{ 'modal-window': true, 'is-active': isUpdateModalActive }">
          <div class="modal-background" @click="openUpdateModal = false"></div>
          <div>
              <el-form
                  :model="connectorForm"
                  status-icon
                  :rules="rules2"
                  ref="connectorForm"
                  label-width="120px"
                  class="demo-ruleForm"
              >
                  <div class="modal-card">
                      <header class="modal-card-head">
                          <h2 class="modal-card-title">
                              Update {{ currentConnector ? currentConnector.connector_name : "" }}
                          </h2>
                          <img
                              :src="`/src/assets/images/${
                                  currentConnector
                                      ? currentConnector.connector_name.toLowerCase() + '.svg'
                                      : 'default-logo.svg'
                              }`"
                              alt="Logo"
                              class="modal-logo"
                          />
                      </header>
                      <section class="modal-card-body">
                          <div class="field">
                              <label class="label">Connector URL</label>
                              <div class="control">
                                  <input class="input" type="text" v-model="connectorForm.connector_url" required />
                              </div>
                          </div>

                          <!-- API Key input for dfir-iris and shuffle -->
                          <div
                              class="field"
                              v-if="
                                  ['dfir-iris', 'shuffle'].includes(
                                      currentConnector ? currentConnector.connector_name.toLowerCase() : ''
                                  )
                              "
                          >
                              <label class="label">API Key</label>
                              <div class="control">
                                  <input
                                      class="input"
                                      type="text"
                                      v-model="connectorForm.connector_api_key"
                                      required
                                  />
                              </div>
                          </div>

                          <!-- Username and Password inputs for other connectors -->
                          <template v-else>
                              <div class="field">
                                  <label class="label">Username</label>
                                  <div class="control">
                                      <input class="input" type="text" v-model="connectorForm.username" required />
                                  </div>
                              </div>
                              <div class="field">
                                  <label class="label">Password</label>
                                  <div class="control">
                                      <input
                                          class="input"
                                          type="password"
                                          v-model="connectorForm.password"
                                          required
                                      />
                                  </div>
                              </div>
                          </template>

                          <div class="field">
                              <div class="control">
                                  <button class="button is-primary" type="submit" @click.prevent="updateConnector">
                                      Save
                                  </button>
                                  <button class="button" type="button" @click="closeUpdateModal">Cancel</button>
                              </div>
                          </div>
                      </section>
                  </div>
              </el-form>
          </div>
      </div>
  </div>
</template>

<script>
import Affix from "@/components/Affix.vue"
import axios from "axios"

import { defineComponent } from "@vue/runtime-core"
import { component } from "v-viewer"

export default defineComponent({
  data() {
      return {
          connectors: [],
          currentConnector: null,

          // Configure Modal
          isConfigureModalActive: false,
          isConfigureModalFileActive: false,

          // Update Modal
          isUpdateModalActive: false,

          loading: false,
          showForm: false,
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
      showDialogUserandPass(connector) {
          this.currentConnector = connector
          this.showForm = true
          //   this.$refs.userAndPassDialog.showModal();
      },

      openConfigureModal(connector) {
          // Open the configure modal and set the initial form values
          this.isConfigureModalActive = true
          this.currentConnector = connector // Store the current connector
          this.connectorForm.connector_url = connector.connector_url
          this.connectorForm.username = connector.connector_username
          this.connectorForm.password = connector.connector_password
          this.connectorForm.connector_api_key = connector.connector_api_key
      },

      openConfigureModalFile(connector) {
          // Open the configure modal and set the initial form values
          this.isConfigureModalFileActive = true
          this.currentConnector = connector // Store the current connector
          this.connectorForm.connector_url = connector.connector_url
          this.connectorForm.username = connector.connector_username
          this.connectorForm.password = connector.connector_password
          this.connectorForm.connector_api_key = connector.connector_api_key
      },

      closeDialogUserandPass() {
          //   this.$refs.userAndPassDialog.close();
          this.showForm = false
          this.isConfigureModalActive = false
      },

      closeConfigureModuleFile() {
          //   this.$refs.userAndPassDialog.close();
          this.showForm = false
          this.isConfigureModalFileActive = false
      },

      openUpdateModal(connector) {
          // Open the update modal and set the initial form values
          this.isUpdateModalActive = true
          this.currentConnector = connector // Store the current connector
          this.connectorForm.connector_url = connector.connector_url
          this.connectorForm.username = connector.connector_username
          this.connectorForm.password = connector.connector_password
          this.connectorForm.connector_api_key = connector.connector_api_key
      },

      closeUpdateModal() {
          //   this.$refs.userAndPassDialog.close();
          this.showForm = false
          this.isUpdateModalActive = false
      },

      configureConnector(event) {
          event.preventDefault()
          const { connector_url, username, password, connector_api_key } = this.connectorForm
          const path = `http://localhost:5000/connectors/${this.currentConnector.id}`
          this.loading = true
          this.closeDialogUserandPass()

          if (connector_api_key) {
              console.log("POST request to: ", path)
              console.log("Data: ", {
                  connector_url: connector_url,
                  connector_api_key: connector_api_key
              })
              axios
                  .post(path, {
                      connector_url: connector_url,
                      connector_api_key: connector_api_key
                  })
                  .then(() => {
                      this.successMessage = "Connector has been successfully configured." // Set success message
                      setTimeout(() => {
                          this.successMessage = "" // Clear success message after 5 seconds
                      }, 5000)
                      this.getConnectors() // Refresh the connectors
                  })
                  .catch(err => {
                      if (err.response.status === 400) {
                          this.errorMessage =
                              "This connector is already configured. If you would like to reconfigure this connector select `Edit`." // Set the error message
                      } else if (err.response.status === 401) {
                          this.errorMessage = "Unauthorized. Please check your endpoint URL, username and password." // Set the error message
                      } else {
                          this.errorMessage =
                              "Error updating the connector. Your settings were not inserted into the keystore. Please try again." // Set the error message
                      }
                      setTimeout(() => {
                          this.errorMessage = "" // Clear error message after 5 seconds
                      }, 5000)
                      this.getConnectors() // Refresh the connectors
                      console.error(err) // Also log the error for debugging
                  })
                  .finally(() => {
                      this.loading = false // Set loading to false
                  })
          } else {
              axios
                  .post(path, {
                      connector_url: connector_url,
                      connector_username: username,
                      connector_password: password
                  })
                  .then(() => {
                      this.successMessage = "Connector has been successfully configured." // Set success message
                      setTimeout(() => {
                          this.successMessage = "" // Clear success message after 5 seconds
                      }, 5000)
                      this.getConnectors() // Refresh the connectors
                  })
                  .catch(err => {
                      if (err.response.status === 400) {
                          this.errorMessage =
                              "This connector is already configured. If you would like to reconfigure this connector select `Edit`." // Set the error message
                      } else if (err.response.status === 401) {
                          this.errorMessage = "Unauthorized. Please check your endpoint URL, username and password." // Set the error message
                      } else {
                          this.errorMessage =
                              "Error updating the connector. Your settings were not inserted into the keystore. Please try again." // Set the error message
                      }
                      setTimeout(() => {
                          this.errorMessage = "" // Clear error message after 5 seconds
                      }, 5000)
                      this.getConnectors() // Refresh the connectors
                      console.error(err) // Also log the error for debugging
                  })
                  .finally(() => {
                      this.loading = false // Set loading to false
                  })
          }
      },

      updateConnector(event) {
          event.preventDefault()
          const { connector_url, username, password, connector_api_key } = this.connectorForm
          const path = `http://localhost:5000/connectors/${this.currentConnector.id}`
          this.loading = true
          this.closeUpdateModal()

          if (connector_api_key) {
              console.log("POST request to: ", path)
              console.log("Data: ", {
                  connector_url: connector_url,
                  connector_api_key: connector_api_key
              })

              axios
                  .put(path, {
                      connector_url: connector_url,
                      connector_username: username,
                      connector_password: password,
                      connector_api_key: connector_api_key
                  })
                  .then(() => {
                      this.successMessage = "Connector has been successfully updated." // Set success message
                      setTimeout(() => {
                          this.successMessage = "" // Clear success message after 5 seconds
                      }, 5000)
                      this.getConnectors() // Refresh the connectors
                  })
                  .catch(err => {
                      if (err.response.status === 400) {
                          this.errorMessage =
                              "This connector is not configured. If you would like to configure this connector select `Configure`." // Set the error message
                      } else if (err.response.status === 401) {
                          this.errorMessage = "Unauthorized. Please check your endpoint URL, username and password." // Set the error message
                      } else {
                          this.errorMessage = "Error updating the connector. Please try again." // Set the error message
                      }
                      setTimeout(() => {
                          this.errorMessage = "" // Clear error message after 5 seconds
                      }, 5000)
                      this.getConnectors() // Refresh the connectors
                      console.error(err) // Also log the error for debugging
                  })
                  .finally(() => {
                      this.loading = false // Set loading to false
                  })
          } else {
              axios
                  .put(path, {
                      connector_url: connector_url,
                      connector_username: username,
                      connector_password: password
                  })
                  .then(() => {
                      this.successMessage = "Connector has been successfully updated." // Set success message
                      setTimeout(() => {
                          this.successMessage = "" // Clear success message after 5 seconds
                      }, 5000)
                      this.getConnectors() // Refresh the connectors
                  })
                  .catch(err => {
                      if (err.response.status === 400) {
                          this.errorMessage =
                              "This connector is not configured. If you would like to configure this connector select `Configure`." // Set the error message
                      } else if (err.response.status === 401) {
                          this.errorMessage = "Unauthorized. Please check your endpoint URL, username and password." // Set the error message
                      } else {
                          this.errorMessage = "Error updating the connector. Please try again." // Set the error message
                      }
                      setTimeout(() => {
                          this.errorMessage = "" // Clear error message after 5 seconds
                      }, 5000)
                      this.getConnectors() // Refresh the connectors
                      console.error(err) // Also log the error for debugging
                  })
                  .finally(() => {
                      this.loading = false // Set loading to false
                  })
          }
      },

      getConnectors() {
          const path = "http://localhost:5000/connectors"
          this.loading = true
          axios
              .get(path)
              .then(res => {
//                 //{
//   "connectors": [
//     {
//       "connectionSuccessful": true,
//       "connector_api_key": "N/A",
//       "connector_last_updated": "Fri, 02 Jun 2023 02:19:13 GMT",
//       "connector_name": "Wazuh-Indexer",
//       "connector_password": "hmx7KPy15XPhJkgjlFrVgrWZ+Aid6QNm",
//       "connector_type": "4.4.1",
//       "connector_url": "https://ashwix01.socfortress.local:9200",
//       "connector_username": "admin",
//       "id": 11,
//       "name": "Wazuh-Indexer"
//     },
//     {
//       "authToken": "eyJhbGciOiJFUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJ3YXp1aCIsImF1ZCI6IldhenVoIEFQSSBSRVNUIiwibmJmIjoxNjkwNDc2MDMzLCJleHAiOjE2OTA0NzY5MzMsInN1YiI6IndhenVoLXd1aSIsInJ1bl9hcyI6ZmFsc2UsInJiYWNfcm9sZXMiOlsxXSwicmJhY19tb2RlIjoid2hpdGUifQ.ANXrdgNlJaQW_dTq4vq-RRE9B1ck9_12bXWI73yVZOCSmrv5DfDmc-e2XkVo5kcl3tcvJ8_AjFa6GNCnpZb0owQtAMQkNQQZAYysbJxbf5BDn1CNVn5kr1Cmam4rpDKVBC8e2yEW2GQ-_uTaFJyNunXrFvVjtIFCCk1nJFYBahsIImlL",
//       "connectionSuccessful": true,
//       "connector_api_key": "N/A",
//       "connector_last_updated": "Fri, 02 Jun 2023 02:21:49 GMT",
//       "connector_name": "Wazuh-Manager",
//       "connector_password": "wazuh-wui",
//       "connector_type": "4.4.1",
//       "connector_url": "https://ashwzhma.socfortress.local:55000",
//       "connector_username": "wazuh-wui",
//       "id": 14,
//       "name": "Wazuh-Manager"
//     },
//     {
//       "connectionSuccessful": true,
//       "connector_api_key": "N/A",
//       "connector_last_updated": "Fri, 02 Jun 2023 02:20:17 GMT",
//       "connector_name": "Graylog",
//       "connector_password": "R{2PvE5TQkU7[xS$pX>fw>`y",
//       "connector_type": "5.0.7",
//       "connector_url": "http://ashgrl02.socfortress.local:9000",
//       "connector_username": "socfortress_graylog_manager",
//       "id": 13,
//       "name": "Graylog"
//     },
//     {
//       "connectionSuccessful": true,
//       "connector_api_key": "bc5d1e18-6230-40f0-b032-6ed898c307c5",
//       "connector_last_updated": "Fri, 02 Jun 2023 13:11:00 GMT",
//       "connector_name": "Shuffle",
//       "connector_password": "string",
//       "connector_type": "1.1.0",
//       "connector_url": "https://ASHDKR02.socfortress.local:3443",
//       "connector_username": "sting",
//       "id": 30,
//       "name": "Shuffle"
//     },
//     {
//       "connectionSuccessful": true,
//       "connector_api_key": "I3Hwvkpvdk8Z0XRFlyGm4WXGw8jksnEzvKNoD9BobtSQ2AgWmdo_p-pfmJCg_ev2cm8I-zgWzAfya3jLBWZ6qw",
//       "connector_last_updated": "Fri, 02 Jun 2023 02:19:36 GMT",
//       "connector_name": "DFIR-IRIS",
//       "connector_password": "N/A",
//       "connector_type": "2.0",
//       "connector_url": "https://ashirs01.socfortress.local",
//       "connector_username": "N/A",
//       "id": 12,
//       "name": "DFIR-IRIS"
//     },
//     {
//       "connectionSuccessful": true,
//       "connector_api_key": "C:\\\\Users\\\\walto\\\\Desktop\\\\copilot_uploads\\\\api.config.yaml",
//       "connector_last_updated": "Fri, 02 Jun 2023 16:14:55 GMT",
//       "connector_name": "Velociraptor",
//       "connector_password": "N/A",
//       "connector_type": "0.6.8",
//       "connector_url": "https://ashvlo01.socfortress.local:8001",
//       "connector_username": "N/A",
//       "id": 57,
//       "name": "Velociraptor"
//     },
//     {
//       "connectionSuccessful": true,
//       "connector_api_key": "N/A",
//       "connector_last_updated": "Tue, 06 Jun 2023 18:06:42 GMT",
//       "connector_name": "RabbitMQ",
//       "connector_password": "guest",
//       "connector_type": "3",
//       "connector_url": "ashdkr02.socfortress.local:5672",
//       "connector_username": "guest",
//       "id": 58,
//       "name": "RabbitMQ"
//     },
//     {
//       "connectionSuccessful": true,
//       "connector_api_key": "7653trxhakxn4wxdh8bbatbvu97hm8fopos7wztzjrwfd12gf5i2kyebhvke9rt4",
//       "connector_last_updated": "Tue, 06 Jun 2023 18:06:42 GMT",
//       "connector_name": "Sublime",
//       "connector_password": "N/A",
//       "connector_type": "3",
//       "connector_url": "http://ashdkr02.socfortress.local:8000",
//       "connector_username": "N/A",
//       "id": 59,
//       "name": "Sublime"
//     },
//     {
//       "connectionSuccessful": false,
//       "connector_api_key": "gOLoFKucQXXd5d1rDx59YYktIz6OfrHIe4jRowJKZ8iB4IcZES8rOhRPaDEejEkahch8Ze2FiMzZxbQ9ZV8K6g==",
//       "connector_last_updated": "Tue, 06 Jun 2023 18:06:42 GMT",
//       "connector_name": "InfluxDB",
//       "connector_password": "N/A",
//       "connector_type": "3",
//       "connector_url": "http://ashdkr02.socfortress.local:8086",
//       "connector_username": "SOCFortress",
//       "id": 60,
//       "name": "InfluxDB",
//       "response": null
//     },
//     {
//       "connectionSuccessful": false,
//       "connector_api_key": "CkKmw1B9NM1hG669tC4sTazLm1HlRfSXVvMZkxa",
//       "connector_last_updated": "Tue, 06 Jun 2023 18:06:42 GMT",
//       "connector_name": "AskSocfortress",
//       "connector_password": "N/A",
//       "connector_type": "3",
//       "connector_url": "https://api.socfortress.co/rule",
//       "connector_username": "N/A",
//       "id": 61,
//       "name": "AskSocfortress",
//       "response": null
//     },
//     {
//       "connectionSuccessful": true,
//       "connector_api_key": "ozH1jHp1zmacCePYrAZmxarJCGptcMth93a86Jq8",
//       "connector_last_updated": "Tue, 06 Jun 2023 18:06:42 GMT",
//       "connector_name": "SocfortressThreatIntel",
//       "connector_password": "N/A",
//       "connector_type": "3",
//       "connector_url": "https://intel.socfortress.co/search",
//       "connector_username": "N/A",
//       "id": 62,
//       "name": "SocfortressThreatIntel"
//     }
//   ],
//   "message": "All available connectors",
//   "success": true
// }

                  this.connectors = res.data.connectors
              })
              .catch(err => {
                  console.error(err)
              })
              .finally(() => {
                  this.loading = false
              })
      },

      resetForm(formName) {
          this.$refs[formName].resetFields()
      }
  },
  created() {
      this.getConnectors()
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

.modal-window {
  position: fixed;
  background-color: rgba(255, 255, 255, 0.25);
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 999;
  visibility: hidden;
  opacity: 0;
  pointer-events: none;
  transition: all 0.3s;
  &.is-active {
      visibility: visible;
      opacity: 1;
      pointer-events: auto;
  }
  &:target {
      visibility: visible;
      opacity: 1;
      pointer-events: auto;
  }
  & > div {
      width: 400px;
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      padding: 2em;
      background: white;
  }
  header {
      font-weight: bold;
  }
  h1 {
      font-size: 150%;
      margin: 0 0 15px;
  }
}

.modal-close {
  color: #aaa;
  line-height: 50px;
  font-size: 80%;
  position: absolute;
  right: 0;
  text-align: center;
  top: 0;
  width: 70px;
  text-decoration: none;
  &:hover {
      color: black;
  }
}

/* Demo Styles */

html,
body {
  height: 100%;
}

html {
  font-size: 18px;
  line-height: 1.4;
}

body {
  font-family: apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue",
      sans-serif;
  font-weight: 600;
  background-image: linear-gradient(to right, #7f53ac 0, #657ced 100%);
  color: black;
}

a {
  color: inherit;
  text-decoration: none;
}

.container {
  display: grid;
  justify-content: center;
  align-items: center;
  height: 100vh;
}

.modal-window {
  & > div {
      border-radius: 1rem;
  }
}

.modal-window div:not(:last-of-type) {
  margin-bottom: 15px;
}

.logo {
  max-width: 150px;
  display: block;
}

small {
  color: lightgray;
}

.btn {
  background-color: white;
  padding: 1em 1.5em;
  border-radius: 0.5rem;
  text-decoration: none;
  i {
      padding-right: 0.3em;
  }
}

.modal-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-logo {
  height: auto; /* adjust as needed */
  width: auto; /* adjust as needed */
}
</style>
