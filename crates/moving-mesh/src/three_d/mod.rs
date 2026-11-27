//! Serial 3D half-space geometry and opt-in predictive Lloyd generator motion.
//!
//! Topological predicates operate on exact dyadic input coordinates. Scientific
//! integrals are compensated binary64 estimates, validated separately. This is
//! not an arbitrary-degeneracy robustness or geometry-acceptance claim.

mod clip;
mod exact;
pub mod fit;
mod lloyd;
mod moments;
pub mod operator_mesh;
mod oracle;
mod types;

pub use lloyd::{GasMotion3, LloydConfig3, LloydError3, LloydStep3, predict_lloyd_step3};
pub use oracle::HalfSpaceOracle3;
pub use types::*;
