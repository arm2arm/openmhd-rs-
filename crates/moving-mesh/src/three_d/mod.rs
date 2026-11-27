//! Independent, serial static 3D half-space oracle. No MHD or moving geometry.
//!
//! Topological predicates operate on exact dyadic input coordinates. Scientific
//! integrals are compensated binary64 estimates, validated separately. This is
//! not an arbitrary-degeneracy robustness or geometry-acceptance claim.

mod clip;
mod exact;
pub mod fit;
mod moments;
pub mod operator_mesh;
mod oracle;
mod types;

pub use oracle::HalfSpaceOracle3;
pub use types::*;
