import os
import platform
import subprocess
from functools import partial
from time import sleep

import flet as ft

from units import DatabaseManager, FileType, FileEntry

def main(page: ft.Page):
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    db = DatabaseManager("localhost", 3306, "root", "@", "File_Management")
    db.ensure_connection()
    result_list = db.fetch_all_files()
    for entry in result_list:
        print(entry)
    page.theme_mode = "dark"
    page.title = "File Management"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    header_text_style = ft.TextStyle(weight=ft.FontWeight.BOLD, size=20)

    page.floating_action_button = ft.IconButton(
        icon=ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.TEAL, icon_size=50
    )

    search_field = ft.TextField(hint_text="Search...", expand=3, border_width=3)

    async def update_list_search(e):
        nonlocal result_list
        result_list = db.search_with_keywords(search_field.value)
        populate_lv(list_view, result_list, page,db)

    search_field.on_submit = update_list_search
    reset_filter = ft.IconButton(icon=ft.Icons.CANCEL, icon_color="red", icon_size=30, expand=1)
    search_btn = ft.IconButton(icon=ft.Icons.SEARCH, icon_color=ft.Colors.GREY_50, icon_size=30, expand=1)
    search_btn.on_click = update_list_search
    search_container = ft.Container(
        content=ft.Row(
            controls=[
                reset_filter,
                search_field,
                search_btn,
            ]
        )
    )

    list_view = ft.ListView(expand=True)

    title_tv = ft.Text(value="Title", style=header_text_style)
    containing_folder_tv = ft.Text(value="Located in", style=header_text_style)
    size_tv = ft.Text(value="Size", style=header_text_style)

    async def sort(by: str, isAscending: bool):
        nonlocal result_list
        if isAscending:
            if by == "S":
                result_list.sort(key=lambda x: x.size if x.size is not None else 0)
            elif by == "T":
                result_list.sort(key=lambda x: x.name if x.name is not None else "")
        else:
            if by == "S":
                result_list.sort(key=lambda x: x.size if x.size is not None else 0, reverse=True)
            elif by == "T":
                result_list.sort(key=lambda x: x.name if x.name is not None else "", reverse=True)

        populate_lv(list_view, result_list, page,db)

    async def update_filters(w):
        if w == "S":
            title_tv.value = "Title"
            if size_tv.value == "Size ⬆️":
                size_tv.value = "Size ⬇️"
                await sort(w, True)
            else:
                size_tv.value = "Size ⬆️"
                await sort(w, False)

        elif w == "T":
            size_tv.value = "Size"
            if title_tv.value == "Title ⬆️":
                title_tv.value = "Title ⬇️"
                await sort(w, True)
            else:
                title_tv.value = "Title ⬆️"
                await sort(w, False)
        elif w == "reset":
            nonlocal result_list
            size_tv.value = "Size"
            title_tv.value = "Title"
            search_field.value = ""
            db.ensure_connection()
            result_list = db.fetch_all_files()
            populate_lv(list_view, result_list, page,db)

        page.update()

    async def on_size_tap(e):
        await update_filters("S")

    async def on_title_tap(e):
        await update_filters("T")

    async def on_reset_tap(e):
        await update_filters("reset")

    size_tv.on_tap = on_size_tap
    title_tv.on_tap = on_title_tap
    reset_filter.on_click = on_reset_tap

    header_row = ft.Container(
        content=ft.Row(
            controls=[
                header_text_view(title_tv, ft.Icons.TITLE, 1),
                header_text_view(containing_folder_tv, ft.Icons.FOLDER, 3),
                header_text_view(size_tv, ft.Icons.STORAGE, 1),
            ]
        ),
        margin=5,
        bgcolor="#000005",
        height=50,
        padding=10,
        border_radius=8,
    )

    populate_lv(list_view, result_list, page,db)
    page.update()

    main_container = ft.Container(
        content=ft.Column(controls=[search_container, header_row, list_view]),
        expand=True,
    )

    directory_tf = ft.TextField(hint_text="Directory")
    def on_dismiss(e):
        db.ensure_connection()
        result_list.clear()
        result_list.extend(db.fetch_all_files())
        populate_lv(list_view, result_list, page, db)
        page.update()

    async def directory_on_submit(e):
        path = directory_tf.value.strip()

        if not path:
            print("⚠️ No directory path provided!")
            return

        await db.insert_directory_to_db(path)
        db.ensure_connection()
        page.close(dlg)



    directory_tf.on_submit = directory_on_submit

    dlg = ft.AlertDialog(
        on_dismiss=on_dismiss,
        content=ft.Container(
            width=200,
            height=200,
            bgcolor="white",
            border_radius=8,
            content=directory_tf,
        ),
        content_padding=0, actions_padding=0, bgcolor="transparent",
    )

    def open_dialog(e):
        dlg.open = True
        page.add(dlg)
        page.update()

    page.floating_action_button.on_click = open_dialog

    page.add(main_container)


