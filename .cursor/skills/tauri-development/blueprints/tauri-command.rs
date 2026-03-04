// BLUEPRINT: tauri-command
// STRUCTURAL: tauri::command, specta::specta, serializable error, state access
// ILLUSTRATIVE: command name, parameter types, business logic (replace with your domain)

use serde::Serialize;
use std::sync::Mutex;
use tauri::State;

#[derive(Serialize)]
pub struct CommandError(String);

impl<E: std::error::Error> From<E> for CommandError {
    fn from(err: E) -> Self {
        CommandError(err.to_string())
    }
}

#[tauri::command]
#[specta::specta]
pub fn graft_status(
    target_repo: String,
    state: State<'_, Mutex<AppState>>,
) -> Result<StatusResult, CommandError> {
    let app_state = state.lock().map_err(|e| CommandError(e.to_string()))?;
    graft_core::run_status(&target_repo, &app_state.config).map_err(CommandError::from)
}
