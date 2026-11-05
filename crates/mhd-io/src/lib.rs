//! Exact-bit little-endian checkpoint codec. SHA-256 checks accidental corruption;
//! it is not authentication of an untrusted author's scientific state.
use sha2::{Digest, Sha256};
use std::{
    fs::{self, OpenOptions},
    io::Write,
    path::Path,
    sync::atomic::{AtomicU64, Ordering},
};

pub fn digest(parts: &[&[u8]]) -> [u8; 32] {
    let mut hash = Sha256::new();
    for part in parts {
        hash.update(part);
    }
    hash.finalize().into()
}

#[derive(Default)]
pub struct Encoder {
    data: Vec<u8>,
}
impl Encoder {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn finish(self) -> Vec<u8> {
        self.data
    }
    pub fn u64(&mut self, v: u64) {
        self.data.extend_from_slice(&v.to_le_bytes());
    }
    pub fn usize(&mut self, v: usize) {
        self.u64(v as u64);
    }
    pub fn i32(&mut self, v: i32) {
        self.data.extend_from_slice(&v.to_le_bytes());
    }
    pub fn boolean(&mut self, v: bool) {
        self.data.push(u8::from(v));
    }
    pub fn float(&mut self, v: f64) {
        self.u64(v.to_bits());
    }
    pub fn floats<const N: usize>(&mut self, v: &[f64; N]) {
        for &v in v {
            self.float(v);
        }
    }
    pub fn bytes(&mut self, v: &[u8]) {
        self.usize(v.len());
        self.data.extend_from_slice(v);
    }
    pub fn string(&mut self, v: &str) {
        self.bytes(v.as_bytes());
    }
}

pub struct Decoder<'a> {
    data: &'a [u8],
    offset: usize,
}
impl<'a> Decoder<'a> {
    pub fn new(data: &'a [u8]) -> Self {
        Self { data, offset: 0 }
    }
    pub fn take(&mut self, n: usize) -> Result<&'a [u8], String> {
        let end = self
            .offset
            .checked_add(n)
            .ok_or("checkpoint length overflow")?;
        let bytes = self
            .data
            .get(self.offset..end)
            .ok_or("truncated checkpoint")?;
        self.offset = end;
        Ok(bytes)
    }
    pub fn finish(self) -> Result<(), String> {
        if self.offset == self.data.len() {
            Ok(())
        } else {
            Err("trailing checkpoint data".into())
        }
    }
    pub fn u64(&mut self) -> Result<u64, String> {
        Ok(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))
    }
    pub fn usize(&mut self) -> Result<usize, String> {
        usize::try_from(self.u64()?)
            .map_err(|_| "checkpoint integer does not fit this platform".into())
    }
    pub fn count(&mut self, min_bytes: usize) -> Result<usize, String> {
        if min_bytes == 0 {
            return Err("invalid checkpoint record size".into());
        }
        let n = self.usize()?;
        if n > (self.data.len() - self.offset) / min_bytes {
            Err("checkpoint count exceeds available data".into())
        } else {
            Ok(n)
        }
    }
    pub fn i32(&mut self) -> Result<i32, String> {
        Ok(i32::from_le_bytes(self.take(4)?.try_into().unwrap()))
    }
    pub fn boolean(&mut self) -> Result<bool, String> {
        match self.take(1)?[0] {
            0 => Ok(false),
            1 => Ok(true),
            _ => Err("invalid checkpoint boolean".into()),
        }
    }
    pub fn float(&mut self) -> Result<f64, String> {
        Ok(f64::from_bits(self.u64()?))
    }
    pub fn floats<const N: usize>(&mut self) -> Result<[f64; N], String> {
        let mut a = [0.; N];
        for v in &mut a {
            *v = self.float()?;
        }
        Ok(a)
    }
    pub fn bytes(&mut self) -> Result<&'a [u8], String> {
        let n = self.count(1)?;
        self.take(n)
    }
    pub fn string(&mut self) -> Result<String, String> {
        String::from_utf8(self.bytes()?.to_vec()).map_err(|_| "invalid checkpoint UTF-8".into())
    }
}

