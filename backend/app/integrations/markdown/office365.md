.. Copyright (C) 2015, Wazuh, Inc.

.. meta::
  :description: Learn how to monitor your organization's Office 365 activity with Wazuh in this section of our documentation.

.. _office365_monitoring_activity:

Monitoring Office 365 Activity
==============================

The `audit log` allows organization admins to quickly review the actions performed by members of your organization. It includes details such as who performed the action, what the action was, and when it was performed.
This Wazuh module allows you to collect all the logs from Office 365 using its API. The Office 365 Management Activity API aggregates actions and events into tenant-specific content blobs, which are classified by the type and source of the content they contain.

**List available content:**

This operation lists the content currently available for retrieval for the specified content type.

.. code-block:: none

    GET https://manage.office.com/api/v1.0/{tenant_id}/activity/feed/subscriptions/content?contentType={content_type}&startTime={start_time}&endTime={end_time}

**Retrieving content:**

To retrieve a content blob, make a GET request against the corresponding content URI that is included in the list of available content.

.. code-block:: xml

    GET {content_uri}

Office 365 API description can be found in this `link <https://docs.microsoft.com/en-us/office/office-365-management-api/office-365-management-activity-api-reference>`_.

Office 365 API requirements
^^^^^^^^^^^^^^^^^^^^^^^^^^^

For **Wazuh** to successfully connect to the **Office365 API**, an authentication process is required. To do this, we must provide the ``tenant_id``, ``client_id``, and ``client_secret`` of the application that we authorize in the organization.

#. Register your app

   To authenticate with the Microsoft identity platform endpoint, you need to register an app in your `Microsoft Azure portal app registrations <https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade>`_  section. Once there click on **New registration**:

   .. thumbnail:: /images/cloud-security/office365/0-azure-app-new-registration.png
       :title: Register your app
       :align: center
       :width: 100%

   Fill in the name of your app, choose the desired account type and click on the **Register** button:

   .. thumbnail:: /images/cloud-security/office365/1-azure-wazuh-app-register-application.png
       :title: Register your app
       :align: center
       :width: 100%

   The app is now registered, and you can see information about it in its **Overview** section, at this point we can get the ``client`` and ``tenant`` IDs:

   .. thumbnail:: /images/cloud-security/office365/2-azure-wazuh-app-overview.png
       :title: Register your app
       :align: center
       :width: 100%

#. Certificates & secrets

   You can generate a password to use during the authentication process. Go to **Certificates & secrets** and click on **New client secret**,
   then the name and the expiration date of the **New client secret** are requested:

   .. thumbnail:: /images/cloud-security/office365/3-azure-wazuh-app-create-password.png
       :title: Certificates & secrets
       :align: center
       :width: 100%

   Copy and save the value section.

   .. thumbnail:: /images/cloud-security/office365/3-azure-wazuh-app-create-password-copy-value.png
       :title: Copy secrets value
       :align: center
       :width: 100%

   .. note:: Make sure you write it down because the UI won’t let you copy it afterward.

#. API permissions

   The application needs specific API permissions to be able to request the Office 365 activity events. In this case, you are looking for permissions related to the ``https://manage.office.com`` resource.

   To configure the application permissions, go to the **API permissions** page and choose **Add a permission**. Select the **Office 365 Management APIs** and click on **Application permissions**.

   You need to add the following permissions under the **ActivityFeed** group:

   - ``ActivityFeed.Read``. Read activity data for your organization.

   - ``ActivityFeed.ReadDlp``. Read DLP policy events including detected sensitive data.

   .. thumbnail:: /images/cloud-security/office365/4-azure-wazuh-app-configure-permissions.png
       :title: API permissions
       :align: center
       :width: 100%

   .. note:: Admin consent is required for API permission changes.

   .. thumbnail:: /images/cloud-security/office365/4-azure-wazuh-app-configure-permissions-admin-consent.png
       :title: API permissions admin consent
       :align: center
       :width: 100%


Wazuh configuration
^^^^^^^^^^^^^^^^^^^

Next, we will see the options we have to configure for the Wazuh integration.

Configure the ``office365`` module either in the Wazuh manager or the Wazuh agent.  To do so, modify the :doc:`ossec.conf </user-manual/reference/ossec-conf/index>` configuration file. Through the following configuration, Wazuh is ready to search for logs created by Office 365 audit-log. In this case, we will only search for the ``Audit.SharePoint`` type events within an interval of ``1m``. Those logs will be only those that were created after the module was started:

.. code-block:: xml

    <office365>
        <enabled>yes</enabled>
        <interval>1m</interval>
        <curl_max_size>1M</curl_max_size>
        <only_future_events>yes</only_future_events>
        <api_auth>
            <tenant_id>your_tenant_id</tenant_id>
            <client_id>your_client_id</client_id>
            <client_secret>your_client_secret</client_secret>
            <api_type>commercial</api_type>
        </api_auth>
        <subscriptions>
            <subscription>Audit.SharePoint</subscription>
        </subscriptions>
    </office365>

To learn more, check the :ref:`office365-module` module reference.

Using the configuration mentioned above, we will see an example of monitoring Office 365 activity.

Generate activity on Office 365
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For this example, we will start by generating some activity in our Office 365 Organization. In this case, let's modify a ``Communication site`` in ``SharePoint``. If we do that, we can see that Office 365 will generate a new json event, something like this:

