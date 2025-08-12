# Management API Documentation

**Version**: 2.1 (Granular Permissions)

This document provides details on the API endpoints relevant for Management and Super Admin users.

---

## API Access Details

To connect your frontend application to this backend, you will need the following:

1.  **Live Backend URL (Your API Endpoint):**
    *   This is the base URL where your backend API is deployed.
    *   **Please replace `YOUR_LIVE_BACKEND_URL_HERE` with your actual deployed backend URL.**
    *   Example: `https://api.yourdomain.com`
    ```
    YOUR_LIVE_BACKEND_URL_HERE
    ```

2.  **Supabase Anon Key (For Authentication):**
    *   This key is required to initialize the Supabase client in your frontend for user authentication (login, register).
    *   You can find this in your Supabase project settings.
    *   **Please replace `YOUR_SUPABASE_ANON_KEY_HERE` with your actual Supabase Anon Key.**
    ```
    YOUR_SUPABASE_ANON_KEY_HERE
    ```

---

## Authentication & Permissions

All protected requests must include an `Authorization` header with a JWT from Supabase:
`Authorization: Bearer <your_supabase_jwt>`

Access to specific API endpoints is now controlled by granular permissions. A user must possess the required permission to access a protected endpoint.

This documentation focuses on the **Manager** and **Super Admin** roles and the permissions typically associated with them. For Client-specific APIs, please refer to the `client_api_documentation.md`.

---

## Management API Endpoints (`/api/management`)

### User & Role Management

- **Endpoint**: `GET /users`
- **Required Permission**: `can_view_users`
- **Description**: Retrieves a list of all users.

- **Endpoint**: `POST /users/<int:user_id>/assign-role`
- **Required Permission**: `can_manage_user_roles`
- **Description**: Assigns a role to a user.
- **Request Body (JSON)**:
  ```json
  {
    "role": "Manager" // or "Client", "Super Admin"
  }
  ```

- **Endpoint**: `GET /users/<int:user_id>/permissions`
- **Required Permission**: `can_manage_user_permissions`
- **Description**: Retrieves explicit permissions assigned to a specific user.

- **Endpoint**: `POST /users/<int:user_id>/permissions`
- **Required Permission**: `can_manage_user_permissions`
- **Description**: Assigns or revokes individual permissions for a specific user. Overwrites existing explicit permissions.
- **Request Body (JSON)**:
  ```json
  [
    { "name": "can_view_users", "has_permission": true },
    { "name": "can_delete_popups", "has_permission": false } // Revoke
  ]
  ```

### Popup Management

- **Endpoint**: `GET /popups`
- **Required Permission**: `can_view_popups`
- **Description**: Retrieves all popups.

- **Endpoint**: `POST /popups`
- **Required Permission**: `can_create_popups`
- **Description**: Creates a new popup.

- **Endpoint**: `PATCH /popups/<int:popup_id>`
- **Required Permission**: `can_update_popups`
- **Description**: Updates an existing popup.

- **Endpoint**: `DELETE /popups/<int:popup_id>`
- **Required Permission**: `can_delete_popups`
- **Description**: Deletes a popup.

### App Settings & Notifications

- **Endpoint**: `GET /app-settings`
- **Required Permission**: `can_view_app_settings`
- **Description**: Retrieves global application settings.

- **Endpoint**: `PATCH /app-settings`
- **Required Permission**: `can_manage_app_settings`
- **Description**: Updates global application settings.

- **Endpoint**: `POST /notifications/send`
- **Required Permission**: `can_send_notifications`
- **Description**: Sends a (mock) push notification.

### Permission Management (Super Admin Only)

- **Endpoint**: `GET /permissions`
- **Required Permission**: `can_manage_user_permissions`
- **Description**: Lists all available permissions in the system.

- **Endpoint**: `GET /roles/<string:role_name>/permissions`
- **Required Permission**: `can_manage_user_permissions`
- **Description**: Gets all permissions assigned to a specific role (default permissions).

- **Endpoint**: `POST /roles/<string:role_name>/permissions`
- **Required Permission**: `can_manage_user_permissions`
- **Description**: Assigns a list of permissions to a specific role. Overwrites existing role permissions.
- **Request Body (JSON)**:
  ```json
  [
    "can_view_users",
    "can_create_popups"
  ]
  ```