const MAGIC: &[u8; 16] = b"OPENMHD-RESTART\0";
/// Envelope includes exact length, version and SHA-256 of the complete header/body.
pub fn seal(version: u64, payload: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(payload.len() + 64);
    out.extend_from_slice(MAGIC);
    out.extend_from_slice(&version.to_le_bytes());
    out.extend_from_slice(&(payload.len() as u64).to_le_bytes());
    out.extend_from_slice(payload);
    let sum = digest(&[&out]);
    out.extend_from_slice(&sum);
    out
}
pub fn unseal(data: &[u8], version: u64) -> Result<&[u8], String> {
    if data.len() < 64 || &data[..16] != MAGIC {
        return Err("not an OpenMHD restart file".into());
    }
    let mut r = Decoder::new(&data[16..32]);
    let stored = r.u64()?;
    let n = r.usize()?;
    if n.checked_add(64) != Some(data.len()) {
        return Err("restart envelope length mismatch".into());
    }
    if digest(&[&data[..data.len() - 32]]) != data[data.len() - 32..] {
        return Err("restart SHA-256 mismatch".into());
    }
    if stored != version {
        return Err(format!("unsupported restart version {stored}"));
    }
    Ok(&data[32..data.len() - 32])
}

static TEMP_ID: AtomicU64 = AtomicU64::new(0);
/// Atomic replacement in the destination directory; never truncate the previous file.
pub fn write_atomic(path: &Path, data: &[u8]) -> Result<(), String> {
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    let name = path
        .file_name()
        .ok_or("checkpoint path needs a filename")?
        .to_string_lossy();
    let temporary = parent.join(format!(
        ".{name}.tmp-{}-{}",
        std::process::id(),
        TEMP_ID.fetch_add(1, Ordering::Relaxed)
    ));
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&temporary)
        .map_err(|e| e.to_string())?;
    let result = (|| {
        file.write_all(data)
            .and_then(|_| file.sync_all())
            .map_err(|e| e.to_string())?;
        drop(file);
        fs::rename(&temporary, path).map_err(|e| e.to_string())?;
        #[cfg(unix)]
        fs::File::open(parent)
            .and_then(|f| f.sync_all())
            .map_err(|e| e.to_string())?;
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn atomic_replace_and_failed_write_preserve_existing_data() {
        let dir = std::env::temp_dir().join(format!("openmhd-atomic-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let path = dir.join("state.chk");
        write_atomic(&path, b"previous").unwrap();
        write_atomic(&path, b"replacement").unwrap();
        assert_eq!(fs::read(&path).unwrap(), b"replacement");
        assert!(write_atomic(&path.join("cannot-create"), b"bad").is_err());
        assert_eq!(fs::read(&path).unwrap(), b"replacement");
        assert_eq!(fs::read_dir(&dir).unwrap().count(), 1);
        fs::remove_dir_all(&dir).unwrap();
    }
    #[test]
    fn exact_bits_and_checked_envelope() {
        let mut w = Encoder::new();
        for x in [0., -0., f64::INFINITY, 1e-300, f64::from_bits(1)] {
            w.float(x);
        }
        w.string("restart");
        let bytes = seal(1, &w.finish());
        let mut r = Decoder::new(unseal(&bytes, 1).unwrap());
        for x in [0., -0., f64::INFINITY, 1e-300, f64::from_bits(1)] {
            assert_eq!(r.float().unwrap().to_bits(), x.to_bits());
        }
        assert_eq!(r.string().unwrap(), "restart");
        r.finish().unwrap();
        for n in 0..bytes.len() {
            assert!(unseal(&bytes[..n], 1).is_err());
        }
        for n in 0..bytes.len() {
            let mut corrupt = bytes.clone();
            corrupt[n] ^= 1;
            assert!(unseal(&corrupt, 1).is_err());
        }
        assert!(unseal(&bytes, 2).is_err());
        let mut huge = Encoder::new();
        huge.u64(u64::MAX);
        assert!(Decoder::new(&huge.finish()).count(8).is_err());
        assert!(Decoder::new(&[2]).boolean().is_err());
    }
    #[test]
    fn sha256_matches_standard_vector() {
        let expected = [
            0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea, 0x41, 0x41, 0x40, 0xde, 0x5d, 0xae,
            0x22, 0x23, 0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c, 0xb4, 0x10, 0xff, 0x61,
            0xf2, 0x00, 0x15, 0xad,
        ];
        assert_eq!(digest(&[b"a", b"bc"]), expected);
    }
}