.. code-block:: json
    :class: output

    {
        "CreationTime":"2021-06-09T22:10:45",
        "Id":"xxxx-xxxx-xxxx-xxxx-xxxx",
        "Operation":"FileModified",
        "OrganizationId":"xxxx-xxxx-xxxx-xxxx-xxxx",
        "RecordType":"6",
        "UserKey":"i:xx.f|membership|xxxx@live.com",
        "UserType":"0",
        "Version":"1",
        "Workload":"SharePoint",
        "ClientIP":"xxx.xx.x.xxx",
        "ObjectId":"https://xxxx.sharepoint.com/SitePages/xxxx.aspx",
        "UserId":"xxx.xxx@xxx.com",
        "CorrelationId":"0b50d09f-e0f2-2000-d9c7-a5b468efc712",
        "DoNotDistributeEvent":"true",
        "EventSource":"SharePoint",
        "ItemType":"File",
        "ListId":"xxxx-xxxx-xxxx-xxxx-xxxx",
        "ListItemUniqueId":"xxxx-xxxx-xxxx-xxxx-xxxx",
        "Site":"xxxx-xxxx-xxxx-xxxx-xxxx",
        "UserAgent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
        "WebId":"xxxx-xxxx-xxxx-xxxx-xxxx",
        "SourceFileExtension":"aspx",
        "SiteUrl":"https://xxxx.sharepoint.com/",
        "SourceFileName":"xxxx.aspx",
        "SourceRelativeUrl":"SitePages"
    }

Wazuh Rules
^^^^^^^^^^^

Wazuh provides a series of rules to catch different events on Office365, for this example we will take the rule id ``91537`` which detects a ``Office 365: SharePoint file operation events.`` action.

.. code-block:: xml

    <rule id="91537" level="3">
        <if_sid>91532</if_sid>
        <field name="office365.RecordType" type="osregex">^6$</field>
        <description>Office 365: SharePoint file operation events.</description>
        <options>no_full_log</options>
        <group>SharePointFileOperation</group>
    </rule>

If Wazuh successfully connects to Office 365 API, the events raised above will trigger these rules and cause an alert like this:

.. code-block:: json
    :emphasize-lines: 5
    :class: output

    {
        "timestamp":"2021-06-09T22:12:54.301+0000",
        "rule":{
            "level":3,
            "description":"Office 365: SharePoint file operation events.",
            "id":"91537",
            "firedtimes":2,
            "mail":false,
            "groups":["office365","SharePointFileOperation"]
        },
        "agent":{
            "id":"001",
            "name":"ubuntu-bionic"
        },
        "manager":{
            "name":"ubuntu-bionic"
        },
        "id":"1623276774.47272",
        "decoder":{
            "name":"json"
        },
        "data":{
            "integration":"office365",
            "office365":{
                "CreationTime":"2021-06-09T22:10:45",
                "Id":"xxxx-xxxx-xxxx-xxxx-xxxx",
                "Operation":"FileModified",
                "OrganizationId":"xxxx-xxxx-xxxx-xxxx-xxxx",
                "RecordType":"6",
                "UserKey":"i:xx.f|membership|xxxx@live.com",
                "UserType":"0",
                "Version":"1",
                "Workload":"SharePoint",
                "ClientIP":"xxx.xx.x.xxx",
                "ObjectId":"https://xxxx.sharepoint.com/SitePages/xxxx.aspx",
                "UserId":"xxx.xxx@xxx.com",
                "CorrelationId":"0b50d09f-e0f2-2000-d9c7-a5b468efc712",
                "DoNotDistributeEvent":"true",
                "EventSource":"SharePoint",
                "ItemType":"File",
                "ListId":"xxxx-xxxx-xxxx-xxxx-xxxx",
                "ListItemUniqueId":"xxxx-xxxx-xxxx-xxxx-xxxx",
                "Site":"xxxx-xxxx-xxxx-xxxx-xxxx",
                "UserAgent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
                "WebId":"xxxx-xxxx-xxxx-xxxx-xxxx",
                "SourceFileExtension":"aspx",
                "SiteUrl":"https://xxxx.sharepoint.com/",
                "SourceFileName":"xxxx.aspx",
                "SourceRelativeUrl":"SitePages",
                "Subscription":"Audit.SharePoint"
            }
        },
        "location":"office365"
    }


Enabling dashboard visualization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once the configuration is complete, you can activate the corresponding Security Information Management module on the Wazuh Dashboard. This module provides additional details and insights about events, as shown in the screenshots below.

    .. thumbnail:: /images/office365/office365-dashboard.png
       :title: Office 365 dashboard
       :alt: Office 365 dashboard
       :align: center
       :width: 80%

    .. thumbnail:: /images/office365/office365-events.png
       :title: Office 365 events
       :alt: Office 365 events
       :align: center
       :width: 80%

To activate the **Office 365** module, navigate to your Wazuh Dashboard and click on **Wazuh > Settings > Modules**. In the **Security Information Management** section, enable the **Office 365** module as shown in the image below.

    .. thumbnail:: /images/office365/office365-module.png
       :title: Office 365 module
       :alt: Office 365 module
       :align: center
       :width: 80%

For further information, please refer to the `modules <https://documentation.wazuh.com/current/user-manual/wazuh-dashboard/settings.html#modules>`_ section.
