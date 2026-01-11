import flet as ft

from src.ui.context import ServiceContext
from src.ui.state import AppState


class LoginView(ft.Column): # type: ignore
    def __init__(self, page: ft.Page, ctx: ServiceContext, state: AppState) -> None:
        super().__init__()
        self.page = page
        self.ctx = ctx
        self.state = state
        
        self.email = ft.TextField(label="Email", width=300)
        self.password = ft.TextField(
            label="Password", width=300, password=True, can_reveal_password=True
        )
        self.error_text = ft.Text(color="red", visible=False)
        
        # Setup Column properties
        self.alignment = ft.MainAxisAlignment.CENTER
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.controls = [
            ft.Text("Little Research Lab", style="headlineMedium"),
            self.email,
            self.password,
            self.error_text,
            ft.ElevatedButton("Login", on_click=self.login_click)
        ]

    def login_click(self, e: ft.ControlEvent) -> None:
        email = self.email.value
        pwd = self.password.value
        
        if not email or not pwd:
            self.error_text.value = "Please enter email and password."
            self.error_text.visible = True
            self.update()
            return
            
        # Rate Limit Check
        client_ip = self.page.client_ip or "unknown"
        if not self.ctx.rate_limiter.check_login(client_ip):
            self.error_text.value = "Too many attempts. Please try again later."
            self.error_text.visible = True
            self.update()
            return
            
        user = self.ctx.auth_service.login(email, pwd)
        if user:
            # Create session
            session = self.ctx.auth_service.create_session(user)
            self.state.current_user = user
            self.state.current_session = session
            self.page.go("/dashboard")
        else:
            self.error_text.value = "Invalid credentials."
            self.error_text.visible = True
            self.update()
