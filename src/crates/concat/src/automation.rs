// SPDX-License-Identifier: AGPL-3.0-or-later
//! One cancellable preparation job with progress delivered to the editor.
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;
use std::sync::{
    Mutex,
    atomic::{AtomicBool, Ordering},
};

static ACTIVE: AtomicBool = AtomicBool::new(false);
static CANCEL_REQUESTED: AtomicBool = AtomicBool::new(false);
static CANCEL: Mutex<Option<PathBuf>> = Mutex::new(None);

pub fn cancel() {
    CANCEL_REQUESTED.store(true, Ordering::SeqCst);
    if let Ok(guard) = CANCEL.lock() {
        if let Some(path) = guard.as_ref() {
            let _ = std::fs::write(path, b"cancel");
        }
    }
}

pub fn start(source: String, mut options: serde_json::Value) {
    if ACTIVE.swap(true, Ordering::SeqCst) {
        return;
    }
    CANCEL_REQUESTED.store(false, Ordering::SeqCst);
    crate::host::spawn_long(
        move || -> Result<(String, String), String> {
            let root =
                std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../arroba-editor");
            let flag = root.join(format!(".cancel-{}.flag", std::process::id()));
            let _ = std::fs::remove_file(&flag);
            if let Ok(mut guard) = CANCEL.lock() {
                *guard = Some(flag.clone());
            }
            if CANCEL_REQUESTED.load(Ordering::SeqCst) {
                let _ = std::fs::write(&flag, b"cancel");
            }
            options["cancelFile"] = serde_json::json!(flag.to_string_lossy());
            let run = || -> Result<(String, String), String> {
                let mut child = crate::background::python()
                    .arg(root.join("worker.py"))
                    .arg(source)
                    .arg(root.join("projects"))
                    .arg("--events")
                    .stdin(std::process::Stdio::piped())
                    .stdout(std::process::Stdio::piped())
                    .stderr(std::process::Stdio::null())
                    .spawn()
                    .map_err(|e| e.to_string())?;
                if let Some(mut input) = child.stdin.take() {
                    if let Err(error) = input.write_all(options.to_string().as_bytes()) {
                        let _ = child.kill();
                        let _ = child.wait();
                        return Err(error.to_string());
                    }
                }
                let mut result = Err("No se recibió el resultado del proceso.".to_owned());
                if let Some(output) = child.stdout.take() {
                    for line in BufReader::new(output).lines() {
                        let Ok(line) = line else {
                            break;
                        };
                        let Ok(event) = serde_json::from_str::<serde_json::Value>(&line) else {
                            continue;
                        };
                        if let Some(message) = event["progress"].as_str() {
                            let message = message.to_owned();
                            crate::host::on_ui(move |_, app, _| {
                                app.set_auto_status(message.into());
                            });
                        }
                        if let Some(error) = event["error"].as_str() {
                            result = Err(error.to_owned());
                        }
                        if let Some(path) = event["project"].as_str() {
                            let summary = event["summary"].as_str().unwrap_or("Edición preparada.");
                            let warnings = event["warnings"]
                                .as_array()
                                .map(|rows| {
                                    rows.iter()
                                        .filter_map(|v| v.as_str())
                                        .collect::<Vec<_>>()
                                        .join("\n")
                                })
                                .unwrap_or_default();
                            result = Ok((path.to_owned(), format!("{summary}\n{warnings}")));
                        }
                    }
                }
                let exit = child.wait().map_err(|e| e.to_string())?;
                if !exit.success() && result.is_ok() {
                    return Err("El proceso no terminó correctamente.".to_owned());
                }
                result
            };
            let result = run();
            if let Ok(mut guard) = CANCEL.lock() {
                *guard = None;
            }
            let _ = std::fs::remove_file(flag);
            result
        },
        |_, app, _, result| {
            ACTIVE.store(false, Ordering::SeqCst);
            app.set_auto_busy(false);
            match result {
                Ok((path, summary)) => {
                    app.set_auto_result(path.into());
                    app.set_auto_status(summary.into());
                }
                Err(error) => app.set_auto_status(error.into()),
            }
        },
    );
}
