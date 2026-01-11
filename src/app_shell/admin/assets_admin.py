import logging

import flet as ft

from src.ui.context import ServiceContext
from src.ui.state import AppState

logger = logging.getLogger(__name__)

def AssetListView(page: ft.Page, ctx: ServiceContext, state: AppState) -> ft.View:

    def on_delete(e: ft.ControlEvent) -> None:
        # asset_id = e.control.data
        # Deletion logic implementation needed in Repo/Service first.
        # Currently showing a snackbar.
        page.snack_bar = ft.SnackBar(ft.Text("Deletion not yet implemented."))
        page.snack_bar.open = True
        page.update()

    def on_upload_result(e: ft.FilePickerResultEvent) -> None:
        if not e.files or not state.current_user:
            return
            
        # Rate Limit Check
        if not ctx.rate_limiter.check_upload(str(state.current_user.id)):
            page.snack_bar = ft.SnackBar(ft.Text("Upload rate limit exceeded."))
            page.snack_bar.open = True
            page.update()
            return

        for f in e.files:
            try:
                # In Flet web/desktop, dealing with file content:
                # If path is available (desktop):
                if f.path:
                    with open(f.path, "rb") as file:
                        data = file.read()
                        
                        if not state.current_user:
                             raise PermissionError("Not logged in")

                        ctx.asset_service.upload_asset(
                            user=state.current_user,
                            filename=f.name,
                            # Inferred or passed? flet might give it?
                            mime_type="application/octet-stream", 
                            data=data,
                            visibility="public" # Default to public for now?
                        )
                
                page.snack_bar = ft.SnackBar(ft.Text(f"Uploaded {f.name}"))
                page.snack_bar.open = True
            except Exception as err:
                logger.error(f"Upload error: {err}")
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Error uploading {f.name}: {err}")
                )
                page.snack_bar.open = True
        
        # Refresh
        page.update()
        page.go("/admin/assets")

    file_picker = ft.FilePicker(on_result=on_upload_result)
    page.overlay.append(file_picker)
    page.update()

    # Data Fetch
    try:
        # SQLiteAssetRepo has list_assets
        assets = ctx.asset_service.repo.list_assets()
    except AttributeError:
        assets = []
        
    from src.app_shell.asset_routes import AssetHandler
    handler = AssetHandler(ctx)

    # UI Construction
    rows = []
    for asset in assets:
        # Preview
        preview_control = ft.Icon(ft.Icons.INSERT_DRIVE_FILE)
        if asset.mime_type.startswith("image/"):
            b64_data = handler.get_asset_content_base64(state.current_user, asset.id)
            if b64_data:
                preview_control = ft.Image(
                    src_base64=b64_data, 
                    width=50, 
                    height=50, 
                    fit=ft.ImageFit.CONTAIN
                )

        rows.append(ft.DataRow(
            cells=[
                ft.DataCell(preview_control), 
                ft.DataCell(ft.Text(asset.filename_original)),
                ft.DataCell(ft.Text(asset.mime_type)),
                ft.DataCell(ft.Text(f"{asset.size_bytes} B")),
                ft.DataCell(ft.Text(asset.created_at.strftime("%Y-%m-%d"))),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.DELETE, 
                        data=str(asset.id), 
                        on_click=on_delete
                    )
                ),
            ]
        ))

    # Return just the content - MainLayout handles the app bar/navigation
    return ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text("All Assets", size=20, weight=ft.FontWeight.BOLD),
                        ft.ElevatedButton(
                            "Upload File", 
                            icon=ft.Icons.UPLOAD, 
                            on_click=lambda _: file_picker.pick_files()
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(),
                    ft.DataTable(
                        columns=[
                            ft.DataColumn(ft.Text("Preview")),
                            ft.DataColumn(ft.Text("Filename")),
                            ft.DataColumn(ft.Text("Type")),
                            ft.DataColumn(ft.Text("Size")),
                            ft.DataColumn(ft.Text("Created")),
                            ft.DataColumn(ft.Text("Actions")),
                        ],
                        rows=rows,
                    )
                ], scroll=ft.ScrollMode.AUTO),
                padding=20,
                expand=True
            )
