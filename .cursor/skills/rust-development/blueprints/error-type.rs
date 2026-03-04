// BLUEPRINT: error-type
// STRUCTURAL: thiserror derive, variant naming, From conversions, structured fields
// ILLUSTRATIVE: error messages, wrapped types (replace with your domain)

use thiserror::Error;

#[derive(Error, Debug)]
pub enum GraftError {
    #[error("configuration error: {0}")]
    Config(String),

    #[error("git operation failed: {0}")]
    Git(String),

    #[error("I/O error: {source}")]
    Io {
        #[from]
        source: std::io::Error,
    },

    #[error("policy violation: {path} is classified as {classification}")]
    PolicyViolation { path: String, classification: String },
}
