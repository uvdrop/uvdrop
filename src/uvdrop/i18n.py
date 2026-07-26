"""Lightweight UI translations (Japanese / English / Chinese).

Default language follows the OS locale. Users can override it in Settings.
Keep wording plain: non-engineers should understand what happens and what
they are approving, without scary jargon.
"""

from __future__ import annotations

import locale
from typing import Any

# Supported UI languages
LANG_JA = "ja"
LANG_EN = "en"
LANG_ZH = "zh"
SUPPORTED = (LANG_JA, LANG_EN, LANG_ZH)

_current: str = LANG_JA


def detect_os_language() -> str:
    """Map the OS locale to ja / en / zh. Falls back to English."""
    raw = ""
    try:
        loc = locale.getlocale()
        if loc and loc[0]:
            raw = loc[0]
    except Exception:  # noqa: BLE001
        raw = ""
    if not raw:
        try:
            import os

            raw = os.environ.get("LANG") or os.environ.get("LC_ALL") or ""
        except Exception:  # noqa: BLE001
            raw = ""
    raw = raw.replace("_", "-").lower()
    if raw.startswith("ja"):
        return LANG_JA
    if raw.startswith("zh"):
        return LANG_ZH
    return LANG_EN


def set_language(code: str | None) -> str:
    """Activate a language. Empty / None / 'auto' → OS default."""
    global _current
    if not code or code == "auto":
        _current = detect_os_language()
    elif code in SUPPORTED:
        _current = code
    else:
        _current = detect_os_language()
    return _current


def get_language() -> str:
    return _current


def language_label(code: str) -> str:
    return {
        "auto": {"ja": "自動（OSの設定）", "en": "Auto (system)", "zh": "自动（跟随系统）"},
        LANG_JA: {"ja": "日本語", "en": "Japanese", "zh": "日语"},
        LANG_EN: {"ja": "English", "en": "English", "zh": "英语"},
        LANG_ZH: {"ja": "中文", "en": "Chinese", "zh": "中文"},
    }.get(code, {}).get(_current, code)


# --- catalog -----------------------------------------------------------------

