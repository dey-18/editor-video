// SPDX-License-Identifier: AGPL-3.0-or-later
//! Background Python workers must never allocate a Windows console.
pub fn python() -> std::process::Command {
    let root = std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../arroba-editor");
    let mut command = std::process::Command::new(root.join(".venv/Scripts/python.exe"));
    if let Ok(executable) = std::env::current_exe() {
        command.env("ARROBA_ENGINE", executable);
    }
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(0x08000000); // CREATE_NO_WINDOW
    }
    command
}
