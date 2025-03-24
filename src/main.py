import json
import os
import platform
import subprocess
from functools import partial
import flet as ft
import flet_lottie as fl
from units import DatabaseManager, FileType, FileEntry, encode_animation

current_page = 0
files_per_page = 500


def get_db_credentials(filepath="credentials.json"):
    try:
        with open(filepath, "r") as f:
            credentials = json.load(f)
            host = credentials.get("host")
            port = credentials.get("port")
            user = credentials.get("user")
            password = credentials.get("password")
            database = credentials.get("database")
            return host, port, user, password, database
    except FileNotFoundError:
        return None, None, None, None, None
    except json.JSONDecodeError:
        return None, None, None, None, None
    except TypeError:  # added type error handling
        return None, None, None, None, None


def setPageZero():
    global current_page
    current_page = 0

credential = None
async def main(page: ft.Page):
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = "dark"
    page.title = "File Management"

    async def build_UI():
        global credential
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        header_text_style = ft.TextStyle(weight=ft.FontWeight.BOLD, size=20)
        host, port, user, password, database = get_db_credentials()

        if host is None or port is None or user is None or database is None:
            display_credential_error()
            return
        # if password is None:
        #     if credential is not None:
        #         password = credential
        #     else:
        #         if credential is not None:
        #             password = credential
        #         else:
        #             display_password_ask()
        #             return
        if credential is None:
            if password is None:
                display_password_ask()
                return
        else:
            password = credential

        db = DatabaseManager(host=host, port=port, user=user, passwd=password, database=database)
        try:
            db.ensure_connection()
        except Exception:
            if password is None:
                display_password_ask()
                return
            if credential is not None:
                display_password_ask()
                return
            else:
                display_auth_error()
                return
        result_list = db.fetch_all_files()

        paging_tv = ft.Text()

        async def go_left(e):
            global current_page
            if current_page > 0:
                current_page -= 1
                await refresh_list_view(list_view, result_list, page, db, paging_tv)

        async def go_right(e):
            global current_page
            if (current_page + 1) * files_per_page < len(result_list):
                current_page += 1
                await refresh_list_view(list_view, result_list, page, db, paging_tv)

        left_button = ft.ElevatedButton("⬅️", on_click=go_left)
        right_button = ft.ElevatedButton("➡️", on_click=go_right)
        paging = ft.Row(controls=[left_button, paging_tv, right_button])

        page.floating_action_button = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE, icon_color=ft.Colors.TEAL, icon_size=50
        )

        search_field = ft.TextField(hint_text="Search...", expand=3, border_width=3)

        async def update_list_search(e):
            title_tv.value = "Title"
            size_tv.value = "Size"
            nonlocal result_list
            result_list = db.search_with_keywords(search_field.value)
            setPageZero()
            await refresh_list_view(list_view, result_list, page, db, paging_tv)
            page.update()
            list_view.scroll_to(0)

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
            setPageZero()
            await refresh_list_view(list_view, result_list, page, db, paging_tv)
            list_view.scroll_to(0)

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
                setPageZero()
                await refresh_list_view(list_view, result_list, page, db, paging_tv)
                list_view.scroll_to(0)

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

        setPageZero()
        await refresh_list_view(list_view, result_list, page, db, paging_tv)

        page.update()

        main_container = ft.Container(
            content=ft.Column(controls=[search_container, header_row, list_view, paging]),
            expand=True,
        )

        directory_tf = ft.TextField(hint_text="Directory", border_color="green")

        def on_dismiss(e):
            refresh()

        delete_dialog = ft.AlertDialog(
            on_dismiss=on_dismiss,
            content=ft.Container(
                bgcolor="#051015",
                border_radius=4,
                content=ft.Column(
                    tight=True,
                    controls=[ft.Text("Enter Valid Directory and press Enter", text_align=ft.alignment.center),
                              directory_tf,
                              ]
                )
            ),
            content_padding=0, actions_padding=0, bgcolor="transparent",
        )

        async def directory_on_submit(e):
            value = str(directory_tf.value)
            path = os.path.exists(value)

            if not path:
                print("⚠️ No directory path provided!")
                directory_tf.border_color = "red"
                page.update()
                return
            directory_tf.border_color = "green"
            anim_loading = encode_animation("anim/anim_loading.json")
            delete_dialog.content.content.controls[1]=fl.Lottie(
                    src_base64=anim_loading,
                    width=300,
                    height=300,
                    repeat=True,
                    animate=True,

                )

            delete_dialog.update()
            page.update()
            await db.insert_directory_to_db(value)
            db.ensure_connection()
            page.close(delete_dialog)
            page.update()

        delete_dialog.content.content.controls[1].on_submit = directory_on_submit

        def open_dialog(e):
            page.add(delete_dialog)
            delete_dialog.open = True
            page.update()

        page.floating_action_button.on_click = open_dialog
        page.add(main_container)

    def display_credential_error():
        page.clean()
        global credential
        credential = None
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.add(ft.Text("There was an error on credential file credentials.json please fix it and refresh"))
        anim_not_found = encode_animation("anim/anim_not_found.json")
        page.add(fl.Lottie(
            src_base64=anim_not_found,
            width=300,
            height=300,
            repeat=True,
            animate=True
        ))
        page.add(ft.IconButton(icon=ft.Icons.REFRESH, on_click=lambda e: refresh(), icon_size=30))
        json_example = """
        //Example:
        {
          "host": "localhost",
          "port": 3306,
          "database": "File_Management",
          "user": "root",
          "password": "Your DB password" (Optional)
        }
        """

        text_control = ft.Text(value=str(json_example))
        page.add(text_control)

    def display_auth_error():
        page.clean()
        global credential
        credential = None
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        anim_auth_err = encode_animation("anim/anim_auth_fail.json")
        page.add(fl.Lottie(
            src_base64=anim_auth_err,
            width=300,
            height=300,
            repeat=True,
            animate=True
        ))
        page.add(ft.Text("Wrong credentials or MYSQL server is not installed"))
        page.add(ft.IconButton(icon=ft.Icons.REFRESH, on_click=lambda e: refresh(), icon_size=30))
        def manual_password(e):
            global credential
            credential = "1"
            refresh()

        page.add(ft.IconButton(icon=ft.Icons.PASSWORD, on_click= manual_password, icon_size=30))
        page.add(ft.Text("Your auto-logon maybe configured wrongly you can enter your password manually"))

    def display_password_ask():
        page.clean()
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        column = ft.Column(
            width=page.width,
            height=page.height,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER
        )

        async def password_on_submit(e):
            global credential
            credential = str(password_field.value)
            await refresh()
        password_field = ft.TextField(hint_text="Password", max_lines=1,text_align=ft.alignment.center,password=True,can_reveal_password=True)
        password_field.on_submit = password_on_submit
        column.controls.append(ft.Text(value="Enter Password and press Enter",size=25,style=ft.TextStyle(weight=ft.FontWeight.BOLD)))
        column.controls.append(password_field)
        page.add(column)
        page.update()


    async def refresh():
        page.clean()
        await build_UI()

    await refresh()


