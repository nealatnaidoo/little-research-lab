import logging

import flet as ft

from src.ui.context import ServiceContext
from src.ui.state import AppState

logger = logging.getLogger(__name__)

def RedeemInviteView(
    page: ft.Page, 
    ctx: ServiceContext, 
    state: AppState, 
    token: str
) -> ft.View:
    
    email_field = ft.TextField(label="Email", width=300)
    name_field = ft.TextField(label="Display Name", width=300)
    password_field = ft.TextField(
        label="Password", width=300, password=True, can_reveal_password=True
    )
    confirm_field = ft.TextField(
        label="Confirm Password", width=300, password=True
    )
    error_text = ft.Text(color="red", visible=False)
    
    def on_submit(e: ft.ControlEvent) -> None:
        if not email_field.value or not name_field.value or not password_field.value:
            error_text.value = "All fields are required."
            error_text.visible = True
            page.update()
            return
            
        if password_field.value != confirm_field.value:
            error_text.value = "Passwords do not match."
            error_text.visible = True
            page.update()
            return
            
        try:
            # Redeem
            user = ctx.invite_service.redeem_invite(
                token, 
                email_field.value, 
                name_field.value, 
                password_field.value
            )
            
            # Login
            session = ctx.auth_service.create_session(user)
            state.current_user = user
            state.current_session = session
            
            page.snack_bar = ft.SnackBar(ft.Text(f"Welcome, {user.display_name}!"))
            page.snack_bar.open = True
            page.go("/dashboard")
            
        except Exception as err:
            logger.error(f"Redemption error: {err}")
            error_text.value = str(err)
            error_text.visible = True
            page.update()

    return ft.View(
        f"/invite/{token}",
        [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Accept Invitation", style="headlineMedium"),
                        ft.Text(
                            "Create your account to join the lab.", 
                            size=14, color=ft.colors.OUTLINE
                        ),
                        email_field,
                        name_field,
                        password_field,
                        confirm_field,
                        error_text,
                        ft.ElevatedButton("Create Account", on_click=on_submit)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=20
                ),
                padding=50,
                alignment=ft.alignment.center
            )
        ]
    )
