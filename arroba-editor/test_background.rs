// SPDX-License-Identifier: AGPL-3.0-or-later
#[path = "../src/crates/concat/src/background.rs"]
mod background;

fn main() {
    let output = background::python()
        .args(["-c", "import ctypes; print(ctypes.windll.kernel32.GetConsoleWindow())"])
        .output().expect("worker starts");
    assert!(output.status.success());
    assert_eq!(String::from_utf8_lossy(&output.stdout).trim(), "0", "worker must have no console window");
    println!("Background worker: no console, stdout captured correctly");
}
