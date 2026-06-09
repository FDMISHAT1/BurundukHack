# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for BurundukHack
# Build: pyinstaller burunduk.spec

import os
import sys

block_cipher = None

# Collect all data files
data_files = [
    ('data', 'data'),
    ('docs', 'docs'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        'commands.general_cmds',
        'commands.network_cmds',
        'commands.exploit_cmds',
        'commands.filesystem_cmds',
        'commands.social_cmds',
        'commands.linux_cmds',
        'commands.apt_cmds',
        'commands.file_edit_cmds',
        'commands.ctf_cmds',
        'commands.text_cmds',
        'commands.shell_builtins',
        'commands.net_tools',
        'commands.sysadmin_cmds',
        'commands.extra_cmds',
        'engine.game',
        'engine.shell',
        'engine.network',
        'engine.player',
        'engine.mission',
        'engine.filesystem',
        'engine.save',
        'engine.container',
        'engine.docker_dispatch',
        'ui.console',
        'ui.lang',
        'ui.banners',
        'ui.animations',
        'ui.prompt',
        'yaml',
        'rich',
        'prompt_toolkit',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='BurundukHack',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    icon=None,  # TODO: add icon
)