async def refresh_list_view(list_view: ft.ListView, list_file_entry: list, page: ft.Page, db, paging: ft.Text,
                      page_number=None):
    list_view.controls.clear()
    global current_page
    global files_per_page

    start_index = current_page * files_per_page

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

    async def delete_file(e, file_id, dialog,page):
        print(f"Deleting ID: {file_id}")
        db.ensure_connection()
        anim_loading = encode_animation("anim/anim_loading.json")
        dialog.content.content.controls[7]=fl.Lottie(
                src_base64=anim_loading,
                width=300,
                height=300,
                repeat=True,
                animate=True
            )



        dialog.update()
        page.update()
        await db.delete_directory(file_id)
        page.close(dialog)
        refresh_list()
        page.update()

    def refresh_list():
        db.ensure_connection()
        new_list = db.fetch_all_files()
        setPageZero()
        refresh_list_view(list_view, new_list, page, db, paging)
        list_view.scroll_to(0)

    for entry in list_file_entry[start_index:]:
        if displayed_entries >= files_per_page:
            break
        displayed_entries += 1

        icon = ft.Icons.INSERT_DRIVE_FILE if entry.type == "file" else ft.Icons.FOLDER

        title_text_field = ft.TextField(value=entry.name, border_color="yellow")

        def updateFN(e, entry_id, text_field):
            db.update(entry=FileEntry(id=entry_id, name=text_field.value))

        title_text_field.on_submit = lambda e, eid=entry.id, tf=title_text_field: updateFN(e, eid, tf)
        def on_dialog_dismiss(e):
            dialog_show_parameters.open =False
            refresh_list()
        dialog_show_parameters = ft.AlertDialog(
            on_dismiss=lambda e: on_dialog_dismiss(e),
            content=ft.Container(
                border_radius=12,
                bgcolor="#101020",
                padding=20,
                content=ft.Column(
                    controls=[
                        ft.Text(value="Title: ", style=ft.TextStyle(weight=ft.FontWeight.BOLD)),
                        title_text_field,
                        ft.Text(value="You can rename title name above and Press Enter to Save", size=10,
                                color="yellow"),
                        ft.Text(value="Absolute Path:", style=ft.TextStyle(weight=ft.FontWeight.BOLD)),
                        ft.Text(value=entry.abs_path),
                        ft.Button(text="Open Folder",
                                  on_click=partial(open_containing_folder, file_path=entry.abs_path)),
                        ft.Text(value="⚠️ This action cannot be undone!", style=ft.TextStyle(weight=ft.FontWeight.BOLD),
                                color="red"),
                    ]
                )
            ),
            content_padding=0, actions_padding=0, bgcolor="transparent"
        )

        delete_button = ft.ElevatedButton(
            text="Delete File",
            on_click=partial(delete_file, file_id=entry.id, dialog=dialog_show_parameters,page=page),
        )

        dialog_show_parameters.content.content.controls.append(delete_button)

        def open_dialog(e, d=dialog_show_parameters):
            d.open = True
            page.add(d)
            page.update()

        item = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(icon, color="#4060F0", size=20),
                                ft.Text(value=entry.name, expand=1),
                            ]
                        ),
                        expand=1,
                    ),
                    ft.Text(value=entry.parent_path if entry.parent_path else "Root Directory", expand=3),
                    ft.Text(value=f"{FileEntry.format_bytes(entry.size)}" if entry.size else "Folder", expand=1),
                ]
            ),
            bgcolor="#000010",
            height=50,
            margin=5,
            padding=ft.Padding(left=15, right=15, bottom=10, top=10),
            border_radius=12,
            on_click=partial(open_dialog, d=dialog_show_parameters)
        )

        list_view.controls.append(item)

    list_view.controls.append(
        ft.Container(
            content=ft.Text(value="You reached the end", expand=1),
            bgcolor="black",
            padding=10,
            margin=10,
            border_radius=8,
        )
    )

    remainder = 0
    if len(list_file_entry) % 500 > 0:
        remainder = 1

    paging.value = f"{displayed_entries} out of {len(list_file_entry)} entries | Page {current_page + 1} / {len(list_file_entry) // 500 + remainder}"

    page.update()


def header_text_view(text_view: ft.Text, icon, expand) -> ft.Container:
    return ft.Container(
        content=ft.Row(controls=[ft.Icon(icon), text_view]), expand=expand, on_click=text_view.on_tap
    )


# def restart():
#     # python = sys.executable
#     subprocess.Popen([sys.executable, *sys.argv])
#     sys.exit(0)
#
#     # os.execl(python, python, *sys.argv)

if __name__ == "__main__":
    ft.app(target=main)
