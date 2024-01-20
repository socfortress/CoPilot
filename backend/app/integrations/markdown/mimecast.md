# [Mimecast](https://integrations.mimecast.com/documentation/api-overview/authentication-scripts-server-apps/)

When developing a script of server application integration you will:

- Use a single user that has the Mimecast administrator permissions to perform the actions required by your use case.
- Update the Authentication Cache TTL setting in the service user's effective Authentication Profile to "Never Expire."

This page provides a step-by-step guide to prepare a user for your integration and get the access key and secret key values required to authorize all requests to the API.

### Step 1: Create a New User
1. Login to the Administration Console.
2. Navigate to the Administration | Directories | Internal Directories menu item to display a list of internal domains.
3. Select the internal domain where you would like to create your new user.
4. Select the New Address button from the menu bar.
5. Complete the new address form and select Save and Exit to create the new user.
6. Keep a note of the password set as you will use this to get your Authentication Token in Step 6.

### Step 2: Add the User to an Administrative Role
1. While logged into the Administration Console, navigate to the Administration | Account | Roles menu item to display the Roles page.
2. Right-click the Basic Administrator role and select Add users to role.
3. Browse or search to find the new user created in Step 1.
4. Select the tick box to the left of the user.
5. Select the Add selected users button to add the user to the role.

### Step 3: Create a New Group and Add Your New User
1. While logged into the Administration Console, navigate to the Administration | Directories | Profile Groups menu item to display the Profile groups page.
2. Create a new group by selecting the plus icon on the parent folder where you would like to create the group. This creates a new group with the Name "New Folder"
3. To rename the group, select the newly created "New Folder" group. Then from the Edit group text box type the name you want to give the folder, for example, Splunk Admin and press the Enter key to apply the change.
4. With the group selected select the Build drop-down button and select Add Email Addresses.
5. Type the name of the new user created in Step 1.
6. Select Save and Exit to add the new user to the group.

### Step 4: Create a New Authentication Profile
1. While logged into the Administration Console, navigate to the Administration | Services | Applications menu item to display the Application Settings page.
2. Select the Authentication Profiles button.
3. Select the New Authentication Profile button.
4. Type a Description for the new profile.
5. Set the Authentication TTL setting to Never Expires. This will make sure that when you create your Authentication Token it will not expire and impact the data collection of the app.
6. Leave all other settings as their default.
7. Select Save and Exit to create the profile.

### Step 5: Create a New Application Setting
1. While logged into the Administration Console, navigate to the Administration | Services | Applications menu item to display the Application Settings page.
2. Select the New Application Settings button.
3. Type a Description.
4. Use the Group Lookup button to select the Group that you created in Step 3.
5. Use the Authentication Profile Lookup button to select the Authentication Profile created in Step 4.
6. Leave all other settings as their default.
7. Select Save and Exit to create and apply the Application Settings to your new group and user.

### Step 6: Get Your Authentication Token
Now that you have a dedicated user who will receive an Authentication Token that will never expire, the final preparation task is to get the Authentication Token for the user.

#### Get an Authentication Token Using Windows
NOTE: This process has been tested in Powershell version 4 and 5.

Copy paste the following script into a Powershell window:
```powershell
$appId = Read-Host -Prompt 'Input your registered application id'

$creds = Get-Credential

$discoverPostBody = @{"data" = ,@{"emailAddress" = $creds.UserName}}

$discoverPostBodyJson = ConvertTo-Json $discoverPostBody

$discoverRequestId = [GUID]::NewGuid().guid

$discoverRequestHeaders = @{"x-mc-app-id" = $appId; "x-mc-req-id" = $discoverRequestId; "Content-Type" = "application/json"}

$discoveryData = Invoke-RestMethod -Method Post -Headers $discoverRequestHeaders -Body $discoverPostBodyJson -Uri "https://api.mimecast.com/api/login/discover-authentication"

$baseUrl = $discoveryData.data.region.api

$keys = @{}

$uri = $baseUrl + "/api/login/login"

$requestId = [GUID]::NewGuid()

$netCred = $creds.GetNetworkCredential()

$PlainPassword = $netCred.Password

$credsBytes = [System.Text.Encoding]::ASCII.GetBytes($creds.UserName + ":" + $PlainPassword)

$creds64 = [System.Convert]::ToBase64String($credsBytes)

$headers = @{"Authorization" = "Basic-Cloud " + $creds64; "x-mc-app-id" = $appId; "x-mc-req-id" = $requestId; "Content-Type" = "application/json"}

$postBody = @{"data" = ,@{"username" = $creds.UserName}}

$postBodyJson = ConvertTo-Json $postBody

$data = Invoke-RestMethod -Method Post -Headers $headers -Body $postBodyJson -Uri $uri

"Meta: " + $data.meta

"Access key: " + $data.data.accessKey

"Secret key: " + $data.data.secretKey

"Fail: " + $data.fail.errorss
```

When prompted, enter the Application ID value received when you registered your application.

Enter the email address and password of the user created in Step 1: Create a new user into the Windows credentials box that will launch after you have pasted the script into the Powershell window.

Copy and paste the accessKey and secretKey values printed at the bottom of the Powershell window to use in your application.

IMPORTANT: be sure to copy and paste these values to a text editor and remove any line breaks caused by your Powershell window size before using the values.