_STRINGS: dict[str, dict[str, str]] = {
    # app chrome
    "app.subtitle": {
        "ja": "Python アプリのフォルダや ZIP を選ぶと、仮想環境を作って起動します",
        "en": "Choose a Python app folder or ZIP to create an environment and run it",
        "zh": "选择 Python 应用文件夹或 ZIP，即可创建环境并启动",
    },
    "app.help": {"ja": "ヘルプ", "en": "Help", "zh": "帮助"},
    "app.settings": {"ja": "設定", "en": "Settings", "zh": "设置"},
    "app.step1": {"ja": "1. 起動する", "en": "1. Run an app", "zh": "1. 启动应用"},
    "app.sample_link": {"ja": "サンプルで試す", "en": "Try a sample", "zh": "试用示例"},
    "app.open_folder": {"ja": "フォルダを開く", "en": "Open folder", "zh": "打开文件夹"},
    "app.open_folder_sub": {
        "ja": "pyproject.toml がある場所",
        "en": "A folder with pyproject.toml",
        "zh": "包含 pyproject.toml 的文件夹",
    },
    "app.open_zip": {"ja": "ZIP を開く", "en": "Open ZIP", "zh": "打开 ZIP"},
    "app.open_zip_sub": {
        "ja": "同じ構成を固めたもの",
        "en": "The same layout, packaged",
        "zh": "相同结构的压缩包",
    },
    "app.open_catalog": {"ja": "カタログから開く", "en": "Open from catalog", "zh": "从目录打开"},
    "app.open_catalog_sub": {
        "ja": "共有フォルダのカタログ一覧",
        "en": "Apps listed in shared catalogs",
        "zh": "共享目录中的应用列表",
    },
    "app.hint_confirm": {
        "ja": "実行前に、インストールされるパッケージを確認できます。",
        "en": "You can review packages before anything is installed.",
        "zh": "安装前可先确认将要安装的软件包。",
    },
    "app.step2": {"ja": "2. 取り込んだアプリ", "en": "2. Saved apps", "zh": "2. 已导入的应用"},
    "app.filter": {"ja": "絞り込み", "en": "Filter", "zh": "筛选"},
    "app.filter_clear": {"ja": "解除", "en": "Clear", "zh": "清除"},
    "app.filter_hint": {
        "ja": "名前・場所などを部分一致で絞り込み（空白区切りで AND）",
        "en": "Partial match on name, location, … (space-separated AND)",
        "zh": "按名称、位置等部分匹配筛选（空格分隔为 AND）",
    },
    "app.usage": {"ja": "使用状況", "en": "Usage", "zh": "使用情况"},
    "app.col_name": {"ja": "名前", "en": "Name", "zh": "名称"},
    "app.col_mode": {"ja": "モード", "en": "Mode", "zh": "模式"},
    "app.col_last": {"ja": "最終起動", "en": "Last run", "zh": "上次启动"},
    "app.col_runs": {"ja": "起動回数", "en": "Runs", "zh": "启动次数"},
    "app.col_place": {"ja": "場所", "en": "Location", "zh": "位置"},
    "app.empty": {
        "ja": "まだありません。上から起動すると、ここに並びます。\nダブルクリック、または下のボタンで再起動できます。不要になったら「削除」で消せます。",
        "en": "Nothing here yet. Apps you run will appear in this list.\nDouble-click or use the buttons below to run again. Remove ones you no longer need.",
        "zh": "暂无内容。启动过的应用会出现在这里。\n可双击或用下方按钮再次启动。不需要时请删除。",
    },
    "app.relaunch": {"ja": "再起動", "en": "Run again", "zh": "再次启动"},
    "app.edit_env": {"ja": ".env を編集", "en": "Edit .env", "zh": "编辑 .env"},
    "app.shortcut": {"ja": "ショートカット", "en": "Shortcut", "zh": "快捷方式"},
    "app.delete": {"ja": "削除", "en": "Delete", "zh": "删除"},
    "app.refresh": {"ja": "更新", "en": "Refresh", "zh": "刷新"},
    "app.log": {"ja": "ログ", "en": "Log", "zh": "日志"},
    "app.log_show": {"ja": "表示", "en": "Show", "zh": "显示"},
    "app.licenses": {"ja": "ライセンス", "en": "Licenses", "zh": "许可证"},
    # confirm
    "confirm.title": {"ja": "実行内容の確認", "en": "Review before running", "zh": "运行前确认"},
    "confirm.lead": {
        "ja": "仮想環境を作る前に、内容をご確認ください。",
        "en": "Please review what will be installed before the environment is created.",
        "zh": "创建环境之前，请先确认以下内容。",
    },
    "confirm.run": {"ja": "この内容で実行", "en": "Run with this setup", "zh": "按此内容运行"},
    "confirm.abort": {"ja": "中止", "en": "Cancel", "zh": "取消"},
    "confirm.show_console": {
        "ja": "コンソール窓を表示する",
        "en": "Show console window",
        "zh": "显示控制台窗口",
    },
    "confirm.cmd_label": {"ja": "起動コマンド", "en": "Start command", "zh": "启动命令"},
    "confirm.cmd": {"ja": "起動コマンド", "en": "Start command", "zh": "启动命令"},
    "confirm.packages": {
        "ja": "インストールされるパッケージ",
        "en": "Packages to install",
        "zh": "将安装的软件包",
    },
    "confirm.resolved": {
        "ja": "・解決済みの全体",
        "en": " · full resolved set",
        "zh": "·已解析的完整列表",
    },
    "confirm.declared_only": {
        "ja": "・直接指定のみ",
        "en": " · declared only",
        "zh": "·仅直接声明",
    },
    "confirm.resolved_hint": {
        "ja": "直接指定したものと、その依存関係として一緒に入るもの（推移依存）の両方を表示しています。",
        "en": "Shows both packages you asked for and transitive dependencies installed with them.",
        "zh": "同时显示您指定的软件包以及随其安装的传递依赖。",
    },
    "confirm.no_allow": {
        "ja": "許可リストは未設定です",
        "en": "No allow list is set",
        "zh": "尚未设置许可列表",
    },
    "confirm.no_allow_body": {
        "ja": "すべてのパッケージがそのまま入ります。設定で許可リストを有効にできます。",
        "en": "Every package will be allowed. You can turn on an allow list in Settings.",
        "zh": "所有软件包都会被允许安装。可在设置中启用许可列表。",
    },
    "confirm.resolve_fail": {
        "ja": "あわせて入るパッケージをすべて確認できませんでした",
        "en": "Could not review every package that comes along",
        "zh": "无法确认全部一并安装的软件包",
    },
    "confirm.resolve_fail_body": {
        "ja": "ネットワークやプロジェクトの都合で全体の解決に失敗しました。いま表示しているのは、アプリが直接指定したパッケージだけです。",
        "en": "Full resolution failed (network or project issue). Only the packages the app named directly are shown.",
        "zh": "因网络或项目原因，完整解析失败。当前仅显示应用直接指定的软件包。",
    },
    "confirm.blocked": {"ja": "実行できません", "en": "Cannot run", "zh": "无法运行"},
    "confirm.blocked_body": {
        "ja": "許可されていない項目があります（仮想環境は作成していません）。",
        "en": "Something is not allowed (no environment was created).",
        "zh": "存在未允许的项目（尚未创建环境）。",
    },
    # settings
    "settings.title": {"ja": "設定", "en": "Settings", "zh": "设置"},
    "settings.heading": {"ja": "安全とポリシー", "en": "Safety & policy", "zh": "安全与策略"},
    "settings.save_hint": {
        "ja": "表の編集後は下の「保存して閉じる」を押してください。",
        "en": "After editing tables, press “Save and close” below.",
        "zh": "编辑表格后，请点击下方的“保存并关闭”。",
    },
    "settings.save": {"ja": "保存して閉じる", "en": "Save and close", "zh": "保存并关闭"},
    "settings.cancel": {"ja": "キャンセル", "en": "Cancel", "zh": "取消"},
    "settings.tab_guard": {"ja": "実行前の確認", "en": "Before running", "zh": "运行前确认"},
    "settings.tab_allow": {"ja": "許可リスト", "en": "Allow list", "zh": "许可列表"},
    "settings.tab_block": {"ja": "NGリスト", "en": "Block list", "zh": "禁止列表"},
    "settings.tab_proxy": {"ja": "プロキシ", "en": "Proxy", "zh": "代理"},
    "settings.tab_lang": {"ja": "表示言語", "en": "Language", "zh": "显示语言"},
    "settings.tab_catalog": {"ja": "カタログ", "en": "Catalogs", "zh": "目录"},
    "settings.catalog_hint": {
        "ja": "共有フォルダ上のカタログファイル、またはカタログAPIのHTTP(S)エンドポイントを登録します（複数可）。フォルダの自動走査はしません。",
        "en": "Register catalog files or HTTP(S) catalog API endpoints (multiple OK). Folders are not auto-scanned.",
        "zh": "注册目录文件或 HTTP(S) 目录 API 端点（可多个）。不会自动扫描文件夹。",
    },
    "settings.catalog_add": {"ja": "追加…", "en": "Add…", "zh": "添加…"},
    "settings.catalog_add_url": {"ja": "URL を追加…", "en": "Add URL…", "zh": "添加 URL…"},
    "settings.catalog_url_prompt": {
        "ja": "カタログAPIのエンドポイント（JSONを返すURL。末尾は .json でなくても可）",
        "en": "Catalog API endpoint (a JSON response; .json suffix is not required)",
        "zh": "目录 API 端点（返回 JSON；无需以 .json 结尾）",
    },
    "settings.catalog_remove": {"ja": "削除", "en": "Remove", "zh": "删除"},
    "settings.catalog_pick": {
        "ja": "カタログ JSON を選ぶ",
        "en": "Choose a catalog JSON",
        "zh": "选择目录 JSON",
    },
    "settings.catalog_empty": {
        "ja": "まだ登録がありません。共有ドライブ上のカタログ JSON か HTTP URL を追加してください。",
        "en": "None yet. Add a catalog JSON from a shared drive or an HTTP URL.",
        "zh": "尚未注册。请添加共享驱动器上的目录 JSON 或 HTTP URL。",
    },
    "settings.confirm_each": {
        "ja": "毎回、実行前に内容を確認する",
        "en": "Always review packages before running",
        "zh": "每次运行前都确认内容",
    },
    "settings.no_al": {
        "ja": "許可リストが未設定のとき",
        "en": "When no allow list is set",
        "zh": "未设置许可列表时",
    },
    "settings.no_al_confirm": {
        "ja": "確認画面を出す（推奨）",
        "en": "Show the review screen (recommended)",
        "zh": "显示确认界面（推荐）",
    },
    "settings.no_al_allow": {
        "ja": "そのまま進む",
        "en": "Continue without asking",
        "zh": "直接继续",
    },
    "settings.req": {
        "ja": "requirements.txt からの変換を許可する",
        "en": "Allow converting from requirements.txt",
        "zh": "允许从 requirements.txt 转换",
    },
    "settings.console": {
        "ja": "起動時にコンソール窓を出す（既定値・デバッグ用）",
        "en": "Show a console window when running (default / debugging)",
        "zh": "启动时显示控制台窗口（默认值・调试用）",
    },
    "settings.lang_label": {
        "ja": "表示に使う言語",
        "en": "Display language",
        "zh": "界面语言",
    },
    "settings.lang_hint": {
        "ja": "「自動」はパソコンの言語設定に合わせます。変更は保存後、アプリを開き直すと全体に反映されます。",
        "en": "“Auto” follows your computer’s language. Restart the app after saving to apply everywhere.",
        "zh": "“自动”会跟随电脑的语言设置。保存后重新打开应用即可全局生效。",
    },
    "settings.allow_use": {
        "ja": "この表の許可リストを使う",
        "en": "Use this allow list",
        "zh": "使用此许可列表",
    },
    "settings.block_use": {
        "ja": "NGリストを使う（ヒットで即ブロック）",
        "en": "Use the block list (always blocks matches)",
        "zh": "使用禁止列表（匹配即阻止）",
    },
    "settings.save_note": {
        "ja": "※ 変更は下の「保存して閉じる」で反映",
        "en": "※ Changes apply when you press “Save and close”",
        "zh": "※ 更改需点击下方“保存并关闭”后生效",
    },
    # common
    "common.close": {"ja": "閉じる", "en": "Close", "zh": "关闭"},
    "common.today": {"ja": "今日", "en": "Today", "zh": "今天"},
    "common.yesterday": {"ja": "昨日", "en": "Yesterday", "zh": "昨天"},
    "common.help_q": {"ja": "？", "en": "?", "zh": "？"},
    # confirm dialog extras
    "confirm.need_cmd": {
        "ja": "起動コマンドを入力してください。",
        "en": "Please enter a start command.",
        "zh": "请输入启动命令。",
    },
    "confirm.converted": {
        "ja": "requirements.txt から変換しました",
        "en": "Converted from requirements.txt",
        "zh": "已从 requirements.txt 转换",
    },
    "confirm.converted_body": {
        "ja": "簡易変換のため、そのままでは動かないことがあります。",
        "en": "This is a best-effort conversion; it may not run as-is.",
        "zh": "这是尽力而为的转换，可能无法直接运行。",
    },
    "confirm.converted_skipped": {
        "ja": "\n取り込めなかった行: {n} 件",
        "en": "\nLines that could not be converted: {n}",
        "zh": "\n无法转换的行数：{n}",
    },
    "confirm.no_entry": {
        "ja": "起動するファイルを見つけられませんでした",
        "en": "Could not find a file to run",
        "zh": "未能找到可运行的文件",
    },
    "confirm.no_entry_body": {
        "ja": "main.py などが無いため、下の欄に実行するファイルを入力してください。",
        "en": "No main.py etc. was found. Please type the file to run below.",
        "zh": "未找到 main.py 等文件。请在下方输入要运行的文件。",
    },
    "confirm.cmd_hint": {
        "ja": "{dir} で実行します。ファイル名と引数を指定できます（例: main.py --debug）。",
        "en": "Runs in {dir}. You can set the file name and arguments (e.g. main.py --debug).",
        "zh": "在 {dir} 中运行。可指定文件名和参数（例如 main.py --debug）。",
    },
    "confirm.unresolved_title": {
        "ja": "バージョンを正確に判定できない項目があります",
        "en": "Some versions cannot be judged precisely",
        "zh": "部分版本无法精确判断",
    },
    "confirm.unresolved_body": {
        "ja": "PyPI のバージョン表記は公開者しだいのため、数字だけでは比べられない書き方があります。次の項目は判定が概算、または規則が使われていません。",
        "en": "PyPI version formats depend on the publisher, so some cannot be compared by numbers alone. The items below are approximate, or their rule was not applied.",
        "zh": "PyPI 的版本写法由发布者决定，有些无法仅凭数字比较。以下项目为近似判断，或其规则未被应用。",
    },
    "confirm.unresolved_more": {
        "ja": "\n…ほか {n} 件",
        "en": "\n… and {n} more",
        "zh": "\n……另有 {n} 项",
    },
    "confirm.version_guide": {
        "ja": "バージョンの書き方",
        "en": "How to write versions",
        "zh": "版本写法说明",
    },
    "confirm.pkg_count_resolved": {
        "ja": "インストールされるパッケージ（{n} 件・解決済みの全体）",
        "en": "Packages to install ({n} · full resolved set)",
        "zh": "将安装的软件包（{n} 个 · 已解析的完整列表）",
    },
    "confirm.pkg_count_declared": {
        "ja": "インストールされるパッケージ（{n} 件・直接指定のみ）",
        "en": "Packages to install ({n} · declared only)",
        "zh": "将安装的软件包（{n} 个 · 仅直接声明）",
    },
    "confirm.no_extra_pkgs": {
        "ja": "（追加パッケージなし）",
        "en": "(no extra packages)",
        "zh": "（无额外软件包）",
    },
    "confirm.unlisted_tag": {
        "ja": "  — 許可リスト外",
        "en": "  — not on allow list",
        "zh": "  — 不在许可列表中",
    },
    "confirm.warn_prefix": {"ja": "警告: ", "en": "Warning: ", "zh": "警告："},
    # generic dialog titles / buttons
    "dlg.error": {"ja": "エラー", "en": "Error", "zh": "错误"},
    "dlg.notice": {"ja": "お知らせ", "en": "Notice", "zh": "提示"},
    "dlg.select_app": {
        "ja": "一覧からアプリを選んでください",
        "en": "Please select an app from the list",
        "zh": "请从列表中选择一个应用",
    },
    "dlg.add_row": {"ja": "行を追加", "en": "Add row", "zh": "添加行"},
    "dlg.del_row": {"ja": "行を削除", "en": "Delete row", "zh": "删除行"},
    "dlg.select_all": {"ja": "全選択", "en": "Select all", "zh": "全选"},
    "dlg.paste": {"ja": "貼り付け", "en": "Paste", "zh": "粘贴"},
    "dlg.copy": {"ja": "コピー", "en": "Copy", "zh": "复制"},
    "dlg.clear_all": {"ja": "全消去", "en": "Clear all", "zh": "清空"},
    # shortcut
    "shortcut.offer_title": {
        "ja": "ショートカットを作りますか？",
        "en": "Create a desktop shortcut?",
        "zh": "要创建桌面快捷方式吗？",
    },
    "shortcut.win_title": {
        "ja": "デスクトップのショートカット",
        "en": "Desktop shortcut",
        "zh": "桌面快捷方式",
    },
    "shortcut.make_now": {
        "ja": "ショートカットを作成します",
        "en": "Create a shortcut",
        "zh": "创建快捷方式",
    },
    "shortcut.pick_icon": {"ja": "アイコンを選ぶ", "en": "Choose an icon", "zh": "选择图标"},
    "shortcut.pick_icon_hint": {
        "ja": "サンプルをタップして色を変えられます。アプリ内の画像やファイルからも選べます。",
        "en": "Tap a sample and change its color. You can also pick an image from the app or a file.",
        "zh": "点选示例并可改色。也可从应用内或文件选择图片。",
    },
    "shortcut.default_icon": {"ja": "既定のアイコン", "en": "Default icon", "zh": "默认图标"},
    "shortcut.samples": {
        "ja": "サンプル",
        "en": "Samples",
        "zh": "示例",
    },
    "shortcut.color": {"ja": "色:", "en": "Color:", "zh": "颜色："},
    "shortcut.color1": {"ja": "背景色", "en": "Background", "zh": "背景色"},
    "shortcut.color2": {"ja": "図柄色", "en": "Glyph", "zh": "图案色"},
    "shortcut.custom": {"ja": "自由…", "en": "More…", "zh": "自选…"},
    "shortcut.custom_color": {
        "ja": "自由に色を選ぶ",
        "en": "Choose a custom color",
        "zh": "自定义颜色",
    },
    "shortcut.inapp_file": {"ja": "アプリ内 / ファイル", "en": "In-app / file", "zh": "应用内 / 文件"},
    "shortcut.no_images": {
        "ja": "アプリの中に使えそうな画像は見つかりませんでした。",
        "en": "No usable images were found inside the app.",
        "zh": "在应用内未找到可用的图片。",
    },
    "shortcut.pick_file": {"ja": "アイコンを選択", "en": "Choose an icon", "zh": "选择图标"},
    "shortcut.icon_images": {"ja": "アイコン画像", "en": "Icon images", "zh": "图标图片"},
    "shortcut.pick_from_file": {"ja": "ファイルから選ぶ…", "en": "Choose from file…", "zh": "从文件选择…"},
    "shortcut.paste": {"ja": "画像を貼り付け", "en": "Paste image", "zh": "粘贴图片"},
    "shortcut.paste_hint": {
        "ja": "スクリーンショットをコピー後、Ctrl+V でも貼り付けできます。",
        "en": "Copy a screenshot, then press Ctrl+V to paste it.",
        "zh": "复制截图后，也可按 Ctrl+V 粘贴。",
    },
    "shortcut.paste_title": {
        "ja": "画像の貼り付け",
        "en": "Paste image",
        "zh": "粘贴图片",
    },
    "shortcut.paste_failed": {
        "ja": "画像を貼り付けられませんでした。\n{e}",
        "en": "Could not paste an image.\n{e}",
        "zh": "无法粘贴图片。\n{e}",
    },
    "shortcut.preview": {"ja": "プレビュー", "en": "Preview", "zh": "预览"},
    "shortcut.none": {"ja": "（なし）", "en": "(none)", "zh": "（无）"},
    "shortcut.default_short": {"ja": "既定", "en": "Default", "zh": "默认"},
    "shortcut.icon_err": {"ja": "アイコン", "en": "Icon", "zh": "图标"},
    "shortcut.create": {"ja": "作成する", "en": "Create", "zh": "创建"},
    "shortcut.later": {"ja": "あとで", "en": "Later", "zh": "以后"},
    "shortcut.done_body": {
        "ja": "デスクトップに作成しました:\n{lnk}\n\n"
        "うまく起動しないときは、作り直すと直ることがあります。\n"
        "ログ: %LOCALAPPDATA%\\uvdrop\\launchers\\run-{key}.log",
        "en": "Created on the desktop:\n{lnk}\n\n"
        "If it does not launch, recreating it sometimes helps.\n"
        "Log: %LOCALAPPDATA%\\uvdrop\\launchers\\run-{key}.log",
        "zh": "已在桌面创建：\n{lnk}\n\n"
        "若无法启动，重新创建有时可解决。\n"
        "日志：%LOCALAPPDATA%\\uvdrop\\launchers\\run-{key}.log",
    },
    "shortcut.bypass_note": {
        "ja": "※ ショートカットからの起動は、この確認画面を表示せずに"
        "（前回と同じ設定で）すぐ実行します。ブロック対象だけは毎回止めます。",
        "en": "Note: launching from a shortcut runs immediately without this "
        "review (same setup as before). Only blocked packages still stop it.",
        "zh": "注意：通过快捷方式启动会直接运行，不再显示此确认界面"
        "（沿用上次设置）。仅被禁止的软件包仍会被拦截。",
    },
    # settings extra
    "settings.q_guard": {"ja": "実行前の確認", "en": "Before running", "zh": "运行前确认"},
    "settings.q_console": {"ja": "コンソール窓", "en": "Console window", "zh": "控制台窗口"},
    "settings.mode_label": {"ja": "未許可時:", "en": "If not allowed:", "zh": "未许可时："},
    "settings.file_import": {
        "ja": "Excel / CSV からも取り込む",
        "en": "Also import from Excel / CSV",
        "zh": "同时从 Excel / CSV 导入",
    },
    "settings.browse": {"ja": "参照…", "en": "Browse…", "zh": "浏览…"},
    "settings.file_pick_title": {
        "ja": "許可リスト（Excel / CSV）",
        "en": "Allow list (Excel / CSV)",
        "zh": "许可列表（Excel / CSV）",
    },
    "settings.badver_title": {
        "ja": "バージョン規則を確認してください",
        "en": "Please check the version rules",
        "zh": "请检查版本规则",
    },
    "settings.badver_body": {
        "ja": "次の行は uvdrop が判定できない書き方です。\nこのまま保存すると、その行はチェックに使われません。\n\n{list}{extra}\n\nこのまま保存しますか？",
        "en": "uvdrop cannot interpret these rows.\nIf you save now, those rows will not be used for checks.\n\n{list}{extra}\n\nSave anyway?",
        "zh": "uvdrop 无法解析以下行。\n若现在保存，这些行将不会用于检查。\n\n{list}{extra}\n\n仍要保存吗？",
    },
    "settings.badver_more": {
        "ja": "\n…ほか {n} 件",
        "en": "\n… and {n} more",
        "zh": "\n……另有 {n} 项",
    },
    # usage
    "usage.title": {"ja": "使用状況", "en": "Usage", "zh": "使用情况"},
    "usage.scope": {"ja": "対象", "en": "Scope", "zh": "范围"},
    "usage.scope_all": {"ja": "すべてのアプリ", "en": "All apps", "zh": "全部应用"},
    "usage.unit": {"ja": "単位", "en": "Unit", "zh": "单位"},
    "usage.daily": {"ja": "日ごと", "en": "Daily", "zh": "按天"},
    "usage.weekly": {"ja": "週ごと", "en": "Weekly", "zh": "按周"},
    "usage.monthly": {"ja": "月ごと", "en": "Monthly", "zh": "按月"},
    "usage.summary": {
        "ja": "{scope}: 直近{unit}で {total} 回起動",
        "en": "{scope}: {total} runs in the last {unit}",
        "zh": "{scope}：最近{unit}共启动 {total} 次",
    },
    "usage.u_day": {"ja": "30日", "en": "30 days", "zh": "30 天"},
    "usage.u_week": {"ja": "16週", "en": "16 weeks", "zh": "16 周"},
    "usage.u_month": {"ja": "12か月", "en": "12 months", "zh": "12 个月"},
    "usage.no_data": {
        "ja": "この期間の起動記録はありません",
        "en": "No runs recorded for this period",
        "zh": "此期间没有启动记录",
    },
    "usage.tip_total": {
        "ja": "合計 {n} 回",
        "en": "{n} runs total",
        "zh": "共 {n} 次",
    },
    "usage.tip_part": {
        "ja": "・{name}: {n} 回",
        "en": "· {name}: {n}",
        "zh": "· {name}：{n} 次",
    },
    # help windows (multi-line)
    "help.title": {"ja": "ヘルプ", "en": "Help", "zh": "帮助"},
    "help.body": {
        "ja": (
            "uvdrop — フォルダ / ZIP を渡すと、uv で仮想環境を作ってアプリを起動します。\n\n"
            "【操作の流れ】\n"
            "  1. 「フォルダ」「ZIP」、または「カタログから開く」を選ぶ（初めてなら「サンプルで試す」）\n"
            "  2. インストールされるパッケージを確認して実行\n"
            "  3. 起動したアプリは一覧に残ります（不要になったら削除）\n\n"
            "【共有カタログ】\n"
            "  設定 → カタログ に共有の uvdrop-catalog.json を登録すると、一覧から起動できます。\n"
            "  フォルダの自動走査はしません。実行前の確認・許可リストは通常どおりです。\n"
            "  詳細は docs/CATALOG.md。\n\n"
            "【必要なファイル構成】\n"
            "  必須\n"
            "    · pyproject.toml\n"
            "    · 起動エントリ（main.py / app.py / run.py、または manifest / scripts）\n\n"
            "  例\n"
            "    my-app/\n"
            "      pyproject.toml\n"
            "      main.py\n\n"
            "  requirements.txt しかない場合\n"
            "    設定 → ガード で「requirements.txt からの変換を許可する」をオンにすると、\n"
            "    最小の pyproject.toml を自動生成して起動を試みます（既定はオン）。\n"
            "    変換は簡易的なので、動かないプロジェクトもあります。\n\n"
            "  ZIP も同じ構成。トップがフォルダ1つなら展開時にまとめます。\n"
            "  .venv / .git は取り込みません。.env は uvdrop が別管理します。\n\n"
            "【uv の優先順位】\n"
            "  1. 同梱 uv.exe（開発: resources/tools/… 、インストール後: tools/uv.exe）\n"
            "  2. 無いときだけ PATH の uv\n"
            "  ※ ステータスバーに [同梱|PATH] と版が出ます\n\n"
            "【データ】 %LOCALAPPDATA%\\uvdrop\\\n"
            "  apps / envs / dotenv / policies / settings.json"
        ),
        "en": (
            "uvdrop — pass a folder or ZIP and it builds an environment with uv, "
            "then runs the app.\n\n"
            "How it works\n"
            "  1. Choose “folder”, “ZIP”, or “Open from catalog” (or “Try a sample” the first time)\n"
            "  2. Review the packages to install, then run\n"
            "  3. Apps you run stay in the list (delete when no longer needed)\n\n"
            "Shared catalogs\n"
            "  In Settings → Catalogs, register a shared uvdrop-catalog.json to launch from a list.\n"
            "  Folders are not auto-scanned. Review / allow / block lists still apply.\n"
            "  See docs/CATALOG.md.\n\n"
            "Required files\n"
            "  Required\n"
            "    · pyproject.toml\n"
            "    · an entry point (main.py / app.py / run.py, or manifest / scripts)\n\n"
            "  Example\n"
            "    my-app/\n"
            "      pyproject.toml\n"
            "      main.py\n\n"
            "  If you only have requirements.txt\n"
            "    In Settings → Guard, turn on “Allow converting from requirements.txt”\n"
            "    (on by default). uvdrop will generate a minimal pyproject.toml and try to run.\n"
            "    Conversion is best-effort — some projects may not work.\n\n"
            "  ZIP uses the same layout. If the top is a single folder, it is flattened "
            "on extract.\n"
            "  .venv / .git are not imported. uvdrop manages .env separately.\n\n"
            "Which uv is used\n"
            "  1. Bundled uv.exe (dev: resources/tools/… , installed: tools/uv.exe)\n"
            "  2. Otherwise the uv on PATH\n"
            "  Note: the status bar shows [bundled|PATH] and the version\n\n"
            "Data folder: %LOCALAPPDATA%\\uvdrop\\\n"
            "  apps / envs / dotenv / policies / settings.json"
        ),
        "zh": (
            "uvdrop — 传入文件夹或 ZIP，它会用 uv 创建环境并启动应用。\n\n"
            "使用流程\n"
            "  1. 选择“文件夹”“ZIP”或“从目录打开”（首次可用“试用示例”）\n"
            "  2. 确认将安装的软件包，然后运行\n"
            "  3. 启动过的应用会保留在列表中（不需要时删除）\n\n"
            "共享目录\n"
            "  在 设置 → 目录 中注册共享的 uvdrop-catalog.json，即可从列表启动。\n"
            "  不会自动扫描文件夹。运行前确认与许可/禁止列表照常生效。\n"
            "  详见 docs/CATALOG.md。\n\n"
            "所需文件结构\n"
            "  必需\n"
            "    · pyproject.toml\n"
            "    · 启动入口（main.py / app.py / run.py，或 manifest / scripts）\n\n"
            "  示例\n"
            "    my-app/\n"
            "      pyproject.toml\n"
            "      main.py\n\n"
            "  只有 requirements.txt 时\n"
            "    在 设置 → 防护 中开启“允许从 requirements.txt 转换”（默认开启），\n"
            "    uvdrop 会生成最小的 pyproject.toml 并尝试运行。\n"
            "    转换为尽力而为，部分项目可能无法运行。\n\n"
            "  ZIP 采用相同结构。若顶层只有一个文件夹，解压时会自动展平。\n"
            "  不会导入 .venv / .git。uvdrop 会单独管理 .env。\n\n"
            "uv 的优先级\n"
            "  1. 随附的 uv.exe（开发：resources/tools/…；安装后：tools/uv.exe）\n"
            "  2. 否则使用 PATH 中的 uv\n"
            "  注：状态栏会显示 [随附|PATH] 及版本\n\n"
            "数据目录：%LOCALAPPDATA%\\uvdrop\\\n"
            "  apps / envs / dotenv / policies / settings.json"
        ),
    },
    "help.format_title": {
        "ja": "必要なファイル構成",
        "en": "Required files",
        "zh": "所需文件结构",
    },
    "help.format_body": {
        "ja": (
            "必須\n"
            "  · pyproject.toml\n"
            "  · 起動エントリ（main.py / app.py / run.py、または manifest / scripts）\n\n"
            "例\n"
            "  my-app/\n"
            "    pyproject.toml\n"
            "    main.py\n\n"
            "requirements.txt しかない場合は、設定 → ガード の\n"
            "「requirements.txt からの変換を許可する」をオンにすると変換して起動を試みます"
            "（既定はオン）。変換は簡易的なので動かないこともあります。\n\n"
            "ZIP も同じ構成。トップがフォルダ1つなら展開時にまとめます。\n"
            ".venv / .git は取り込みません。.env は uvdrop が別管理します。"
        ),
        "en": (
            "Required\n"
            "  · pyproject.toml\n"
            "  · an entry point (main.py / app.py / run.py, or manifest / scripts)\n\n"
            "Example\n"
            "  my-app/\n"
            "    pyproject.toml\n"
            "    main.py\n\n"
            "If you only have requirements.txt, turn on “Allow converting from "
            "requirements.txt” under Settings → Guard (on by default). Conversion is "
            "best-effort and may not work.\n\n"
            "ZIP uses the same layout. If the top is a single folder, it is flattened "
            "on extract.\n"
            ".venv / .git are not imported. uvdrop manages .env separately."
        ),
        "zh": (
            "必需\n"
            "  · pyproject.toml\n"
            "  · 启动入口（main.py / app.py / run.py，或 manifest / scripts）\n\n"
            "示例\n"
            "  my-app/\n"
            "    pyproject.toml\n"
            "    main.py\n\n"
            "只有 requirements.txt 时，请在 设置 → 防护 中开启“允许从 "
            "requirements.txt 转换”（默认开启）。转换为尽力而为，可能无法运行。\n\n"
            "ZIP 采用相同结构。若顶层只有一个文件夹，解压时会自动展平。\n"
            "不会导入 .venv / .git。uvdrop 会单独管理 .env。"
        ),
    },
    "help.xlsx": {
        "ja": (
            "Excel（.xlsx）または CSV の URL / ローカルパスから、許可パッケージを取り込みます。\n"
            "A 列 = パッケージ名、B 列 = バージョン規則（空または * で全部OK）。\n"
            "例: 1.*  /  >=1.0,<2  /  ==2.31.0"
        ),
        "en": (
            "Import allowed packages from an Excel (.xlsx) or CSV file (URL or local path).\n"
            "Column A = package name, Column B = version rule (empty or * means any).\n"
            "e.g. 1.*  /  >=1.0,<2  /  ==2.31.0"
        ),
        "zh": (
            "从 Excel（.xlsx）或 CSV 的网址 / 本地路径导入许可的软件包。\n"
            "A 列 = 软件包名称，B 列 = 版本规则（留空或 * 表示全部允许）。\n"
            "例如：1.*  /  >=1.0,<2  /  ==2.31.0"
        ),
    },
    "help.manual_allow": {
        "ja": (
            "表計算のように編集できます。セルをクリック（またはダブルクリック）して入力、\n"
            "Tab で右のセル、Enter で下の行へ進みます。\n"
            "Excel から A列=パッケージ名 / B列=バージョンをコピーし、Ctrl+V で貼り付け\n"
            "（足りない行は自動追加。Ctrl+A 全選択 / Ctrl+C コピー / Shift・Ctrl で複数選択）。\n"
            "バージョンは空または * で全部OK。例: 1.*  /  >=1.0,<2  /  ==2.31.0\n"
            "変更はウィンドウ下の「保存して閉じる」で反映されます。\n"
            "Excel/CSV 取り込みや allowlist.json がある場合は和集合でマージします。"
        ),
        "en": (
            "Edit it like a spreadsheet. Click (or double-click) a cell to type,\n"
            "Tab moves right, Enter moves to the next row.\n"
            "Copy column A = name / column B = version from Excel and paste with Ctrl+V\n"
            "(missing rows are added automatically; Ctrl+A select all / Ctrl+C copy / "
            "Shift・Ctrl multi-select).\n"
            "Version empty or * means any. e.g. 1.*  /  >=1.0,<2  /  ==2.31.0\n"
            "Changes take effect when you press “Save and close” below.\n"
            "If an Excel/CSV import or allowlist.json exists, they are merged (union)."
        ),
        "zh": (
            "可像电子表格一样编辑。单击（或双击）单元格输入，\n"
            "Tab 移到右侧，Enter 移到下一行。\n"
            "从 Excel 复制 A 列=名称 / B 列=版本，用 Ctrl+V 粘贴\n"
            "（不足的行会自动添加；Ctrl+A 全选 / Ctrl+C 复制 / Shift·Ctrl 多选）。\n"
            "版本留空或 * 表示全部允许。例如：1.*  /  >=1.0,<2  /  ==2.31.0\n"
            "更改在点击下方“保存并关闭”后生效。\n"
            "若存在 Excel/CSV 导入或 allowlist.json，将合并（并集）。"
        ),
    },
    "help.block": {
        "ja": (
            "ここに載っているパッケージは、見つかった時点で常にブロックします。"
            "バージョン規則も書けます（空/* なら名前一致で即ブロック）。"
        ),
        "en": (
            "Packages listed here are always blocked as soon as they appear. "
            "You can add version rules too (empty/* blocks on a name match)."
        ),
        "zh": (
            "此处列出的软件包一经发现即被阻止。"
            "也可写版本规则（留空/* 表示按名称匹配即阻止）。"
        ),
    },
    "help.proxy": {
        "ja": "プロキシ経由で PyPI / Excel・CSV に出るとき。例: http://proxy.example.com:8080",
        "en": "For reaching PyPI / Excel・CSV through a proxy. e.g. http://proxy.example.com:8080",
        "zh": "通过代理访问 PyPI / Excel·CSV 时使用。例如：http://proxy.example.com:8080",
    },
    "help.guard": {
        "ja": (
            "仮想環境を作る前に、これからインストールされるパッケージを一覧で確認します。"
            "許可リストが未設定でも、確認画面で内容を見てから実行できます。"
        ),
        "en": (
            "Before creating the environment, review the packages that will be installed. "
            "Even without an allow list, you can inspect everything before running."
        ),
        "zh": (
            "在创建环境之前，先以列表形式确认将要安装的软件包。"
            "即使未设置许可列表，也可在确认界面查看后再运行。"
        ),
    },
    "help.console": {
        "ja": (
            "オフ（推奨）: 起動時に黒いコンソール窓を出しません。\n"
            "オン: 新しいコンソールを開き、標準出力・標準エラーを表示します。"
            "print の確認やエラー調査に使えます。"
        ),
        "en": (
            "Off (recommended): no black console window when running.\n"
            "On: opens a new console showing standard output/error. "
            "Useful for checking print output or investigating errors."
        ),
        "zh": (
            "关闭（推荐）：运行时不显示黑色控制台窗口。\n"
            "开启：打开新的控制台，显示标准输出/错误。"
            "可用于查看 print 输出或排查错误。"
        ),
    },
    "help.shortcut": {
        "ja": (
            "デスクトップに .lnk を作ります。中身は uvdrop が用意した "
            "%LOCALAPPDATA%\\uvdrop\\launchers\\run-{key}.cmd を呼ぶだけのショートカットで、"
            "そこから同じ仮想環境・同じ起動コマンドでアプリを再実行します。"
            "uvdrop の画面を開かなくても起動でき、失敗したときは同じフォルダの "
            "run-{key}.log に記録が残ります。\n\n"
            "※ ショートカットからの起動は、この確認画面を出さずにすぐ実行します"
            "（ブロック対象だけは毎回止めます）。"
        ),
        "en": (
            "Creates a .lnk on the desktop. It simply calls "
            "%LOCALAPPDATA%\\uvdrop\\launchers\\run-{key}.cmd prepared by uvdrop, "
            "which re-runs the app with the same environment and start command. "
            "You can launch without opening uvdrop; on failure a log is kept at "
            "run-{key}.log in the same folder.\n\n"
            "Note: launching from a shortcut runs immediately without this review "
            "(only blocked packages still stop it)."
        ),
        "zh": (
            "在桌面创建 .lnk。它只是调用 uvdrop 生成的 "
            "%LOCALAPPDATA%\\uvdrop\\launchers\\run-{key}.cmd，"
            "以相同的环境和启动命令重新运行应用。"
            "无需打开 uvdrop 即可启动；失败时会在同一文件夹保留 run-{key}.log 日志。\n\n"
            "注意：通过快捷方式启动会直接运行，不显示此确认界面"
            "（仅被禁止的软件包仍会被拦截）。"
        ),
    },
    "help.requirements": {
        "ja": (
            "pyproject.toml が無いとき、requirements.txt から最小の pyproject.toml を作って uv に渡します。"
            "pip 専用の記述（-e、--index-url、直接の URL など）は落ちるため、そのままでは動かないことがあります。"
        ),
        "en": (
            "When there is no pyproject.toml, uvdrop builds a minimal one from "
            "requirements.txt and passes it to uv. pip-only lines (-e, --index-url, "
            "direct URLs, …) are dropped, so it may not run as-is."
        ),
        "zh": (
            "当没有 pyproject.toml 时，uvdrop 会根据 requirements.txt 生成最小的 "
            "pyproject.toml 交给 uv。pip 专用写法（-e、--index-url、直接 URL 等）会被丢弃，"
            "因此可能无法直接运行。"
        ),
    },
    "settings.tab_lang_title": {
        "ja": "表示言語",
        "en": "Language",
        "zh": "显示语言",
    },
    # delete / licenses / sample / misc dialogs
    "delete.confirm": {
        "ja": "アプリのデータごと削除しますか？\n{key}\n（ワークスペース / venv / .env）",
        "en": "Delete this app and all its data?\n{key}\n(workspace / venv / .env)",
        "zh": "要连同数据一起删除此应用吗？\n{key}\n（工作区 / venv / .env）",
    },
    "licenses.missing": {
        "ja": "THIRD_PARTY_NOTICES.md が見つかりません。",
        "en": "THIRD_PARTY_NOTICES.md was not found.",
        "zh": "未找到 THIRD_PARTY_NOTICES.md。",
    },
    "sample.title": {"ja": "サンプルで試す", "en": "Try a sample", "zh": "试用示例"},
    "sample.which": {"ja": "どれを試しますか？", "en": "Which one to try?", "zh": "试用哪一个？"},
    "sample.after": {
        "ja": "保存先を選んだあと、そのまま起動できます。",
        "en": "After choosing where to save, you can run it right away.",
        "zh": "选择保存位置后即可直接运行。",
    },
    "sample.format": {"ja": "形式:", "en": "Format:", "zh": "格式："},
    "sample.folder": {"ja": "フォルダ", "en": "Folder", "zh": "文件夹"},
    "sample.save_continue": {"ja": "保存して続ける", "en": "Save and continue", "zh": "保存并继续"},
    "sample.cancel": {"ja": "キャンセル", "en": "Cancel", "zh": "取消"},
    "sample.save_dir_title": {
        "ja": "サンプルの保存先（親フォルダ）",
        "en": "Where to save the sample (parent folder)",
        "zh": "示例的保存位置（父文件夹）",
    },
    "sample.save_zip_title": {
        "ja": "サンプル ZIP の保存先",
        "en": "Where to save the sample ZIP",
        "zh": "示例 ZIP 的保存位置",
    },
    "sample.saved_run": {
        "ja": "保存しました:\n{path}\n\n今すぐ起動しますか？",
        "en": "Saved:\n{path}\n\nRun it now?",
        "zh": "已保存：\n{path}\n\n现在运行吗？",
    },
    "status.bundled": {"ja": "同梱", "en": "bundled", "zh": "随附"},
    # package sheet
    "sheet.col_name": {"ja": "A  パッケージ名", "en": "A  Package", "zh": "A  软件包名"},
    "sheet.col_version": {"ja": "B  バージョン", "en": "B  Version", "zh": "B  版本"},
    "sheet.add_row": {"ja": "行を追加", "en": "Add row", "zh": "添加行"},
    "sheet.del_row": {"ja": "行を削除", "en": "Delete row", "zh": "删除行"},
    "sheet.select_all": {"ja": "全選択", "en": "Select all", "zh": "全选"},
    "sheet.paste": {"ja": "貼り付け", "en": "Paste", "zh": "粘贴"},
    "sheet.copy": {"ja": "コピー", "en": "Copy", "zh": "复制"},
    "sheet.clear_all": {"ja": "全消去", "en": "Clear all", "zh": "清空"},
    "sheet.version_guide": {
        "ja": "バージョンの書き方",
        "en": "How to write versions",
        "zh": "版本写法说明",
    },
    "sheet.hint": {
        "ja": "Excel から貼り付け可（A列=名前 / B列=バージョン）。空欄や * は全バージョンOK。",
        "en": "Paste from Excel (col A = name / col B = version). Empty or * means any version.",
        "zh": "可从 Excel 粘贴（A 列=名称 / B 列=版本）。留空或 * 表示任意版本。",
    },
    "sheet.bad_rules": {
        "ja": "読み取れないバージョン規則があります — {head}",
        "en": "Some version rules cannot be read — {head}",
        "zh": "有无法识别的版本规则 — {head}",
    },
    "sheet.bad_more": {
        "ja": "{first} ほか {n} 件",
        "en": "{first} and {n} more",
        "zh": "{first} 等 {n} 项",
    },
    "pick.folder_title": {
        "ja": "アプリフォルダを選択（pyproject.toml がある場所）",
        "en": "Choose an app folder (where pyproject.toml is)",
        "zh": "选择应用文件夹（pyproject.toml 所在处）",
    },
    "pick.zip_title": {
        "ja": "アプリ ZIP を選択",
        "en": "Choose an app ZIP",
        "zh": "选择应用 ZIP",
    },
    "settings.https_hint": {
        "ja": "HTTPS_PROXY（空なら HTTP）",
        "en": "HTTPS_PROXY (falls back to HTTP if empty)",
        "zh": "HTTPS_PROXY（留空则用 HTTP）",
    },
    # version rule messages (package_spec)
    "ver.note.epoch": {
        "ja": "{v} はエポック付き（1!2.0 形式）のため、数字だけでは比較できません",
        "en": "{v} has an epoch (like 1!2.0), so it cannot be compared by numbers alone",
        "zh": "{v} 带有 epoch（形如 1!2.0），无法仅凭数字比较",
    },
    "ver.note.local": {
        "ja": "{v} はローカル版（+ 以降）付きのため、数字だけでは比較できません",
        "en": "{v} has a local version (after +), so it cannot be compared by numbers alone",
        "zh": "{v} 带有本地版本（+ 之后），无法仅凭数字比较",
    },
    "ver.note.leading_v": {
        "ja": "{v} は先頭に v が付いています（1.2 のように数字だけで書いてください）",
        "en": "{v} starts with 'v' (write just the numbers, e.g. 1.2)",
        "zh": "{v} 以 v 开头（请只写数字，例如 1.2）",
    },
    "ver.note.pre_post_dev": {
        "ja": "{v} はプレリリース / post / dev 付きのため、数字だけでは比較できません",
        "en": "{v} is a pre-release / post / dev version, so it cannot be compared by numbers alone",
        "zh": "{v} 为预发布 / post / dev 版本，无法仅凭数字比较",
    },
    "ver.note.non_numeric": {
        "ja": "{v} は数字とドットだけの表記ではないため、正確に比較できません",
        "en": "{v} is not written only with digits and dots, so it cannot be compared exactly",
        "zh": "{v} 不是仅由数字和点组成，无法精确比较",
    },
    "ver.val.tilde": {
        "ja": "~= は未対応です。>=1.4,<2 のように書いてください",
        "en": "~= is not supported. Write it like >=1.4,<2",
        "zh": "不支持 ~=。请写成 >=1.4,<2",
    },
    "ver.val.triple_eq": {
        "ja": "=== は未対応です。== か完全一致の数字で書いてください",
        "en": "=== is not supported. Use == or an exact number",
        "zh": "不支持 ===。请用 == 或精确数字",
    },
    "ver.val.leading_v": {
        "ja": "先頭の v は不要です（1.2 のように書いてください）",
        "en": "Drop the leading 'v' (write it like 1.2)",
        "zh": "无需前导 v（请写成 1.2）",
    },
    "ver.val.op_wildcard": {
        "ja": "記号とワイルドカードは併用できません（1.* とだけ書いてください）",
        "en": "Operators and wildcards cannot be combined (write just 1.*)",
        "zh": "运算符与通配符不能混用（请只写 1.*）",
    },
    "ver.val.bad_wildcard": {
        "ja": "ワイルドカードは 1.* / 1.2.* のようにドット区切りで書いてください",
        "en": "Write wildcards dot-separated, like 1.* / 1.2.*",
        "zh": "通配符请用点分隔书写，如 1.* / 1.2.*",
    },
    "ver.val.need_numeric": {
        "ja": "数字とドット、または比較記号で書いてください",
        "en": "Write it with digits and dots, or with comparison operators",
        "zh": "请用数字和点，或比较运算符书写",
    },
    "ver.val.clause_unreadable": {
        "ja": "「{clause}」を読み取れません（例: >=1.0,<2）",
        "en": "Cannot read “{clause}” (e.g. >=1.0,<2)",
        "zh": "无法识别“{clause}”（例如 >=1.0,<2）",
    },
    "ver.val.clause_num_unreadable": {
        "ja": "「{clause}」の数字部分を読み取れません（例: >=1.0）",
        "en": "Cannot read the number in “{clause}” (e.g. >=1.0)",
        "zh": "无法识别“{clause}”中的数字（例如 >=1.0）",
    },
    "ver.desc.any": {"ja": "全バージョンOK", "en": "any version is allowed", "zh": "允许任意版本"},
    "ver.desc.prefix": {
        "ja": "{prefix}. で始まるバージョンだけOK",
        "en": "only versions starting with {prefix}.",
        "zh": "仅允许以 {prefix}. 开头的版本",
    },
    "ver.desc.exact": {
        "ja": "{r} と完全一致するものだけOK",
        "en": "only the exact version {r}",
        "zh": "仅允许与 {r} 完全一致的版本",
    },
    "ver.desc.compare": {
        "ja": "{clauses} バージョンだけOK",
        "en": "only versions where {clauses}",
        "zh": "仅允许满足 {clauses} 的版本",
    },
    "ver.desc.satisfy": {"ja": "{p} を満たす", "en": "{p}", "zh": "{p}"},
    "ver.desc.and": {"ja": " かつ ", "en": " and ", "zh": " 且 "},
    "ver.allow.mismatch": {
        "ja": "{name}=={ver} は許可規則 {rule} に合いません",
        "en": "{name}=={ver} does not match the allow rule {rule}",
        "zh": "{name}=={ver} 不符合许可规则 {rule}",
    },
    "ver.allow.open": {
        "ja": "{name} は版未確定のため名前のみ照合（許可規則: {rule}）",
        "en": "{name} has no fixed version, matched by name only (allow rule: {rule})",
        "zh": "{name} 版本未固定，仅按名称匹配（许可规则：{rule}）",
    },
    "ver.uncertain.rule_bad": {
        "ja": "{name}: 規則「{rule}」を判定できません — {msg}",
        "en": "{name}: cannot evaluate rule “{rule}” — {msg}",
        "zh": "{name}：无法判定规则“{rule}” — {msg}",
    },
    "ver.uncertain.approx": {
        "ja": "{name}: {note}（規則「{rule}」との照合は数字部分だけの概算です）",
        "en": "{name}: {note} (matching against rule “{rule}” uses only the numeric part)",
        "zh": "{name}：{note}（与规则“{rule}”的匹配仅使用数字部分，为近似）",
    },
    "ver.guide": {
        "ja": (
            "■ 基本の考え方\n"
            "  バージョンは「.（ドット）」区切りの数字で書きます（例: 2.31.0）。\n"
            "  数字の位は左から 「メジャー.マイナー.パッチ」 の順です。\n"
            "  * （アスタリスク）は「その位はどんな数字でもよい」というワイルドカードです。\n\n"
            "■ 書き方と意味\n"
            "  （空欄）   … そのパッケージなら全バージョンOK（* と同じ）\n"
            "  *          … 全バージョンOK\n"
            "  2.*        … メジャーが 2 なら全部OK（2.0.0 / 2.31.4 など）\n"
            "  2.*.*      … 2.* と同じ意味（位を明示しただけ）\n"
            "  0.0.*      … 0.0. で始まるものだけOK（0.0.1 はOK、0.1.0 はNG）\n"
            "  1.2.*      … 1.2. で始まるものだけOK\n"
            "  2.31.0     … 完全一致のみOK\n"
            "  >=1.0      … 1.0 以上ならOK\n"
            "  <2         … 2 未満ならOK\n"
            "  >=1.0,<2   … カンマは「かつ（AND）」。1.0 以上かつ 2 未満\n"
            "  使える記号: >=  >  <=  <  ==  !=\n\n"
            "■ 判定のしかた\n"
            "  ワイルドカードは「位ごとの一致」で判定します（文字列の前方一致ではありません）。\n"
            "  比較記号は数字の位ごとに比べます。足りない位は 0 とみなします（1.0 は 1.0.0 と同じ）。\n\n"
            "■ バージョン表記は PyPI の登録内容しだいです\n"
            "  実際のバージョン文字列は、そのパッケージを PyPI に公開した人が決めています。\n"
            "  そのため、数字だけで並べられない書き方が混ざることがあります。\n"
            "    2.0.0rc1 / 1.0b2   … プレリリース（正式版より前）\n"
            "    1.0.post1          … ポストリリース\n"
            "    1.0.dev0           … 開発版\n"
            "    1.0+cu118          … ローカル版（環境ごとのビルド）\n"
            "    1!2.0              … エポック（バージョン体系の作り直し）\n"
            "  uvdrop はこれらを数字部分だけに丸めて比べるため、正確に判定できません。\n"
            "  該当したときは黙って通さず、実行前の確認画面で「判定できない表記」として知らせます。\n\n"
            "■ 対応していない書き方\n"
            "  ~=1.4      … 互換リリース指定（>=1.4,<2 のように書き換えてください）\n"
            "  ==1.*      … 記号とワイルドカードの併用（1.* とだけ書いてください）\n"
            "  ===1.0     … 任意一致\n"
            "  v1.2       … 先頭の v は不要（1.2 と書いてください）"
        ),
        "en": (
            "■ The basics\n"
            "  Versions are digits separated by '.' (dots), e.g. 2.31.0.\n"
            "  From the left the positions are major.minor.patch.\n"
            "  * (asterisk) is a wildcard meaning 'any number in this position'.\n\n"
            "■ Notation and meaning\n"
            "  (empty)    … any version of that package (same as *)\n"
            "  *          … any version\n"
            "  2.*        … any version whose major is 2 (2.0.0 / 2.31.4 …)\n"
            "  2.*.*      … same meaning as 2.* (positions just spelled out)\n"
            "  0.0.*      … only those starting with 0.0. (0.0.1 yes, 0.1.0 no)\n"
            "  1.2.*      … only those starting with 1.2.\n"
            "  2.31.0     … exact match only\n"
            "  >=1.0      … 1.0 or newer\n"
            "  <2         … below 2\n"
            "  >=1.0,<2   … a comma means AND: 1.0 or newer and below 2\n"
            "  Usable operators: >=  >  <=  <  ==  !=\n\n"
            "■ How matching works\n"
            "  Wildcards match position by position (not string prefix).\n"
            "  Operators compare each numeric position; missing positions are 0 "
            "(1.0 equals 1.0.0).\n\n"
            "■ Version text depends on what is published to PyPI\n"
            "  The actual version string is decided by whoever published the package.\n"
            "  So some notations cannot be ordered by numbers alone:\n"
            "    2.0.0rc1 / 1.0b2   … pre-release (before the final)\n"
            "    1.0.post1          … post-release\n"
            "    1.0.dev0           … development\n"
            "    1.0+cu118          … local version (per-environment build)\n"
            "    1!2.0              … epoch (versioning restarted)\n"
            "  uvdrop rounds these to their numeric part, so it cannot judge them exactly.\n"
            "  When that happens it does not silently allow them — the review dialog shows "
            "them as 'notations we cannot judge'.\n\n"
            "■ Notations that are not supported\n"
            "  ~=1.4      … compatible release (rewrite as >=1.4,<2)\n"
            "  ==1.*      … operator + wildcard together (write just 1.*)\n"
            "  ===1.0     … arbitrary equality\n"
            "  v1.2       … no leading v (write 1.2)"
        ),
        "zh": (
            "■ 基本概念\n"
            "  版本用“.”（点）分隔的数字书写（例如 2.31.0）。\n"
            "  从左到右依次是 主版本.次版本.修订号。\n"
            "  *（星号）是通配符，表示“该位可为任意数字”。\n\n"
            "■ 写法与含义\n"
            "  （留空）   … 该软件包的任意版本（等同于 *）\n"
            "  *          … 任意版本\n"
            "  2.*        … 主版本为 2 的全部（2.0.0 / 2.31.4 等）\n"
            "  2.*.*      … 与 2.* 含义相同（只是写全了位）\n"
            "  0.0.*      … 仅以 0.0. 开头（0.0.1 可以，0.1.0 不行）\n"
            "  1.2.*      … 仅以 1.2. 开头\n"
            "  2.31.0     … 仅完全一致\n"
            "  >=1.0      … 1.0 及以上\n"
            "  <2         … 低于 2\n"
            "  >=1.0,<2   … 逗号表示“且(AND)”：1.0 及以上且低于 2\n"
            "  可用符号：>=  >  <=  <  ==  !=\n\n"
            "■ 匹配方式\n"
            "  通配符按位匹配（不是字符串前缀匹配）。\n"
            "  比较符号按数字位比较；缺失的位视为 0（1.0 等于 1.0.0）。\n\n"
            "■ 版本写法取决于 PyPI 上的登记内容\n"
            "  实际的版本字符串由发布该软件包的人决定。\n"
            "  因此可能混入无法仅凭数字排序的写法：\n"
            "    2.0.0rc1 / 1.0b2   … 预发布（正式版之前）\n"
            "    1.0.post1          … 后发布\n"
            "    1.0.dev0           … 开发版\n"
            "    1.0+cu118          … 本地版本（按环境构建）\n"
            "    1!2.0              … epoch（版本体系重启）\n"
            "  uvdrop 会将其舍入到数字部分再比较，因此无法精确判断。\n"
            "  遇到这种情况不会默默放行，而会在运行前确认界面标为“无法判断的写法”。\n\n"
            "■ 不支持的写法\n"
            "  ~=1.4      … 兼容发布（请改写为 >=1.4,<2）\n"
            "  ==1.*      … 符号与通配符混用（请只写 1.*）\n"
            "  ===1.0     … 任意相等\n"
            "  v1.2       … 无需前导 v（请写 1.2）"
        ),
    },
    # policy evaluation messages
    "pol.file_fetch_fail": {
        "ja": "許可リストファイルの取得に失敗: {e}",
        "en": "Failed to fetch the allow-list file: {e}",
        "zh": "获取许可列表文件失败：{e}",
    },
    "pol.resolved_note": {
        "ja": "インストール前に解決したパッケージ {n} 件を照合しています（直接指定＋あわせて入るもの）",
        "en": "Checking {n} packages resolved before install (declared + everything pulled in)",
        "zh": "正在核对安装前解析出的 {n} 个软件包（直接声明 + 一并引入的）",
    },
    "pol.declared_note": {
        "ja": "pyproject.toml に書かれたパッケージのみを照合しています（あわせて入るものは未確認）",
        "en": "Checking only packages written in pyproject.toml (pulled-in ones not verified)",
        "zh": "仅核对 pyproject.toml 中写明的软件包（一并引入的未核实）",
    },
    "pol.block_hit": {
        "ja": "NG リストに該当: {name}",
        "en": "On the block list: {name}",
        "zh": "命中禁止列表：{name}",
    },
    "pol.block_hit_rule": {
        "ja": "NG リストに該当: {name}（規則 {rule}）",
        "en": "On the block list: {name} (rule {rule})",
        "zh": "命中禁止列表：{name}（规则 {rule}）",
    },
    "pol.unresolved_ng": {
        "ja": "NGリスト — {note}",
        "en": "Block list — {note}",
        "zh": "禁止列表 — {note}",
    },
    "pol.no_allowlist_note": {
        "ja": "許可リストは未設定です（すべてのパッケージが通ります）",
        "en": "No allow list is set (every package passes)",
        "zh": "未设置许可列表（所有软件包均通过）",
    },
    "pol.allow_count_note": {
        "ja": "許可リスト {n} 件と照合しました（未許可時: {mode}）",
        "en": "Checked against {n} allow-list entries (if not allowed: {mode})",
        "zh": "已与 {n} 条许可列表核对（未许可时：{mode}）",
    },
    "pol.unresolved_allow_rule": {
        "ja": "許可リスト — {name}: 規則「{rule}」{msg}",
        "en": "Allow list — {name}: rule “{rule}” {msg}",
        "zh": "许可列表 — {name}：规则“{rule}”{msg}",
    },
    "pol.not_listed": {
        "ja": "許可リストにありません: {name}",
        "en": "Not on the allow list: {name}",
        "zh": "不在许可列表中：{name}",
    },
    "pol.unresolved_allow": {
        "ja": "許可リスト — {note}",
        "en": "Allow list — {note}",
        "zh": "许可列表 — {note}",
    },
    "pol.version_out": {
        "ja": "版が許可規則外: {name}",
        "en": "Version outside the allow rule: {name}",
        "zh": "版本超出许可规则：{name}",
    },
    "pol.all_allowed": {
        "ja": "依存パッケージはすべて許可リスト内です",
        "en": "All dependencies are on the allow list",
        "zh": "所有依赖都在许可列表中",
    },
    "pol.resolve_failed": {
        "ja": "依存関係の全体解決に失敗したため、pyproject.toml に書かれたパッケージだけを確認しました。詳細: {err}",
        "en": "Could not resolve the full dependency tree, so only packages written in "
        "pyproject.toml were checked. Details: {err}",
        "zh": "无法解析完整依赖树，因此仅检查了 pyproject.toml 中写明的软件包。详情：{err}",
    },
    "pol.block_needs_resolve": {
        "ja": "許可リストが「未許可はブロック」設定ですが、依存関係の全体を確認できませんでした。"
        "確認できないパッケージが入る可能性があるため、安全のため実行を中止します。",
        "en": "The allow list is set to block anything not allowed, but the full dependency "
        "tree could not be verified. Unverified packages might be installed, so the run is "
        "stopped for safety.",
        "zh": "许可列表设为“未许可即阻止”，但无法核实完整依赖树。"
        "可能会安装未核实的软件包，为安全起见已中止运行。",
    },
    "cli.needs_confirm": {
        "ja": "この起動には確認が必要です（許可リスト未設定、警告、または確認設定がオン）。\n"
        "GUI から起動するか、環境変数 UVDROP_ASSUME_YES=1 を付けてください。",
        "en": "This launch needs confirmation (no allow list, warnings, or confirm setting is on).\n"
        "Launch from the GUI, or set the environment variable UVDROP_ASSUME_YES=1.",
        "zh": "此次启动需要确认（未设置许可列表、有警告或已开启确认设置）。\n"
        "请从 GUI 启动，或设置环境变量 UVDROP_ASSUME_YES=1。",
    },
    "err.no_command": {
        "ja": "起動コマンドが指定されていません。確認画面で実行するファイルを入力してください。",
        "en": "No start command was given. Enter the file to run in the review dialog.",
        "zh": "未指定启动命令。请在确认界面中输入要运行的文件。",
    },
    "launch.zip_bad_path": {
        "ja": "ZIP に不正なパスが含まれています: {name}",
        "en": "The ZIP contains an unsafe path: {name}",
        "zh": "ZIP 中包含不安全的路径：{name}",
    },
    "uv.not_found": {
        "ja": "uv.exe が見つかりません。\n"
        "優先1: 同梱 resources/tools/windows-x64/uv.exe（またはインストール先 tools/uv.exe）\n"
        "優先2: PATH 上の uv\n"
        "どちらかを用意してください。",
        "en": "uv.exe was not found.\n"
        "Priority 1: bundled resources/tools/windows-x64/uv.exe (or tools/uv.exe when installed)\n"
        "Priority 2: uv on PATH\n"
        "Please provide one of them.",
        "zh": "未找到 uv.exe。\n"
        "优先级 1：随附的 resources/tools/windows-x64/uv.exe（或安装后的 tools/uv.exe）\n"
        "优先级 2：PATH 中的 uv\n"
        "请提供其中之一。",
    },
    "project.no_entry": {
        "ja": "起動できるファイルが見つかりません: {root}\n"
        "main.py などを置くか、起動コマンドを直接指定してください。",
        "en": "No runnable file was found: {root}\n"
        "Add a main.py (etc.) or specify the start command directly.",
        "zh": "未找到可运行的文件：{root}\n"
        "请放置 main.py 等，或直接指定启动命令。",
    },
    "project.empty_command": {
        "ja": "起動コマンドが空です",
        "en": "The start command is empty",
        "zh": "启动命令为空",
    },
    # shortcut icon themes / colors
    "theme.office": {"ja": "OA・事務", "en": "Office", "zh": "办公・事务"},
    "theme.chart": {"ja": "計測・解析", "en": "Measure・Analyze", "zh": "测量・分析"},
    "theme.tool": {"ja": "ツール", "en": "Tool", "zh": "工具"},
    "theme.lab": {"ja": "実験・研究", "en": "Lab・Research", "zh": "实验・研究"},
    "theme.bolt": {"ja": "稲妻", "en": "Bolt", "zh": "闪电"},
    "theme.box": {"ja": "荷物", "en": "Package", "zh": "包裹"},
    "theme.nodes": {"ja": "つながる", "en": "Network", "zh": "联网"},
    "theme.rocket": {"ja": "ロケット", "en": "Rocket", "zh": "火箭"},
    "color.forest": {"ja": "フォレスト", "en": "Forest", "zh": "森林绿"},
    "color.blue": {"ja": "ブルー", "en": "Blue", "zh": "蓝色"},
    "color.amber": {"ja": "アンバー", "en": "Amber", "zh": "琥珀"},
    "color.rose": {"ja": "ローズ", "en": "Rose", "zh": "玫红"},
    "color.slate": {"ja": "スレート", "en": "Slate", "zh": "石板灰"},
    "color.teal": {"ja": "ティール", "en": "Teal", "zh": "青色"},
    "delete.done": {
        "ja": "削除しました: {key}",
        "en": "Deleted: {key}",
        "zh": "已删除：{key}",
    },
    "delete.failed": {
        "ja": "削除に失敗しました: {e}",
        "en": "Could not delete: {e}",
        "zh": "删除失败：{e}",
    },
    "xlsx.load_fail": {
        "ja": "許可リストの読み込みに失敗: {e}",
        "en": "Failed to load the allow list: {e}",
        "zh": "加载许可列表失败：{e}",
    },
    "launch.no_project": {
        "ja": "pyproject.toml も requirements.txt も見つかりません: {workspace}",
        "en": "Neither pyproject.toml nor requirements.txt was found: {workspace}",
        "zh": "未找到 pyproject.toml 或 requirements.txt：{workspace}",
    },
    # shared catalogs
    "catalog.win_title": {"ja": "カタログ", "en": "Catalog", "zh": "目录"},
    "catalog.col_name": {"ja": "名前", "en": "Name", "zh": "名称"},
    "catalog.col_summary": {"ja": "概要", "en": "Summary", "zh": "简介"},
    "catalog.col_source": {"ja": "カタログ", "en": "Catalog", "zh": "目录"},
    "catalog.col_path": {"ja": "置き場", "en": "Location", "zh": "位置"},
    "catalog.run": {"ja": "このアプリを開く", "en": "Open this app", "zh": "打开此应用"},
    "catalog.refresh": {"ja": "再読込", "en": "Reload", "zh": "重新加载"},
    "catalog.none": {
        "ja": "表示できるアプリがありません。設定でカタログ JSON を登録してください。",
        "en": "No apps to show. Register a catalog JSON in Settings.",
        "zh": "没有可显示的应用。请在设置中注册目录 JSON。",
    },
    "catalog.load_notes": {
        "ja": "読み込み時の注意（{n}件）",
        "en": "Load notes ({n})",
        "zh": "加载提示（{n}）",
    },
    "catalog.err_not_object": {
        "ja": "カタログは JSON オブジェクトである必要があります",
        "en": "A catalog must be a JSON object",
        "zh": "目录必须是 JSON 对象",
    },
    "catalog.err_no_apps": {
        "ja": "カタログに apps 配列がありません",
        "en": "Catalog has no apps array",
        "zh": "目录中没有 apps 数组",
    },
    "catalog.err_apps_not_list": {
        "ja": "apps は配列である必要があります",
        "en": "apps must be an array",
        "zh": "apps 必须是数组",
    },
    "catalog.err_entry_not_object": {
        "ja": "apps[{n}] がオブジェクトではありません",
        "en": "apps[{n}] is not an object",
        "zh": "apps[{n}] 不是对象",
    },
    "catalog.err_entry_incomplete": {
        "ja": "apps[{n}] に name と path が必要です",
        "en": "apps[{n}] needs name and path",
        "zh": "apps[{n}] 需要 name 和 path",
    },
    "catalog.err_read": {
        "ja": "カタログを読めません: {path}\n{e}",
        "en": "Cannot read catalog: {path}\n{e}",
        "zh": "无法读取目录：{path}\n{e}",
    },
    "catalog.err_json": {
        "ja": "カタログの JSON が不正です: {path}\n{e}",
        "en": "Invalid catalog JSON: {path}\n{e}",
        "zh": "目录 JSON 无效：{path}\n{e}",
    },
    "catalog.err_missing": {
        "ja": "カタログファイルがありません: {path}",
        "en": "Catalog file not found: {path}",
        "zh": "未找到目录文件：{path}",
    },
    "catalog.err_path_missing": {
        "ja": "アプリの置き場にアクセスできません（無いか、権限がありません）:\n{path}",
        "en": "Cannot reach the app location (missing or no permission):\n{path}",
        "zh": "无法访问应用位置（不存在或无权限）：\n{path}",
    },
    "catalog.err_path_kind": {
        "ja": "置き場はフォルダか .zip である必要があります:\n{path}",
        "en": "Location must be a folder or a .zip:\n{path}",
        "zh": "位置必须是文件夹或 .zip：\n{path}",
    },
    "catalog.err_not_url": {
        "ja": "カタログ URL が不正です: {url}",
        "en": "Invalid catalog URL: {url}",
        "zh": "无效的目录 URL：{url}",
    },
    "catalog.err_http": {
        "ja": "カタログを取得できません: {url}\n{e}",
        "en": "Cannot fetch catalog: {url}\n{e}",
        "zh": "无法获取目录：{url}\n{e}",
    },
    "catalog.err_http_relative": {
        "ja": "HTTP カタログの相対 path には catalog の base が必要です: {path}",
        "en": "Relative path in an HTTP catalog needs catalog base: {path}",
        "zh": "HTTP 目录中的相对 path 需要 catalog 的 base：{path}",
    },
    "help.catalog": {
        "ja": (
            "カタログ JSON は共有アプリの「目次」です。自動でフォルダを走査しません。\n"
            "ファイルパス、または同じ形式の JSON を返す HTTP(S) API エンドポイントを登録できます。\n"
            "URL の末尾は .json でなくても構いません。各項目の path に初めてアクセスしたとき、\n"
            "必要ファイルの検証と実行前の確認が動きます。詳しくは docs/CATALOG.md。"
        ),
        "en": (
            "A catalog JSON is a table of contents for shared apps. Folders are not scanned.\n"
            "Register a file path or an HTTP(S) API endpoint returning the same JSON schema;\n"
            "the URL does not need a .json suffix. The first time a path is opened,\n"
            "required-file checks and the review dialog run as usual. See docs/CATALOG.md."
        ),
        "zh": (
            "目录 JSON 是共享应用的“目录表”。不会自动扫描文件夹。\n"
            "可注册文件路径或返回相同 JSON 格式的 HTTP(S) API 端点；URL 无需以 .json 结尾。\n"
            "首次访问 path 时，会进行必需文件校验并显示运行前确认。\n"
            "详见 docs/CATALOG.md。"
        ),
    },
}


def t(msgid: str, **kwargs: Any) -> str:
    """Translate `msgid` into the active language, with optional format kwargs.

    The first parameter is named ``msgid`` (not ``key``) so callers can pass
    ``key=...`` as a format field without colliding.
    """
    entry = _STRINGS.get(msgid)
    if not entry:
        return msgid
    text = entry.get(_current) or entry.get(LANG_EN) or entry.get(LANG_JA) or msgid
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def apply_from_settings() -> str:
    """Load language preference from settings and activate it."""
    try:
        from uvdrop.settings import load_settings

        code = load_settings().ui_language
    except Exception:  # noqa: BLE001
        code = "auto"
    return set_language(code or "auto")
