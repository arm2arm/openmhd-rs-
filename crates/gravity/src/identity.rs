use sha2::{Digest, Sha256};

/// Both digest and complete canonical bytes participate in equality.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Identity {
    bytes: Vec<u8>,
    sha256: [u8; 32],
}

impl Identity {
    pub(crate) fn new(bytes: Vec<u8>) -> Self {
        let sha256 = Sha256::digest(&bytes).into();
        Self { bytes, sha256 }
    }

    pub fn bytes(&self) -> &[u8] {
        &self.bytes
    }

    pub fn sha256(&self) -> [u8; 32] {
        self.sha256
    }
}

pub(crate) fn f64_bytes(out: &mut Vec<u8>, x: f64) {
    out.extend_from_slice(&x.to_bits().to_be_bytes());
}

pub(crate) fn sized_bytes(out: &mut Vec<u8>, bytes: &[u8]) {
    // usize fits u64 on the supported 64-bit reference target.
    out.extend_from_slice(&(bytes.len() as u64).to_be_bytes());
    out.extend_from_slice(bytes);
}
