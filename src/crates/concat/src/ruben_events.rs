// SPDX-License-Identifier: AGPL-3.0-or-later
//! Persist editor outcomes without sending another provider request.
pub fn record(path: String, status: &'static str, message: String) {
    crate::host::spawn_long(
        move || {
            use std::io::Write;
            let root =
                std::path::Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../arroba-editor");
            let payload = serde_json::json!({"action":"record", "projectPath":path,
            "snapshot":{}, "instruction":"", "status":status, "message":message});
            let result = (|| -> Option<serde_json::Value> {
                let mut child = crate::background::python()
                    .arg(root.join("ruben_plan.py"))
                    .stdin(std::process::Stdio::piped())
                    .stdout(std::process::Stdio::piped())
                    .stderr(std::process::Stdio::null())
                    .spawn()
                    .ok()?;
                child
                    .stdin
                    .take()?
                    .write_all(payload.to_string().as_bytes())
                    .ok()?;
                let output = child.wait_with_output().ok()?;
                serde_json::from_slice(&output.stdout).ok()
            })();
            (path, result)
        },
        |studio, app, _, (path, result)| {
            if studio.session.as_ref().map(|s| s.path()) != Some(path.as_str()) {
                return;
            }
            if let Some(value) = result {
                if let Some(rows) = value["history"].as_array() {
                    let messages = rows
                        .iter()
                        .map(|row| crate::ui::RubenMessage {
                            user: row["role"].as_str() == Some("user"),
                            text: row["content"].as_str().unwrap_or_default().into(),
                        })
                        .collect::<Vec<_>>();
                    app.set_ruben_messages(
                        std::rc::Rc::new(slint::VecModel::from(messages)).into(),
                    );
                    app.set_ruben_reply(value["message"].as_str().unwrap_or_default().into());
                }
            } else {
                studio.notify(
                    "El cambio se procesó, pero no se pudo guardar su estado en el chat.",
                    true,
                );
            }
        },
    );
}
