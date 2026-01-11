import logging
import uuid
from typing import cast

import flet as ft

from src.ui.context import ServiceContext
from src.ui.state import AppState

logger = logging.getLogger(__name__)

def UserListView(page: ft.Page, ctx: ServiceContext, state: AppState) -> ft.View:
    # 1. Check Permissions
    if not state.current_user or not ctx.policy.can_manage_users(state.current_user):
        page.go("/dashboard")
        return ft.View()

    # 2. Load Data
    try:
        users = ctx.auth_service.list_users(state.current_user)
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
        users = []

    # 3. Build Table
    def edit_user(e: ft.ControlEvent) -> None:
        uid = e.control.data
        page.go(f"/admin/users/{uid}")

    columns = [
        ft.DataColumn(ft.Text("Display Name")),
        ft.DataColumn(ft.Text("Email")),
        ft.DataColumn(ft.Text("Roles")),
        ft.DataColumn(ft.Text("Status")),
        ft.DataColumn(ft.Text("Actions")),
    ]

    rows = []
    for u in users:
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(u.display_name)),
                    ft.DataCell(ft.Text(u.email)),
                    ft.DataCell(ft.Text(", ".join(u.roles))),
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text(u.status),
                            bgcolor=
                                "greenAccent" 
                                if u.status == "active" else 
                                "redAccent",
                            padding=5,
                            border_radius=5
                        )
                    ),
                    ft.DataCell(
                        ft.IconButton(
                            icon=ft.Icons.EDIT,
                            data=str(u.id),
                            on_click=edit_user
                        )
                    ),
                ]
            )
        )

    # Return just the content - MainLayout handles the app bar/navigation
    return ft.Container(
        content=ft.Column([
            ft.Text("User Management", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.DataTable(columns=columns, rows=rows),
        ]),
        padding=20,
        expand=True
    )

def UserEditView(
    page: ft.Page, ctx: ServiceContext, state: AppState, user_id: str
) -> ft.View:
    if not state.current_user or not ctx.policy.can_manage_users(state.current_user):
        page.go("/dashboard")
        return ft.View()

    try:
        target_user = ctx.auth_service.user_repo.get_by_id(uuid.UUID(user_id))
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        target_user = None

    if not target_user:
        return ft.View(controls=[ft.Text("User not found")])

    # Form Controls
    name_field = ft.TextField(
        label="Display Name", value=target_user.display_name, read_only=True
    )
    email_field = ft.TextField(
        label="Email", value=target_user.email, read_only=True
    )
    
    # Roles
    all_roles = ["owner", "admin", "publisher", "editor", "viewer"]
    role_checks: dict[str, ft.Checkbox] = {}
    
    roles_col = ft.Column()
    for r in all_roles:
        cb = ft.Checkbox(label=r, value=(r in target_user.roles))
        role_checks[r] = cb
        roles_col.controls.append(cb)

    # Status
    status_dropdown = ft.Dropdown(
        label="Status",
        options=[ft.dropdown.Option("active"), ft.dropdown.Option("disabled")],
        value=target_user.status
    )

    def save_changes(e: ft.ControlEvent) -> None:
        if not state.current_user:
            return
        try:
            new_roles = [r for r, cb in role_checks.items() if cb.value]
            new_status = status_dropdown.value
            
            ctx.auth_service.update_user(
                state.current_user,
                str(target_user.id),
                new_roles, 
                cast(str, new_status)
            )
            
            page.snack_bar = ft.SnackBar(ft.Text("User updated"))
            page.snack_bar.open = True
            page.update()
            
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"Error: {ex}"))
            page.snack_bar.open = True
            page.update()
    
    target_name = target_user.display_name

    # Return just the content - MainLayout handles the app bar/navigation
    return ft.Container(
        content=ft.Column([
            ft.Text(f"Edit User: {target_name}", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            name_field,
            email_field,
            ft.Text("Roles:"),
            roles_col,
            status_dropdown,
            ft.ElevatedButton("Save Changes", on_click=save_changes)
        ], width=600),
        padding=20,
        expand=True
    )
