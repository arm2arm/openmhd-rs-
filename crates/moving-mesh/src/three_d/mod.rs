//! Serial 3D half-space geometry, prescribed motion rates and predictive Lloyd motion.
//!
//! Topological predicates operate on exact dyadic input coordinates. Scientific
//! integrals are compensated binary64 estimates, validated separately. This is
//! not an arbitrary-degeneracy robustness or geometry-acceptance claim.

mod advance;
mod clip;
mod exact;
pub mod fit;
mod lloyd;
mod moments;
mod motion;
pub mod motion_io;
pub mod operator_mesh;
mod oracle;
mod oriented;
mod polygon_motion;
mod types;

pub use advance::{
    FaceChange3, MeshStep3, MeshStepError3, advance_generators3, generator_endpoints3,
};
pub use lloyd::{
    GasMotion3, LloydConfig3, LloydError3, LloydStep3, predict_lloyd_step3, predict_lloyd_with,
};
pub use motion::{
    CellMotionRate3, FaceMotionRate3, MotionRateError3, MotionRates3, prescribed_motion_rates3,
};
pub use oracle::HalfSpaceOracle3;
pub use oriented::OrientedFace3;
pub use polygon_motion::{PolygonMotion3, PrescribedPolygonRates3};
pub use types::*;
