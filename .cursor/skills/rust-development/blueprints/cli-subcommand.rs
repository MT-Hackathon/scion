// BLUEPRINT: cli-subcommand
// STRUCTURAL: clap derive, subcommand enum, execution dispatch
// ILLUSTRATIVE: command names, arguments, descriptions (replace with your domain)

use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "graft", about = "Knowledge sync CLI")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Check sync status of a connected project
    Status {
        #[arg(long)]
        target_repo: PathBuf,
    },
    /// Pull canonical knowledge into a project
    Pull {
        #[arg(long)]
        target_repo: PathBuf,
        #[arg(long, default_value_t = false)]
        dry_run: bool,
    },
}
