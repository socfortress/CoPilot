Documentation provided by [Wazuh](https://documentation.wazuh.com/current/cloud-security/office365/monitoring-office365-activity.html).

Learn how to monitor your organization's Office 365 activity with Wazuh in this section of our documentation.

# Monitoring Office 365 Activity

The `audit log` allows organization admins to quickly review the actions performed by members of your organization. It includes details such as who performed the action, what the action was, and when it was performed.
This Wazuh module allows you to collect all the logs from Office 365 using its API. The Office 365 Management Activity API aggregates actions and events into tenant-specific content blobs, which are classified by the type and source of the content they contain.

**List available content:**

This operation lists the content currently available for retrieval for the specified content type.

    GET https://manage.office.com/api/v1.0/{tenant_id}/activity/feed/subscriptions/content?contentType={content_type}&startTime={start_time}&endTime={end_time}

**Retrieving content:**

To retrieve a content blob, make a GET request against the corresponding content URI that is included in the list of available content.

    GET {content_uri}

Office 365 API description can be found in this `link <https://docs.microsoft.com/en-us/office/office-365-management-api/office-365-management-activity-api-reference>`\_.

### Office 365 API requirements

For **Wazuh** to successfully connect to the **Office365 API**, an authentication process is required. To do this, we must provide the `tenant_id`, `client_id`, and `client_secret` of the application that we authorize in the organization.

# Register your app

To authenticate with the Microsoft identity platform endpoint, you need to register an app in your [Microsoft Azure portal app registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade) section. Once there click on **New registration**:

![Register your app](/images/office365/0-azure-app-new-registration.png)

Fill in the name of your app, choose the desired account type and click on the **Register** button:

![Register your app](/images/office365/1-azure-wazuh-app-register-application.png)

The app is now registered, and you can see information about it in its **Overview** section, at this point we can get the `client` and `tenant` IDs:

![Register your app](/images/office365/2-azure-wazuh-app-overview.png)

# Certificates & secrets

You can generate a password to use during the authentication process. Go to **Certificates & secrets** and click on **New client secret**,
then the name and the expiration date of the **New client secret** are requested:

![Certificates & secrets](/images/office365/3-azure-wazuh-app-create-password.png)

Copy and save the value section.

![Certificates & secrets](/images/office365/3-azure-wazuh-app-create-password-copy-value.png)

Make sure you write it down because the UI won’t let you copy it afterward.

# API permissions

The application needs specific API permissions to be able to request the Office 365 activity events. In this case, you are looking for permissions related to the `https://manage.office.com` resource.

To configure the application permissions, go to the **API permissions** page and choose **Add a permission**. Select the **Office 365 Management APIs** and click on **Application permissions**.

You need to add the following permissions under the **ActivityFeed** group:

-   `ActivityFeed.Read`. Read activity data for your organization.

-   `ActivityFeed.ReadDlp`. Read DLP policy events including detected sensitive data.

![API permissions](/images/office365/4-azure-wazuh-app-configure-permissions.png)

Admin consent is required for API permission changes.

![API permissions](/images/office365/4-azure-wazuh-app-configure-permissions-admin-consent.png)

### CoPilot configuration

Next, we will see how to deploy this module in CoPilot. To do so, we will need to navigate to the `Customers` section and select the customer we want to deploy the module to. Once there, we will click on the `Integrations` tab and then on the `Add integration` button. We will select the `Office365` module and fill in the required fields.

![Copilot Configuration](/images/office365/copilot_config_customer_details.PNG)

![Copilot Configuration](/images/office365/copilot_config_customer_integration.PNG)

![Copilot Configuration](/images/office365/copilot_config_customer_integration_config.PNG)

![Copilot Configuration](/images/office365/copilot_config_customer_integration_auth.PNG)

Once deployed, Copilot will automatically add the required configuration to the `Wazuh manager`, deploy the required Index, Stream, and Pipeline to `Graylog` and create the required Dashboards within `Grafana`. `Praeco` will also be configured to send `Exchange` and `Threat Intel` Office365 alerts to `DFIR-IRIS`.

### Generate activity on Office 365

For this example, we will start by generating some activity in our Office 365 Organization. In this case, let's modify a `Communication site` in `SharePoint`. If we do that, we can see that Office 365 will generate a new json event, something like this:

```json
{
	"CreationTime": "2021-06-09T22:10:45",
	"Id": "xxxx-xxxx-xxxx-xxxx-xxxx",
	"Operation": "FileModified",
	"OrganizationId": "xxxx-xxxx-xxxx-xxxx-xxxx",
	"RecordType": "6",
	"UserKey": "i:xx.f|membership|xxxx@live.com",
	"UserType": "0",
	"Version": "1",
	"Workload": "SharePoint",
	"ClientIP": "xxx.xx.x.xxx",
	"ObjectId": "https://xxxx.sharepoint.com/SitePages/xxxx.aspx",
	"UserId": "xxx.xxx@xxx.com",
	"CorrelationId": "0b50d09f-e0f2-2000-d9c7-a5b468efc712",
	"DoNotDistributeEvent": "true",
	"EventSource": "SharePoint",
	"ItemType": "File",
	"ListId": "xxxx-xxxx-xxxx-xxxx-xxxx",
	"ListItemUniqueId": "xxxx-xxxx-xxxx-xxxx-xxxx",
	"Site": "xxxx-xxxx-xxxx-xxxx-xxxx",
	"UserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
	"WebId": "xxxx-xxxx-xxxx-xxxx-xxxx",
	"SourceFileExtension": "aspx",
	"SiteUrl": "https://xxxx.sharepoint.com/",
	"SourceFileName": "xxxx.aspx",
	"SourceRelativeUrl": "SitePages"
}
```

### Wazuh Rules

Wazuh provides a series of rules to catch different events on Office365, for this example we will take the rule id `91537` which detects a `Office 365: SharePoint file operation events.` action.

```html
<rule id="91537" level="3">
	<if_sid>91532</if_sid>
	<field name="office365.RecordType" type="osregex">^6$</field>
	<description>Office 365: SharePoint file operation events.</description>
	<options>no_full_log</options>
	<group>SharePointFileOperation</group>
</rule>
```

If Wazuh successfully connects to Office 365 API, the events raised above will trigger these rules and cause an alert like this:

```json
{
	"timestamp": "2021-06-09T22:12:54.301+0000",
	"rule": {
		"level": 3,
		"description": "Office 365: SharePoint file operation events.",
		"id": "91537",
		"firedtimes": 2,
		"mail": false,
		"groups": ["office365", "SharePointFileOperation"]
	},
	"agent": {
		"id": "001",
		"name": "ubuntu-bionic"
	},
	"manager": {
		"name": "ubuntu-bionic"
	},
	"id": "1623276774.47272",
	"decoder": {
		"name": "json"
	},
	"data": {
		"integration": "office365",
		"office365": {
			"CreationTime": "2021-06-09T22:10:45",
			"Id": "xxxx-xxxx-xxxx-xxxx-xxxx",
			"Operation": "FileModified",
			"OrganizationId": "xxxx-xxxx-xxxx-xxxx-xxxx",
			"RecordType": "6",
			"UserKey": "i:xx.f|membership|xxxx@live.com",
			"UserType": "0",
			"Version": "1",
			"Workload": "SharePoint",
			"ClientIP": "xxx.xx.x.xxx",
			"ObjectId": "https://xxxx.sharepoint.com/SitePages/xxxx.aspx",
			"UserId": "xxx.xxx@xxx.com",
			"CorrelationId": "0b50d09f-e0f2-2000-d9c7-a5b468efc712",
			"DoNotDistributeEvent": "true",
			"EventSource": "SharePoint",
			"ItemType": "File",
			"ListId": "xxxx-xxxx-xxxx-xxxx-xxxx",
			"ListItemUniqueId": "xxxx-xxxx-xxxx-xxxx-xxxx",
			"Site": "xxxx-xxxx-xxxx-xxxx-xxxx",
			"UserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
			"WebId": "xxxx-xxxx-xxxx-xxxx-xxxx",
			"SourceFileExtension": "aspx",
			"SiteUrl": "https://xxxx.sharepoint.com/",
			"SourceFileName": "xxxx.aspx",
			"SourceRelativeUrl": "SitePages",
			"Subscription": "Audit.SharePoint"
		}
	},
	"location": "office365"
}
```

For further information, please refer to the [Modules](https://documentation.wazuh.com/current/user-manual/wazuh-dashboard/settings.html#modules)