def populate_lv(list_view: ft.ListView, list_file_entry: list, page: ft.Page, db):
    list_view.controls.clear()

    MAX_ENTRIES = 1000  # Limit displayed entries
    displayed_entries = 0

    def open_containing_folder(e, file_path):
        if not os.path.exists(file_path):
            print(f"⚠️ Path does not exist: {file_path}")
            return

        system = platform.system()
        target = os.path.abspath(file_path)
        parent_folder = os.path.dirname(target)

        try:
            if system == "Windows":
                subprocess.run(["explorer", "/select,", os.path.normpath(target)], check=True)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", "-R", target], check=True)
            elif system == "Linux":
                subprocess.run(["xdg-open", parent_folder], check=True)
            else:
                print("⚠️ Unsupported OS")
        except Exception as e:
            print(f"⚠️ Error opening folder: {e}")

    def delete_file(e, file_id,dialog):
        print(f"Deleting ID: {file_id}")
        db.ensure_connection()
        db.delete_directory(file_id)
        page.close(dialog)
        refresh_list()
        page.update()

    def refresh_list():
        db.ensure_connection()
        new_list = db.fetch_all_files()
        populate_lv(list_view, new_list, page, db)

    for i in list_file_entry:
        if displayed_entries >= MAX_ENTRIES:
            break
        displayed_entries += 1

        icon = ft.Icons.INSERT_DRIVE_FILE if i.type == "file" else ft.Icons.FOLDER

        dialog_show_parameters = ft.AlertDialog(
            on_dismiss=lambda e: refresh_list(),
            content=ft.Container(
                border_radius=12,
                bgcolor="#101020",
                padding=20,
                content=ft.Column(
                    controls=[
                        ft.Text(value=i.name, style=ft.TextStyle(weight=ft.FontWeight.BOLD)),
                        ft.Text(value="Absolute Path:", style=ft.TextStyle(weight=ft.FontWeight.BOLD)),
                        ft.Text(value=i.abs_path),
                        ft.Button(text="Open Folder", on_click=partial(open_containing_folder, file_path=i.abs_path)),
                        ft.Text(value="⚠️ This action cannot be undone!", style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                                color="red"),
                    ]
                )
            ),
            content_padding=0, actions_padding=0, bgcolor="transparent"
        )

        delete_button = ft.ElevatedButton(
            text="Delete File",
            on_click=partial(delete_file, file_id=i.id, dialog=dialog_show_parameters)
        )

        dialog_show_parameters.content.content.controls.append(delete_button)

        def open_dialog(e, d=dialog_show_parameters):
            d.open = True
            page.add(d)
            page.update()

        # Create file row container
        item = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(icon, color="#4060F0", size=20),
                                ft.Text(value=i.name, expand=1),
                            ]
                        ),
                        expand=1,
                    ),
                    ft.Text(value=i.parent_path if i.parent_path else "Root Directory", expand=3),
                    ft.Text(value=f"{i.size} Bytes" if i.size else "Folder", expand=1),
                ]
            ),
            bgcolor="#000010",
            height=50,
            margin=5,
            padding=ft.Padding(left=15, right=15, bottom=10, top=10),
            border_radius=12,
            on_click=partial(open_dialog, d=dialog_show_parameters)  # ✅ Fix: Ensure correct file info shows
        )

        list_view.controls.append(item)

    # Append End Message
    list_view.controls.append(
        ft.Container(
            content=ft.Text(value="You reached the end", expand=1),
            bgcolor="black",
            padding=10,
            margin=10,
            border_radius=8,
        )
    )

    page.update()

def header_text_view(text_view: ft.Text, icon, expand) -> ft.Container:
    return ft.Container(
        content=ft.Row(controls=[ft.Icon(icon), text_view]), expand=expand, on_click=text_view.on_tap
    )


if __name__ == "__main__":
    ft.app(target=main)
